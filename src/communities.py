"""Louvain community detection and departmental alignment evaluation for Email-Eu-core.

Provides undirected projection, modularity optimization (Lecture 7), conductance
profiling, departmental partition comparison (NMI, ARI, contingency matrix),
and multi-seed/resolution robustness checks.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

logger = logging.getLogger(__name__)


def create_undirected_projection(
    G_directed: nx.DiGraph,
) -> Tuple[nx.Graph, Dict[str, Any]]:
    """Create unweighted undirected projection of the directed communication graph.

    Collapses reciprocal directed edges (u, v) and (v, u) into a single
    undirected edge {u, v}. Preserves all nodes and their attributes.

    Parameters
    ----------
    G_directed : nx.DiGraph
        Directed analysis graph G_analysis (expected 1,005 nodes, 24,929 directed edges).

    Returns
    -------
    Tuple[nx.Graph, Dict[str, Any]]
        Undirected graph G_undir and audit dictionary detailing reciprocal edge collapse.
    """
    G_undir = G_directed.to_undirected()

    num_dir_edges = G_directed.number_of_edges()
    num_undir_edges = G_undir.number_of_edges()

    # Reciprocal pairs: pairs where both (u, v) and (v, u) exist in G_directed
    reciprocal_pairs_count = num_dir_edges - num_undir_edges
    reciprocal_directed_edges = reciprocal_pairs_count * 2
    unreciprocated_directed_edges = num_dir_edges - reciprocal_directed_edges

    audit = {
        "num_nodes": G_undir.number_of_nodes(),
        "directed_edges": num_dir_edges,
        "undirected_edges": num_undir_edges,
        "reciprocal_pairs_collapsed": reciprocal_pairs_count,
        "reciprocal_directed_edges": reciprocal_directed_edges,
        "unreciprocated_directed_edges": unreciprocated_directed_edges,
        "fraction_directed_edges_reciprocal": float(reciprocal_directed_edges / num_dir_edges) if num_dir_edges else 0.0,
    }

    return G_undir, audit


def detect_louvain_communities(
    G_undir: nx.Graph, resolution: float = 1.0, seed: int = 42
) -> Tuple[List[Set[int]], Dict[int, int], float]:
    """Detect communities using Louvain modularity optimization (NetworkX).

    Communities are sorted deterministically in descending order of size,
    with community IDs assigned from 0 to C-1.

    Parameters
    ----------
    G_undir : nx.Graph
        Undirected communication network.
    resolution : float
        Modularity resolution parameter (default 1.0).
    seed : int
        Random seed for stochastic phase ordering.

    Returns
    -------
    Tuple[List[Set[int]], Dict[int, int], float]
        Sorted list of community node sets, node-to-community mapping, and modularity Q.
    """
    raw_communities = nx.community.louvain_communities(
        G_undir, weight=None, resolution=resolution, seed=seed
    )

    # Sort communities deterministically by size (descending), then by smallest node_id
    sorted_communities = sorted(
        raw_communities, key=lambda c: (-len(c), min(c) if c else 0)
    )

    node_to_comm: Dict[int, int] = {}
    for comm_id, node_set in enumerate(sorted_communities):
        for node in node_set:
            node_to_comm[node] = comm_id

    modularity_q = float(nx.community.modularity(G_undir, sorted_communities, resolution=resolution))

    return sorted_communities, node_to_comm, modularity_q


def evaluate_community_conductance(
    G_undir: nx.Graph, communities: List[Set[int]]
) -> Dict[str, Any]:
    r"""Compute conductance for each non-trivial community.

    Conductance measures the ratio of cut edges crossing the community boundary
    to the minimum volume of the community and the rest of the network:
        \phi(S) = \frac{|\partial(S)|}{\min(\text{vol}(S), \text{vol}(V \setminus S))}

    Trivial communities (e.g. isolated nodes where vol(S) = 0) are excluded
    from conductance summaries.
    """
    total_volume = 2 * G_undir.number_of_edges()
    conductance_by_comm: Dict[int, float] = {}

    for comm_id, S in enumerate(communities):
        if len(S) == 0:
            continue
        vol_s = sum(G_undir.degree(u) for u in S)
        # If community has no edges (e.g. isolated singleton), conductance is undefined
        if vol_s == 0 or vol_s == total_volume:
            continue

        try:
            phi = float(nx.conductance(G_undir, S))
            conductance_by_comm[comm_id] = phi
        except Exception:
            continue

    phi_values = list(conductance_by_comm.values())

    return {
        "conductance_by_community": conductance_by_comm,
        "evaluated_communities_count": len(phi_values),
        "mean_conductance": float(np.mean(phi_values)) if phi_values else 0.0,
        "median_conductance": float(np.median(phi_values)) if phi_values else 0.0,
        "min_conductance": float(np.min(phi_values)) if phi_values else 0.0,
        "max_conductance": float(np.max(phi_values)) if phi_values else 0.0,
    }


def compare_communities_with_departments(
    G_undir: nx.Graph, node_to_comm: Dict[int, int]
) -> Dict[str, Any]:
    """Compare discovered Louvain communities against ground-truth department labels.

    Computes:
    - Normalized Mutual Information (NMI)
    - Adjusted Rand Index (ARI)
    - Baseline departmental modularity Q_dept
    - Department-community contingency matrix
    - Department fragmentation and community purity metrics
    """
    nodes = sorted(list(G_undir.nodes()))
    dept_labels = [G_undir.nodes[n]["department"] for n in nodes]
    comm_labels = [node_to_comm[n] for n in nodes]

    nmi = float(normalized_mutual_info_score(dept_labels, comm_labels))
    ari = float(adjusted_rand_score(dept_labels, comm_labels))

    # Construct departmental community partition for modularity baseline
    dept_to_nodes: Dict[int, Set[int]] = defaultdict(set)
    for n in nodes:
        dept_to_nodes[G_undir.nodes[n]["department"]].add(n)
    dept_partition = list(dept_to_nodes.values())
    dept_modularity = float(nx.community.modularity(G_undir, dept_partition))
    dept_conductance = evaluate_community_conductance(G_undir, dept_partition)

    # Contingency matrix: rows = departments, cols = communities
    contingency_df = pd.crosstab(
        pd.Series(dept_labels, name="Department"),
        pd.Series(comm_labels, name="Community"),
    )

    # Department fragmentation: how many communities does each department span?
    dept_fragmentation: Dict[int, Dict[str, Any]] = {}
    for d, row in contingency_df.iterrows():
        non_zero = row[row > 0]
        dept_size = int(row.sum())
        max_in_one_comm = int(non_zero.max()) if not non_zero.empty else 0
        purity = float(max_in_one_comm / dept_size) if dept_size > 0 else 0.0
        dept_fragmentation[int(d)] = {
            "size": dept_size,
            "communities_spanned": len(non_zero),
            "dominant_community": int(non_zero.idxmax()) if not non_zero.empty else -1,
            "dominant_community_count": max_in_one_comm,
            "purity": purity,
        }

    # Community department diversity: how many departments reside in each community?
    comm_diversity: Dict[int, Dict[str, Any]] = {}
    for c in contingency_df.columns:
        col = contingency_df[c]
        non_zero = col[col > 0]
        comm_size = int(col.sum())
        max_from_one_dept = int(non_zero.max()) if not non_zero.empty else 0
        concentration = float(max_from_one_dept / comm_size) if comm_size > 0 else 0.0
        comm_diversity[int(c)] = {
            "size": comm_size,
            "departments_represented": len(non_zero),
            "dominant_department": int(non_zero.idxmax()) if not non_zero.empty else -1,
            "dominant_department_count": max_from_one_dept,
            "department_concentration": concentration,
        }

    return {
        "nmi": nmi,
        "ari": ari,
        "department_modularity": dept_modularity,
        "department_conductance": dept_conductance,
        "contingency_matrix": contingency_df,
        "dept_fragmentation": dept_fragmentation,
        "comm_diversity": comm_diversity,
    }


def run_louvain_robustness(
    G_undir: nx.Graph,
    seeds: Tuple[int, ...] = (42, 123, 2026, 7, 99),
    resolutions: Tuple[float, ...] = (0.8, 1.0, 1.2),
) -> Dict[str, Any]:
    """Evaluate Louvain stability across random seeds and resolution variations.

    Measures:
    - Modularity Q, community count, NMI, and ARI across seeds at resolution=1.0
    - Pairwise ARI between partitions generated with different seeds
    - Modularity Q, community count, NMI, ARI, and agreement with resolution 1.0 baseline
    """
    nodes = sorted(list(G_undir.nodes()))
    dept_labels = [G_undir.nodes[n]["department"] for n in nodes]

    # 1. Seed stability at resolution 1.0
    seed_results: Dict[int, Dict[str, Any]] = {}
    seed_partitions: Dict[int, List[int]] = {}

    for s in seeds:
        comms, n2c, q = detect_louvain_communities(G_undir, resolution=1.0, seed=s)
        labels = [n2c[n] for n in nodes]
        seed_partitions[s] = labels
        seed_nmi = float(normalized_mutual_info_score(dept_labels, labels))
        seed_ari = float(adjusted_rand_score(dept_labels, labels))
        seed_results[s] = {
            "num_communities": len(comms),
            "sizes": [len(c) for c in comms if len(c) > 1],
            "singletons_count": sum(1 for c in comms if len(c) == 1),
            "modularity": q,
            "nmi": seed_nmi,
            "ari": seed_ari,
        }

    # Pairwise ARI between seed runs
    pairwise_seed_ari: Dict[str, float] = {}
    for i in range(len(seeds)):
        for j in range(i + 1, len(seeds)):
            s1, s2 = seeds[i], seeds[j]
            ari_val = float(adjusted_rand_score(seed_partitions[s1], seed_partitions[s2]))
            pairwise_seed_ari[f"seed_{s1}_vs_seed_{s2}"] = ari_val

    # 2. Resolution sensitivity at seed=42
    resolution_results: Dict[float, Dict[str, Any]] = {}
    res_partitions: Dict[float, List[int]] = {}
    base_res_labels = seed_partitions.get(42)

    for gamma in resolutions:
        comms, n2c, q = detect_louvain_communities(G_undir, resolution=gamma, seed=42)
        labels = [n2c[n] for n in nodes]
        res_partitions[gamma] = labels
        res_nmi = float(normalized_mutual_info_score(dept_labels, labels))
        res_ari = float(adjusted_rand_score(dept_labels, labels))
        agreement_with_base = (
            float(adjusted_rand_score(base_res_labels, labels))
            if base_res_labels is not None
            else 1.0
        )
        resolution_results[gamma] = {
            "num_communities": len(comms),
            "sizes": [len(c) for c in comms if len(c) > 1],
            "singletons_count": sum(1 for c in comms if len(c) == 1),
            "modularity": q,
            "nmi": res_nmi,
            "ari": res_ari,
            "ari_with_res_1_0": agreement_with_base,
        }

    return {
        "seeds": seeds,
        "seed_results": seed_results,
        "pairwise_seed_ari": pairwise_seed_ari,
        "resolutions": resolutions,
        "resolution_results": resolution_results,
    }

