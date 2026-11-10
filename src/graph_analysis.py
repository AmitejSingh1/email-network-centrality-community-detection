"""Graph analysis and exploratory network metrics for Email-Eu-core.

Calculates degree distributions, connectivity components, reciprocity, density,
and departmental edge composition (within-department vs. cross-department),
comparing empirical communication against a uniform random ordered-pair reference model.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import networkx as nx
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_directed_density(
    G: nx.DiGraph, allow_self_loops: bool = False
) -> Dict[str, Any]:
    """Calculate directed network density with documented mathematical formulas.

    Parameters
    ----------
    G : nx.DiGraph
        Directed graph.
    allow_self_loops : bool
        If False, density uses denominator N * (N - 1) representing maximum
        possible ordered pairs between distinct nodes.
        If True, density uses denominator N * N representing all possible
        directed edges including self-loops.

    Returns
    -------
    Dict[str, Any]
        Dictionary with density value, edge count, node count, max possible edges,
        and LaTeX formula description.
    """
    n = G.number_of_nodes()
    m = G.number_of_edges()

    if n <= 1:
        return {
            "density": 0.0,
            "formula": "m / (n * (n - 1))",
            "nodes": n,
            "edges": m,
            "max_possible_edges": 0,
        }

    if allow_self_loops:
        max_edges = n * n
        formula_str = r"\rho_{raw} = \frac{|E|}{|V|^2}"
    else:
        max_edges = n * (n - 1)
        formula_str = r"\rho_{analysis} = \frac{|E|}{|V|(|V|-1)}"

    density_val = float(m / max_edges)

    return {
        "density": density_val,
        "nodes": n,
        "edges": m,
        "max_possible_edges": max_edges,
        "allow_self_loops": allow_self_loops,
        "formula": formula_str,
    }


def compute_degree_statistics(G: nx.DiGraph) -> Dict[str, Any]:
    """Compute detailed in-degree, out-degree, and total degree statistics.

    Parameters
    ----------
    G : nx.DiGraph
        Directed email communication graph.

    Returns
    -------
    Dict[str, Any]
        Dictionary of degree metrics including distribution moments and arrays.
    """
    in_degrees = np.array([d for _, d in G.in_degree()])
    out_degrees = np.array([d for _, d in G.out_degree()])
    total_degrees = in_degrees + out_degrees

    zero_degree_nodes = [n for n in G.nodes() if G.in_degree(n) == 0 and G.out_degree(n) == 0]
    zero_in_degree_nodes = [n for n in G.nodes() if G.in_degree(n) == 0]
    zero_out_degree_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]

    stats = {
        "num_nodes": G.number_of_nodes(),
        "zero_degree_nodes_count": len(zero_degree_nodes),
        "zero_degree_nodes_list": sorted(zero_degree_nodes),
        "zero_in_degree_count": len(zero_in_degree_nodes),
        "zero_out_degree_count": len(zero_out_degree_nodes),
        "in_degree": {
            "mean": float(np.mean(in_degrees)),
            "std": float(np.std(in_degrees)),
            "median": float(np.median(in_degrees)),
            "min": int(np.min(in_degrees)),
            "max": int(np.max(in_degrees)),
            "p25": float(np.percentile(in_degrees, 25)),
            "p75": float(np.percentile(in_degrees, 75)),
            "p95": float(np.percentile(in_degrees, 95)),
            "values": in_degrees.tolist(),
        },
        "out_degree": {
            "mean": float(np.mean(out_degrees)),
            "std": float(np.std(out_degrees)),
            "median": float(np.median(out_degrees)),
            "min": int(np.min(out_degrees)),
            "max": int(np.max(out_degrees)),
            "p25": float(np.percentile(out_degrees, 25)),
            "p75": float(np.percentile(out_degrees, 75)),
            "p95": float(np.percentile(out_degrees, 95)),
            "values": out_degrees.tolist(),
        },
        "total_degree": {
            "mean": float(np.mean(total_degrees)),
            "std": float(np.std(total_degrees)),
            "median": float(np.median(total_degrees)),
            "min": int(np.min(total_degrees)),
            "max": int(np.max(total_degrees)),
            "p25": float(np.percentile(total_degrees, 25)),
            "p75": float(np.percentile(total_degrees, 75)),
            "p95": float(np.percentile(total_degrees, 95)),
            "values": total_degrees.tolist(),
        },
    }
    return stats


def compute_component_statistics(G: nx.DiGraph) -> Dict[str, Any]:
    """Compute weakly and strongly connected component distributions."""
    wcc = list(nx.weakly_connected_components(G))
    wcc_sizes = sorted([len(c) for c in wcc], reverse=True)

    scc = list(nx.strongly_connected_components(G))
    scc_sizes = sorted([len(c) for c in scc], reverse=True)

    total_nodes = G.number_of_nodes()
    stats = {
        "wcc_count": len(wcc),
        "largest_wcc_size": wcc_sizes[0] if wcc_sizes else 0,
        "largest_wcc_fraction": float(wcc_sizes[0] / total_nodes) if total_nodes else 0.0,
        "wcc_size_distribution": wcc_sizes,
        "scc_count": len(scc),
        "largest_scc_size": scc_sizes[0] if scc_sizes else 0,
        "largest_scc_fraction": float(scc_sizes[0] / total_nodes) if total_nodes else 0.0,
        "scc_size_distribution": scc_sizes,
    }
    return stats


def compute_department_statistics(G: nx.DiGraph) -> Dict[str, Any]:
    """Analyze departmental composition and size distribution across graph nodes."""
    depts: List[int] = [data["department"] for _, data in G.nodes(data=True)]
    dept_series = pd.Series(depts)
    dept_counts = dept_series.value_counts().sort_index()

    stats = {
        "num_departments": len(dept_counts),
        "department_sizes": dept_counts.to_dict(),
        "mean_size": float(dept_counts.mean()),
        "std_size": float(dept_counts.std()),
        "median_size": float(dept_counts.median()),
        "min_size": int(dept_counts.min()),
        "max_size": int(dept_counts.max()),
        "p25_size": float(dept_counts.quantile(0.25)),
        "p75_size": float(dept_counts.quantile(0.75)),
    }
    return stats


def compute_uniform_random_reference_model(G: nx.DiGraph) -> Dict[str, Any]:
    """Compute expected within-department edge fraction under a uniform random ordered-pair model.

    Holds empirical department sizes fixed. Assumes any ordered pair (u, v) with
    u != v is equally likely to form an edge.

    Formula:
        p_null = sum_{d=0}^{D-1} [ S_d * (S_d - 1) ] / [ N * (N - 1) ]

    where N = |V| and S_d is the number of individuals affiliated with department d.
    """
    dept_stats = compute_department_statistics(G)
    dept_sizes = list(dept_stats["department_sizes"].values())
    n = G.number_of_nodes()

    if n <= 1:
        return {"expected_within_fraction": 0.0, "total_ordered_pairs": 0}

    total_ordered_pairs = n * (n - 1)
    within_dept_possible_pairs = sum(s * (s - 1) for s in dept_sizes)
    p_null = float(within_dept_possible_pairs / total_ordered_pairs)

    return {
        "num_nodes": n,
        "num_departments": len(dept_sizes),
        "total_possible_ordered_pairs": total_ordered_pairs,
        "within_dept_possible_pairs": within_dept_possible_pairs,
        "cross_dept_possible_pairs": total_ordered_pairs - within_dept_possible_pairs,
        "expected_within_fraction": p_null,
        "expected_cross_fraction": 1.0 - p_null,
        "formula": r"p_{null} = \frac{\sum_{d} S_d(S_d - 1)}{N(N - 1)}",
    }


def compute_edge_department_composition(
    G: nx.DiGraph, exclude_self_loops: bool = False
) -> Dict[str, Any]:
    """Evaluate within-department vs. cross-department communication volume.

    Parameters
    ----------
    G : nx.DiGraph
        Directed graph with 'department' node attribute.
    exclude_self_loops : bool
        If True, self-loops (u == v) are excluded before evaluating within/cross edges.
        If False, self-loops are counted as within-department edges.

    Returns
    -------
    Dict[str, Any]
        Edge breakdown metrics including counts, proportions, and comparison against
        uniform random reference model.
    """
    total_edges = 0
    within_dept_edges = 0
    cross_dept_edges = 0
    self_loops_count = 0

    dept_matrix: Dict[Tuple[int, int], int] = {}
    dept_internal_edges: Dict[int, int] = {}
    dept_outgoing_cross: Dict[int, int] = {}
    dept_incoming_cross: Dict[int, int] = {}

    for u, v in G.edges():
        is_self_loop = (u == v)
        if is_self_loop:
            self_loops_count += 1
            if exclude_self_loops:
                continue

        total_edges += 1
        d_u = G.nodes[u]["department"]
        d_v = G.nodes[v]["department"]

        # Track pairwise department flow
        dept_matrix[(d_u, d_v)] = dept_matrix.get((d_u, d_v), 0) + 1

        if d_u == d_v:
            within_dept_edges += 1
            dept_internal_edges[d_u] = dept_internal_edges.get(d_u, 0) + 1
        else:
            cross_dept_edges += 1
            dept_outgoing_cross[d_u] = dept_outgoing_cross.get(d_u, 0) + 1
            dept_incoming_cross[d_v] = dept_incoming_cross.get(d_v, 0) + 1

    within_fraction = float(within_dept_edges / total_edges) if total_edges else 0.0
    cross_fraction = float(cross_dept_edges / total_edges) if total_edges else 0.0

    # Reference model comparison
    ref_model = compute_uniform_random_reference_model(G)
    p_null = ref_model["expected_within_fraction"]
    homophily_ratio = float(within_fraction / p_null) if p_null > 0 else 0.0

    return {
        "total_evaluated_edges": total_edges,
        "self_loops_count": self_loops_count,
        "exclude_self_loops": exclude_self_loops,
        "within_dept_edges": within_dept_edges,
        "within_dept_fraction": within_fraction,
        "cross_dept_edges": cross_dept_edges,
        "cross_dept_fraction": cross_fraction,
        "dept_internal_edges": dept_internal_edges,
        "dept_outgoing_cross": dept_outgoing_cross,
        "dept_incoming_cross": dept_incoming_cross,
        "dept_flow_matrix": dept_matrix,
        "reference_model_expected_within_fraction": p_null,
        "reference_model_expected_cross_fraction": ref_model["expected_cross_fraction"],
        "homophily_enrichment_ratio": homophily_ratio,
    }


def compute_reciprocity_statistics(G: nx.DiGraph) -> Dict[str, Any]:
    """Compute overall reciprocity in the directed network."""
    overall_reciprocity = float(nx.reciprocity(G))

    G_no_self = G.copy()
    G_no_self.remove_edges_from(nx.selfloop_edges(G_no_self))
    reciprocity_no_self = float(nx.reciprocity(G_no_self))

    return {
        "reciprocity_with_self_loops": overall_reciprocity,
        "reciprocity_no_self_loops": reciprocity_no_self,
        "num_self_loops": G.number_of_edges() - G_no_self.number_of_edges(),
    }


def compare_raw_vs_analysis_graphs(
    G_raw: nx.DiGraph, G_analysis: nx.DiGraph
) -> Dict[str, Any]:
    """Generate side-by-side comparative metrics for G_raw and G_analysis."""
    return {
        "raw": {
            "num_nodes": G_raw.number_of_nodes(),
            "num_edges": G_raw.number_of_edges(),
            "self_loops": nx.number_of_selfloops(G_raw),
            "density": compute_directed_density(G_raw, allow_self_loops=True)["density"],
            "wcc_count": nx.number_weakly_connected_components(G_raw),
            "largest_wcc_size": max(len(c) for c in nx.weakly_connected_components(G_raw)),
            "scc_count": nx.number_strongly_connected_components(G_raw),
            "largest_scc_size": max(len(c) for c in nx.strongly_connected_components(G_raw)),
            "zero_degree_nodes": sum(1 for n in G_raw.nodes() if G_raw.degree(n) == 0),
            "edge_composition": compute_edge_department_composition(G_raw, exclude_self_loops=False),
            "reciprocity": compute_reciprocity_statistics(G_raw)["reciprocity_with_self_loops"],
        },
        "analysis": {
            "num_nodes": G_analysis.number_of_nodes(),
            "num_edges": G_analysis.number_of_edges(),
            "self_loops": nx.number_of_selfloops(G_analysis),
            "density": compute_directed_density(G_analysis, allow_self_loops=False)["density"],
            "wcc_count": nx.number_weakly_connected_components(G_analysis),
            "largest_wcc_size": max(len(c) for c in nx.weakly_connected_components(G_analysis)),
            "scc_count": nx.number_strongly_connected_components(G_analysis),
            "largest_scc_size": max(len(c) for c in nx.strongly_connected_components(G_analysis)),
            "zero_degree_nodes": sum(1 for n in G_analysis.nodes() if G_analysis.degree(n) == 0),
            "edge_composition": compute_edge_department_composition(G_analysis, exclude_self_loops=True),
            "reciprocity": compute_reciprocity_statistics(G_analysis)["reciprocity_no_self_loops"],
        },
    }
