"""Automated verification suite for PageRank and centrality analysis."""

from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from src.data_loader import load_email_network, create_analysis_graph
from src.centrality import (
    compute_pagerank,
    compute_centrality_dataframe,
    compute_spearman_rank_correlation,
    compute_top_k_overlap,
    identify_ranking_disagreements,
    analyze_sender_profiles_for_disagreement,
    run_pagerank_sensitivity,
    compare_raw_vs_analysis_pagerank,
)


@pytest.fixture
def synthetic_digraph():
    """Create a 5-node synthetic DiGraph with known structural properties.

    Topology:
    - Node 0 -> Node 1, Node 2
    - Node 1 -> Node 2
    - Node 2 -> Node 0 (creates cycle 0 -> 1 -> 2 -> 0)
    - Node 3 -> Node 2 (dangling predecessor: out-degree 1)
    - Node 4 is completely isolated (degree 0)
    """
    G = nx.DiGraph()
    G.add_nodes_from([0, 1, 2, 3, 4], department=0)
    G.add_edge(0, 1)
    G.add_edge(0, 2)
    G.add_edge(1, 2)
    G.add_edge(2, 0)
    G.add_edge(3, 2)
    return G


def test_synthetic_pagerank_normalization_and_finiteness(synthetic_digraph):
    """Verify that PageRank scores are finite, non-negative, and sum to 1."""
    pr = compute_pagerank(synthetic_digraph, alpha=0.85)

    assert len(pr) == 5
    for node, score in pr.items():
        assert np.isfinite(score)
        assert score > 0.0

    assert sum(pr.values()) == pytest.approx(1.0, abs=1e-5)


def test_synthetic_isolated_and_dangling_nodes(synthetic_digraph):
    """Verify that isolated and dangling nodes are handled properly and receive valid scores."""
    pr = compute_pagerank(synthetic_digraph, alpha=0.85)

    # Node 4 is isolated: receives teleportation + dangling redistribution mass
    assert pr[4] > 0.0
    # Node 2 receives multiple endorsements, including from dangling predecessor 3
    assert pr[2] > pr[4]


def test_synthetic_centrality_dataframe_and_tie_handling(synthetic_digraph):
    """Test deterministic unique ranking and tie handling."""
    df = compute_centrality_dataframe(synthetic_digraph, alpha=0.85)

    assert len(df) == 5
    assert set(df["node_id"]) == {0, 1, 2, 3, 4}
    # Unique ranks must form a strict permutation of 1..5
    assert sorted(df["pagerank_rank_unique"].tolist()) == [1, 2, 3, 4, 5]
    assert sorted(df["in_degree_rank_unique"].tolist()) == [1, 2, 3, 4, 5]


def test_synthetic_top_k_overlap(synthetic_digraph):
    """Test top-k overlap computation on synthetic graph."""
    df = compute_centrality_dataframe(synthetic_digraph, alpha=0.85)

    res_k2 = compute_top_k_overlap(df, k=2)
    assert res_k2["k"] == 2
    assert 0 <= res_k2["overlap_count"] <= 2
    assert res_k2["overlap_fraction"] == res_k2["overlap_count"] / 2.0
    assert 0.0 <= res_k2["jaccard_similarity"] <= 1.0


def test_synthetic_sensitivity_runs(synthetic_digraph):
    """Test damping factor sensitivity analysis on synthetic graph."""
    sens = run_pagerank_sensitivity(synthetic_digraph, damping_factors=(0.75, 0.85, 0.95), k_values=(2,))

    assert "d=0.75_vs_d=0.85" in sens["pairwise_spearman"]
    assert "d=0.85_vs_d=0.95" in sens["pairwise_spearman"]
    for rho in sens["pairwise_spearman"].values():
        assert -1.0 <= rho <= 1.0


# --- Real Dataset Tests ---

@pytest.fixture(scope="session")
def real_analysis_graph():
    """Load real SNAP graphs G_raw and G_analysis."""
    G_raw, _ = load_email_network()
    G_analysis = create_analysis_graph(G_raw)
    return G_raw, G_analysis


def test_real_dataset_pagerank_validity(real_analysis_graph):
    """Verify that PageRank on real G_analysis produces normalized, finite scores across all 1,005 nodes."""
    _, G_analysis = real_analysis_graph
    pr = compute_pagerank(G_analysis, alpha=0.85, tol=1e-6)

    assert len(pr) == 1005
    for node, score in pr.items():
        assert np.isfinite(score)
        assert score >= 0.0

    assert sum(pr.values()) == pytest.approx(1.0, abs=1e-5)


def test_real_dataset_centrality_comparison(real_analysis_graph):
    """Verify centrality correlation, top-k overlaps, and disagreement identification."""
    _, G_analysis = real_analysis_graph
    df = compute_centrality_dataframe(G_analysis, alpha=0.85)

    # 1. Row count and node universe
    assert len(df) == 1005

    # 2. Spearman correlation
    corr = compute_spearman_rank_correlation(df, "pagerank", "in_degree")
    assert corr["spearman_rho"] > 0.95  # Very high overall monotonic association (~0.983)
    assert corr["p_value"] < 1e-10

    # 3. Top-k overlaps for k in {10, 20, 50}
    for k in [10, 20, 50]:
        res = compute_top_k_overlap(df, k=k)
        assert res["overlap_count"] <= k
        assert 0.50 <= res["overlap_fraction"] <= 1.0  # High but non-identical overlap

    # 4. Disagreement detection
    disagreements = identify_ranking_disagreements(df, top_k_threshold=50, rank_diff_threshold=30)
    assert not disagreements["consistent_top"].empty


def test_real_dataset_damping_sensitivity(real_analysis_graph):
    """Verify sensitivity across alpha in {0.75, 0.85, 0.95}."""
    _, G_analysis = real_analysis_graph
    sens = run_pagerank_sensitivity(G_analysis, damping_factors=(0.75, 0.85, 0.95), k_values=(10, 20, 50))

    # High rank correlation across damping factors
    assert sens["pairwise_spearman"]["d=0.75_vs_d=0.85"] > 0.95
    assert sens["pairwise_spearman"]["d=0.85_vs_d=0.95"] > 0.95


def test_real_dataset_self_loop_robustness(real_analysis_graph):
    """Verify that PageRank on G_raw vs G_analysis exhibits substantial rank shifts due to self-loop trapping."""
    G_raw, G_analysis = real_analysis_graph
    comp = compare_raw_vs_analysis_pagerank(G_raw, G_analysis, alpha=0.85, k_values=(10, 20, 50))

    # Correlation is ~0.8720 (average tie-ranks on scores; ~0.8732 on deterministic unique ranks)
    assert 0.85 < comp["spearman_rho"] < 0.92
    # Top-k overlaps between raw and analysis models
    assert comp["top_k_overlap"]["top_10"]["overlap_fraction"] >= 0.70
    assert comp["top_k_overlap"]["top_20"]["overlap_fraction"] >= 0.80
    assert comp["top_k_overlap"]["top_50"]["overlap_fraction"] >= 0.90

