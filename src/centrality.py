"""PageRank and centrality analysis module for Email-Eu-core.

Computes PageRank, in-degree centrality, rank comparisons (Spearman correlation,
top-k Jaccard overlap), structural ranking disagreements, damping factor
sensitivity analysis, and self-loop robustness evaluations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


def compute_pagerank(
    G: nx.DiGraph,
    alpha: float = 0.85,
    max_iter: int = 500,
    tol: float = 1e-6,
    weight: Optional[str] = None,
) -> Dict[int, float]:
    """Compute PageRank scores on directed graph G using NetworkX.

    Parameters
    ----------
    G : nx.DiGraph
        Directed graph (expected G_analysis with 1,005 nodes).
    alpha : float
        Damping factor (default 0.85).
    max_iter : int
        Maximum power iteration rounds.
    tol : float
        Convergence error tolerance.
    weight : Optional[str]
        Edge attribute for link weights (None for unweighted graph).

    Returns
    -------
    Dict[int, float]
        Dictionary mapping node_id to PageRank score.
    """
    pr = nx.pagerank(G, alpha=alpha, max_iter=max_iter, tol=tol, weight=weight)
    return pr


def compute_centrality_dataframe(
    G: nx.DiGraph, alpha: float = 0.85, tol: float = 1e-6
) -> pd.DataFrame:
    """Construct unified DataFrame comparing PageRank and In-Degree centralities.

    Provides both competition ranking (method='min') and deterministic unique
    ranking with secondary tie-break on node_id.
    """
    pr_scores = compute_pagerank(G, alpha=alpha, tol=tol)
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())

    records = []
    for node in G.nodes():
        records.append(
            {
                "node_id": node,
                "department": G.nodes[node].get("department", -1),
                "pagerank": float(pr_scores[node]),
                "in_degree": int(in_degrees[node]),
                "out_degree": int(out_degrees[node]),
            }
        )

    df = pd.DataFrame(records)

    # Standard competition rank (method='min')
    df["pagerank_rank"] = df["pagerank"].rank(ascending=False, method="min").astype(int)
    df["in_degree_rank"] = df["in_degree"].rank(ascending=False, method="min").astype(int)

    # Strictly deterministic unique rank (ties broken by ascending node_id)
    df = df.sort_values(by=["pagerank", "node_id"], ascending=[False, True]).reset_index(drop=True)
    df["pagerank_rank_unique"] = np.arange(1, len(df) + 1)

    df = df.sort_values(by=["in_degree", "node_id"], ascending=[False, True]).reset_index(drop=True)
    df["in_degree_rank_unique"] = np.arange(1, len(df) + 1)

    # Rank difference using unique ranks: positive means higher PR prominence than in-degree rank
    df["rank_difference"] = df["in_degree_rank_unique"] - df["pagerank_rank_unique"]

    df = df.sort_values(by="pagerank_rank_unique", ascending=True).reset_index(drop=True)
    return df


def compute_spearman_rank_correlation(
    df: pd.DataFrame, col1: str = "pagerank", col2: str = "in_degree"
) -> Dict[str, float]:
    """Compute Spearman rank correlation between two centrality measures."""
    rho, p_val = stats.spearmanr(df[col1], df[col2])
    return {
        "spearman_rho": float(rho),
        "p_value": float(p_val),
    }


def compute_top_k_overlap(
    df: pd.DataFrame,
    k: int,
    col1_rank: str = "pagerank_rank_unique",
    col2_rank: str = "in_degree_rank_unique",
) -> Dict[str, Any]:
    """Calculate overlap and Jaccard similarity between top-k individuals under two rankings.

    Formula:
        overlap_fraction = |TopK_1 ∩ TopK_2| / k
    """
    top_k_1 = set(df.sort_values(by=col1_rank)["node_id"].head(k))
    top_k_2 = set(df.sort_values(by=col2_rank)["node_id"].head(k))

    intersection = top_k_1.intersection(top_k_2)
    union = top_k_1.union(top_k_2)

    overlap_count = len(intersection)
    overlap_fraction = float(overlap_count / k) if k > 0 else 0.0
    jaccard = float(overlap_count / len(union)) if union else 0.0

    return {
        "k": k,
        "overlap_count": overlap_count,
        "overlap_fraction": overlap_fraction,
        "jaccard_similarity": jaccard,
        "common_nodes": sorted(list(intersection)),
        "only_col1_nodes": sorted(list(top_k_1 - top_k_2)),
        "only_col2_nodes": sorted(list(top_k_2 - top_k_1)),
    }


def identify_ranking_disagreements(
    df: pd.DataFrame, top_k_threshold: int = 50, rank_diff_threshold: int = 30
) -> Dict[str, pd.DataFrame]:
    """Identify nodes with substantial disagreement between PageRank and In-Degree rankings.

    Categories:
    1. Consistent top: Rank <= top_k_threshold in both PageRank and In-Degree.
    2. PageRank boosted: High PageRank (rank <= top_k_threshold) but much lower In-Degree.
    3. In-Degree boosted: High In-Degree (rank <= top_k_threshold) but much lower PageRank.
    """
    consistent = df[
        (df["pagerank_rank_unique"] <= top_k_threshold)
        & (df["in_degree_rank_unique"] <= top_k_threshold)
    ].sort_values(by="pagerank_rank_unique")

    pr_boosted = df[
        (df["pagerank_rank_unique"] <= top_k_threshold)
        & (df["rank_difference"] >= rank_diff_threshold)
    ].sort_values(by="rank_difference", ascending=False)

    in_degree_boosted = df[
        (df["in_degree_rank_unique"] <= top_k_threshold)
        & (df["rank_difference"] <= -rank_diff_threshold)
    ].sort_values(by="rank_difference", ascending=True)

    return {
        "consistent_top": consistent,
        "pagerank_boosted": pr_boosted,
        "in_degree_boosted": in_degree_boosted,
    }


def analyze_sender_profiles_for_disagreement(
    G: nx.DiGraph, node_id: int, pr_scores: Dict[int, float]
) -> Dict[str, Any]:
    """Investigate incoming link structure explaining why a node's PageRank differs from In-Degree.

    Examines senders' out-degrees L(u) and senders' PageRank scores PR(u).
    """
    incoming_senders = list(G.predecessors(node_id))
    if not incoming_senders:
        return {
            "node_id": node_id,
            "in_degree": 0,
            "mean_sender_out_degree": 0.0,
            "mean_sender_pagerank": 0.0,
            "mean_effective_contribution": 0.0,
        }

    sender_out_degrees = [G.out_degree(u) for u in incoming_senders]
    sender_prs = [pr_scores.get(u, 0.0) for u in incoming_senders]
    contributions = [
        pr_scores.get(u, 0.0) / G.out_degree(u) if G.out_degree(u) > 0 else 0.0
        for u in incoming_senders
    ]

    return {
        "node_id": node_id,
        "in_degree": len(incoming_senders),
        "mean_sender_out_degree": float(np.mean(sender_out_degrees)),
        "median_sender_out_degree": float(np.median(sender_out_degrees)),
        "mean_sender_pagerank": float(np.mean(sender_prs)),
        "total_pr_contribution": float(np.sum(contributions)),
        "mean_effective_contribution": float(np.mean(contributions)),
    }


def run_pagerank_sensitivity(
    G: nx.DiGraph,
    damping_factors: Tuple[float, ...] = (0.75, 0.85, 0.95),
    k_values: Tuple[int, ...] = (10, 20, 50),
    tol: float = 1e-6,
) -> Dict[str, Any]:
    """Evaluate PageRank stability across alternative damping factors.

    Computes pairwise Spearman correlations and top-k overlaps across d in {0.75, 0.85, 0.95}.
    """
    runs: Dict[float, Dict[int, float]] = {}
    rankings: Dict[float, pd.Series] = {}

    for d in damping_factors:
        pr = compute_pagerank(G, alpha=d, tol=tol)
        runs[d] = pr
        # Strictly deterministic ranking (score desc, node_id asc)
        s = pd.Series(pr)
        df_temp = pd.DataFrame({"node_id": s.index, "score": s.values})
        df_temp = df_temp.sort_values(by=["score", "node_id"], ascending=[False, True]).reset_index(drop=True)
        df_temp["rank"] = np.arange(1, len(df_temp) + 1)
        rankings[d] = pd.Series(df_temp["rank"].values, index=df_temp["node_id"])

    # Pairwise Spearman correlations
    pairwise_spearman: Dict[str, float] = {}
    for i in range(len(damping_factors)):
        for j in range(i + 1, len(damping_factors)):
            d1, d2 = damping_factors[i], damping_factors[j]
            rho, _ = stats.spearmanr(rankings[d1].loc[rankings[d2].index], rankings[d2])
            pairwise_spearman[f"d={d1}_vs_d={d2}"] = float(rho)

    # Top-k overlaps across damping factors compared to primary d=0.85
    overlap_results: Dict[str, Any] = {}
    base_d = 0.85
    base_ranks = rankings[base_d]

    for d in damping_factors:
        if d == base_d:
            continue
        d_ranks = rankings[d]
        overlap_results[f"d={base_d}_vs_d={d}"] = {}
        for k in k_values:
            top_base = set(base_ranks.nsmallest(k).index)
            top_d = set(d_ranks.nsmallest(k).index)
            common = top_base.intersection(top_d)
            overlap_results[f"d={base_d}_vs_d={d}"][f"top_{k}"] = {
                "overlap_count": len(common),
                "overlap_fraction": float(len(common) / k),
                "jaccard_similarity": float(len(common) / len(top_base.union(top_d))),
            }

    return {
        "damping_factors": damping_factors,
        "pairwise_spearman": pairwise_spearman,
        "top_k_overlaps": overlap_results,
        "scores_by_damping": runs,
        "rankings_by_damping": rankings,
    }


def compare_raw_vs_analysis_pagerank(
    G_raw: nx.DiGraph,
    G_analysis: nx.DiGraph,
    alpha: float = 0.85,
    k_values: Tuple[int, ...] = (10, 20, 50),
    tol: float = 1e-6,
) -> Dict[str, Any]:
    """Evaluate self-loop robustness by comparing PageRank on G_raw vs. G_analysis at alpha=0.85."""
    pr_raw = compute_pagerank(G_raw, alpha=alpha, tol=tol)
    pr_analysis = compute_pagerank(G_analysis, alpha=alpha, tol=tol)

    df_raw = pd.DataFrame({"node_id": list(pr_raw.keys()), "score_raw": list(pr_raw.values())})
    df_raw = df_raw.sort_values(by=["score_raw", "node_id"], ascending=[False, True]).reset_index(drop=True)
    df_raw["rank_raw"] = np.arange(1, len(df_raw) + 1)

    df_analysis = pd.DataFrame({"node_id": list(pr_analysis.keys()), "score_analysis": list(pr_analysis.values())})
    df_analysis = df_analysis.sort_values(by=["score_analysis", "node_id"], ascending=[False, True]).reset_index(drop=True)
    df_analysis["rank_analysis"] = np.arange(1, len(df_analysis) + 1)

    merged = pd.merge(df_raw, df_analysis, on="node_id")
    rho, p_val = stats.spearmanr(merged["rank_raw"], merged["rank_analysis"])

    top_k_comp: Dict[str, Any] = {}
    for k in k_values:
        top_raw = set(merged.sort_values(by="rank_raw")["node_id"].head(k))
        top_an = set(merged.sort_values(by="rank_analysis")["node_id"].head(k))
        common = top_raw.intersection(top_an)
        top_k_comp[f"top_{k}"] = {
            "overlap_count": len(common),
            "overlap_fraction": float(len(common) / k),
            "jaccard_similarity": float(len(common) / len(top_raw.union(top_an))),
            "raw_only": sorted(list(top_raw - top_an)),
            "analysis_only": sorted(list(top_an - top_raw)),
        }

    return {
        "spearman_rho": float(rho),
        "p_value": float(p_val),
        "top_k_overlap": top_k_comp,
    }
