"""Integrated analysis module connecting PageRank centrality with Louvain communities.

Combines node prominence, departmental affiliations, and cross-community
boundary bridging metrics to answer the primary research question.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np
import pandas as pd
from scipy import stats

from src.centrality import compute_centrality_dataframe, compute_pagerank
from src.communities import detect_louvain_communities, evaluate_community_conductance

logger = logging.getLogger(__name__)


def build_integrated_node_dataframe(
    G_directed: nx.DiGraph,
    G_undirected: nx.Graph,
    node_to_comm: Dict[int, int],
    alpha: float = 0.85,
    tol: float = 1e-6,
) -> pd.DataFrame:
    """Construct unified node-level analysis DataFrame.

    Combines directed centrality (PageRank, In-Degree) with undirected community
    membership and cross-community connectivity metrics.

    Parameters
    ----------
    G_directed : nx.DiGraph
        Directed analysis graph G_analysis (1,005 nodes).
    G_undirected : nx.Graph
        Undirected projection G_undirected (1,005 nodes).
    node_to_comm : Dict[int, int]
        Mapping from node_id to Louvain community identifier.
    alpha : float
        PageRank damping factor.
    tol : float
        PageRank convergence tolerance.

    Returns
    -------
    pd.DataFrame
        Complete node-level metrics table.
    """
    df_cent = compute_centrality_dataframe(G_directed, alpha=alpha, tol=tol)

    # Compute community sizes
    comm_sizes = pd.Series(list(node_to_comm.values())).value_counts().to_dict()

    records = []
    for node in G_undirected.nodes():
        c_u = node_to_comm[node]
        neighbors = list(G_undirected.neighbors(node))
        tot_deg = len(neighbors)

        internal_count = sum(1 for v in neighbors if node_to_comm[v] == c_u)
        cross_count = sum(1 for v in neighbors if node_to_comm[v] != c_u)

        cross_fraction = (
            float(cross_count / tot_deg) if tot_deg > 0 else np.nan
        )

        records.append(
            {
                "node_id": node,
                "comm_id": c_u,
                "comm_size": comm_sizes.get(c_u, 1),
                "internal_edges_count": internal_count,
                "cross_community_count": cross_count,
                "total_undirected_degree": tot_deg,
                "cross_community_fraction": cross_fraction,
            }
        )

    df_comm = pd.DataFrame(records)
    df_merged = pd.merge(df_cent, df_comm, on="node_id")

    # Sort strictly by PageRank prominence rank
    df_merged = df_merged.sort_values(by="pagerank_rank_unique", ascending=True).reset_index(drop=True)
    return df_merged


def compare_top_nodes_cross_connectivity(
    df: pd.DataFrame, top_percent: float = 0.10
) -> Dict[str, Any]:
    """Statistically compare cross-community connectivity of top PageRank nodes vs. remaining nodes.

    Parameters
    ----------
    df : pd.DataFrame
        Integrated node DataFrame.
    top_percent : float
        Fraction of nodes defined as top tier (default 0.10 = top 101 nodes).

    Returns
    -------
    Dict[str, Any]
        Summary comparison statistics, correlations, and distribution tests.
    """
    n_top = int(np.ceil(len(df) * top_percent))
    top_df = df.head(n_top)
    rem_df = df.iloc[n_top:]

    # Remove NaN values for fraction calculations (zero-degree nodes)
    top_fracs = top_df["cross_community_fraction"].dropna()
    rem_fracs = rem_df["cross_community_fraction"].dropna()

    top_counts = top_df["cross_community_count"]
    rem_counts = rem_df["cross_community_count"]

    # Mann-Whitney U tests
    u_count, p_count = stats.mannwhitneyu(top_counts, rem_counts, alternative="two-sided")
    u_frac, p_frac = stats.mannwhitneyu(top_fracs, rem_fracs, alternative="two-sided")

    # Correlations across all valid nodes
    valid_df = df.dropna(subset=["cross_community_fraction"])
    rho_count, p_rho_count = stats.spearmanr(df["pagerank"], df["cross_community_count"])
    rho_frac, p_rho_frac = stats.spearmanr(valid_df["pagerank"], valid_df["cross_community_fraction"])

    return {
        "top_percent": top_percent,
        "n_top": n_top,
        "n_remaining": len(rem_df),
        "top_tier": {
            "mean_cross_count": float(top_counts.mean()),
            "median_cross_count": float(top_counts.median()),
            "std_cross_count": float(top_counts.std()),
            "mean_cross_fraction": float(top_fracs.mean()),
            "median_cross_fraction": float(top_fracs.median()),
            "std_cross_fraction": float(top_fracs.std()),
        },
        "remaining_tier": {
            "mean_cross_count": float(rem_counts.mean()),
            "median_cross_count": float(rem_counts.median()),
            "std_cross_count": float(rem_counts.std()),
            "mean_cross_fraction": float(rem_fracs.mean()),
            "median_cross_fraction": float(rem_fracs.median()),
            "std_cross_fraction": float(rem_fracs.std()),
        },
        "mann_whitney_count": {"u_stat": float(u_count), "p_value": float(p_count)},
        "mann_whitney_fraction": {"u_stat": float(u_frac), "p_value": float(p_frac)},
        "spearman_pagerank_vs_cross_count": {"rho": float(rho_count), "p_value": float(p_rho_count)},
        "spearman_pagerank_vs_cross_fraction": {"rho": float(rho_frac), "p_value": float(p_rho_frac)},
    }


def compute_community_level_summaries(
    G_undirected: nx.Graph, df: pd.DataFrame, communities: List[Set[int]]
) -> pd.DataFrame:
    """Compute community-level profiles combining size, conductance, departments, and centrality."""
    cond_res = evaluate_community_conductance(G_undirected, communities)
    cond_dict = cond_res["conductance_by_community"]

    rows = []
    for c_id, node_set in enumerate(communities):
        sz = len(node_set)
        if sz == 0:
            continue

        c_df = df[df["comm_id"] == c_id]
        depts = c_df["department"].value_counts()
        dominant_dept = depts.index[0] if not depts.empty else -1
        dominant_dept_count = depts.iloc[0] if not depts.empty else 0
        dominant_dept_fraction = dominant_dept_count / sz if sz > 0 else 0.0

        # Subgraph edges
        subG = G_undirected.subgraph(node_set)
        internal_edges = subG.number_of_edges()
        vol_s = sum(G_undirected.degree(n) for n in node_set)
        external_cut = vol_s - (2 * internal_edges)

        mean_pr = float(c_df["pagerank"].mean())
        sum_pr = float(c_df["pagerank"].sum())
        mean_cross_frac = float(c_df["cross_community_fraction"].dropna().mean()) if sz > 1 else np.nan

        rows.append(
            {
                "comm_id": c_id,
                "size": sz,
                "num_departments": len(depts),
                "dominant_department": dominant_dept,
                "dominant_dept_fraction": float(dominant_dept_fraction),
                "internal_edges": internal_edges,
                "external_cut_edges": external_cut,
                "conductance": cond_dict.get(c_id, np.nan),
                "mean_pagerank": mean_pr,
                "total_pagerank": sum_pr,
                "mean_cross_fraction": mean_cross_frac,
            }
        )

    summary_df = pd.DataFrame(rows)
    return summary_df


def select_case_study_nodes(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Select informative individual case studies illustrating contrasting structural archetypes.

    Archetypes:
    1. High PR, High Cross-Community Connectivity (Global Boundary Spanner).
    2. High PR, Moderate/Lower Cross-Community Connectivity (Internal Community Hub).
    3. Low/Moderate PR, High Cross-Community Fraction (Peripheral Local Bridge).
    """
    valid_df = df.dropna(subset=["cross_community_fraction"])

    # High PR (top 50) and high cross fraction (>= 0.60) and high cross count (>= 50)
    high_pr_bridge = valid_df[
        (valid_df["pagerank_rank_unique"] <= 50)
        & (valid_df["cross_community_fraction"] >= 0.60)
        & (valid_df["cross_community_count"] >= 50)
    ].sort_values(by="cross_community_count", ascending=False)

    # High PR (top 50) and lower cross fraction (<= 0.40)
    high_pr_hub = valid_df[
        (valid_df["pagerank_rank_unique"] <= 50)
        & (valid_df["cross_community_fraction"] <= 0.45)
    ].sort_values(by="cross_community_fraction", ascending=True)

    # Low PR (bottom 50%, rank >= 500) with high cross fraction (>= 0.70) and total degree >= 5
    peripheral_bridge = valid_df[
        (valid_df["pagerank_rank_unique"] >= 500)
        & (valid_df["cross_community_fraction"] >= 0.70)
        & (valid_df["total_undirected_degree"] >= 5)
    ].sort_values(by="cross_community_fraction", ascending=False)

    return {
        "high_pr_bridge": high_pr_bridge,
        "high_pr_hub": high_pr_hub,
        "peripheral_bridge": peripheral_bridge,
    }


def run_integrated_robustness(
    G_directed: nx.DiGraph,
    G_undirected: nx.Graph,
    seeds: Tuple[int, ...] = (42, 123),
    resolutions: Tuple[float, ...] = (0.8, 1.0, 1.2),
) -> Dict[str, Any]:
    """Evaluate stability of integrated centrality-community conclusions across partitions."""
    results: Dict[str, Any] = {}

    # Seed variations at resolution 1.0
    seed_comparisons: Dict[int, Dict[str, Any]] = {}
    for s in seeds:
        _, n2c, _ = detect_louvain_communities(G_undirected, resolution=1.0, seed=s)
        df_s = build_integrated_node_dataframe(G_directed, G_undirected, n2c)
        comp_s = compare_top_nodes_cross_connectivity(df_s, top_percent=0.10)
        seed_comparisons[s] = {
            "top_10_mean_cross_count": comp_s["top_tier"]["mean_cross_count"],
            "rem_90_mean_cross_count": comp_s["remaining_tier"]["mean_cross_count"],
            "top_10_mean_cross_fraction": comp_s["top_tier"]["mean_cross_fraction"],
            "rem_90_mean_cross_fraction": comp_s["remaining_tier"]["mean_cross_fraction"],
            "spearman_pr_vs_cross_count": comp_s["spearman_pagerank_vs_cross_count"]["rho"],
            "spearman_pr_vs_cross_frac": comp_s["spearman_pagerank_vs_cross_fraction"]["rho"],
        }
    results["seed_comparisons"] = seed_comparisons

    # Resolution variations at seed 42
    res_comparisons: Dict[float, Dict[str, Any]] = {}
    for gamma in resolutions:
        _, n2c, _ = detect_louvain_communities(G_undirected, resolution=gamma, seed=42)
        df_r = build_integrated_node_dataframe(G_directed, G_undirected, n2c)
        comp_r = compare_top_nodes_cross_connectivity(df_r, top_percent=0.10)
        res_comparisons[gamma] = {
            "top_10_mean_cross_count": comp_r["top_tier"]["mean_cross_count"],
            "rem_90_mean_cross_count": comp_r["remaining_tier"]["mean_cross_count"],
            "top_10_mean_cross_fraction": comp_r["top_tier"]["mean_cross_fraction"],
            "rem_90_mean_cross_fraction": comp_r["remaining_tier"]["mean_cross_fraction"],
            "spearman_pr_vs_cross_count": comp_r["spearman_pagerank_vs_cross_count"]["rho"],
            "spearman_pr_vs_cross_frac": comp_r["spearman_pagerank_vs_cross_fraction"]["rho"],
        }
    results["resolution_comparisons"] = res_comparisons

    return results
