"""Automated verification suite for integrated centrality and community evaluation."""

from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from src.data_loader import load_email_network, create_analysis_graph
from src.communities import create_undirected_projection, detect_louvain_communities
from src.evaluation import (
    analyze_degree_confounding,
    build_integrated_node_dataframe,
    compare_top_nodes_cross_connectivity,
    compute_community_level_summaries,
    select_case_study_nodes,
    run_integrated_robustness,
)


@pytest.fixture
def synthetic_integrated_graph():
    """Create a synthetic graph with known community structure and centrality.

    Two communities:
    - Community 0: Nodes 0, 1, 2
    - Community 1: Nodes 3, 4
    - Isolated: Node 5

    Edges:
    - Internal Comm 0: (0, 1), (1, 0), (1, 2), (2, 1), (2, 0), (0, 2)
    - Internal Comm 1: (3, 4), (4, 3)
    - Bridge edge: (0, 3), (3, 0)
    - Node 5 is isolated
    """
    G_dir = nx.DiGraph()
    G_dir.add_nodes_from([0, 1, 2], department=0)
    G_dir.add_nodes_from([3, 4], department=1)
    G_dir.add_node(5, department=2)

    # Comm 0 internal cycle
    G_dir.add_edges_from([(0, 1), (1, 0), (1, 2), (2, 1), (2, 0), (0, 2)])
    # Comm 1 internal
    G_dir.add_edges_from([(3, 4), (4, 3)])
    # Bridge
    G_dir.add_edges_from([(0, 3), (3, 0)])

    G_undir = G_dir.to_undirected()
    node_to_comm = {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 2}
    return G_dir, G_undir, node_to_comm


def test_synthetic_integrated_dataframe_and_nan_handling(synthetic_integrated_graph):
    """Test unified dataframe assembly and zero-degree NaN handling."""
    G_dir, G_undir, node_to_comm = synthetic_integrated_graph
    df = build_integrated_node_dataframe(G_dir, G_undir, node_to_comm)

    assert len(df) == 6
    # Node 0 has 2 internal edges (1, 2) and 1 cross edge (3)
    row_0 = df[df["node_id"] == 0].iloc[0]
    assert row_0["internal_edges_count"] == 2
    assert row_0["cross_community_count"] == 1
    assert row_0["total_undirected_degree"] == 3
    assert row_0["cross_community_fraction"] == pytest.approx(1 / 3)

    # Node 5 is isolated: total degree = 0, cross fraction must be NaN
    row_5 = df[df["node_id"] == 5].iloc[0]
    assert row_5["total_undirected_degree"] == 0
    assert np.isnan(row_5["cross_community_fraction"])


def test_synthetic_compare_top_nodes(synthetic_integrated_graph):
    """Test top nodes comparison statistics on synthetic graph."""
    G_dir, G_undir, node_to_comm = synthetic_integrated_graph
    df = build_integrated_node_dataframe(G_dir, G_undir, node_to_comm)
    comp = compare_top_nodes_cross_connectivity(df, top_percent=0.33)  # Top 2 nodes

    assert comp["n_top"] == 2
    assert comp["n_remaining"] == 4
    assert np.isfinite(comp["top_tier"]["mean_cross_count"])
    assert np.isfinite(comp["remaining_tier"]["mean_cross_count"])


def test_synthetic_community_summaries(synthetic_integrated_graph):
    """Test community-level summary metrics computation."""
    G_dir, G_undir, node_to_comm = synthetic_integrated_graph
    df = build_integrated_node_dataframe(G_dir, G_undir, node_to_comm)
    communities = [{0, 1, 2}, {3, 4}, {5}]
    summary = compute_community_level_summaries(G_undir, df, communities)

    assert len(summary) == 3
    # Community 0 has 3 members, 1 department, 3 internal edges
    c0 = summary[summary["comm_id"] == 0].iloc[0]
    assert c0["size"] == 3
    assert c0["num_departments"] == 1
    assert c0["internal_edges"] == 3
    assert c0["external_cut_edges"] == 1  # edge {0, 3}


# --- Real Dataset Tests ---

@pytest.fixture(scope="session")
def real_integrated_data():
    """Load real graphs and construct integrated DataFrame."""
    G_raw, _ = load_email_network()
    G_analysis = create_analysis_graph(G_raw)
    G_undir, _ = create_undirected_projection(G_analysis)
    comms, node_to_comm, q = detect_louvain_communities(G_undir, resolution=1.0, seed=42)
    df = build_integrated_node_dataframe(G_analysis, G_undir, node_to_comm)
    return G_analysis, G_undir, comms, node_to_comm, df


def test_real_dataset_integrated_dataframe_invariants(real_integrated_data):
    """Verify invariants of the real integrated node DataFrame."""
    _, _, _, _, df = real_integrated_data

    # 1. Total row count exactly 1,005
    assert len(df) == 1005

    # 2. Exactly 19 nodes have NaN cross_community_fraction (the 19 isolates)
    nan_rows = df[df["cross_community_fraction"].isna()]
    assert len(nan_rows) == 19
    for _, r in nan_rows.iterrows():
        assert r["total_undirected_degree"] == 0
        assert r["in_degree"] == 0
        assert r["out_degree"] == 0

    # 3. All non-isolated nodes have fractions in [0, 1]
    valid_df = df.dropna(subset=["cross_community_fraction"])
    assert len(valid_df) == 1005 - 19
    assert valid_df["cross_community_fraction"].min() >= 0.0
    assert valid_df["cross_community_fraction"].max() <= 1.0


def test_real_dataset_top_nodes_connectivity_advantage(real_integrated_data):
    """Verify that top 10% PageRank individuals possess substantially higher cross-community connectivity."""
    _, _, _, _, df = real_integrated_data
    comp = compare_top_nodes_cross_connectivity(df, top_percent=0.10)

    # 1. Sample partition sizes
    assert comp["n_top"] == 101
    assert comp["n_remaining"] == 904

    # 2. Top 10% has much higher mean cross-community connections count
    mean_top_count = comp["top_tier"]["mean_cross_count"]
    mean_rem_count = comp["remaining_tier"]["mean_cross_count"]
    assert mean_top_count > 50.0  # Top 10% averages ~67.9 cross edges
    assert mean_rem_count < 15.0  # Remaining 90% averages ~7.9 cross edges
    assert mean_top_count > 5.0 * mean_rem_count

    # 3. Top 10% has much higher mean cross-community fraction
    mean_top_frac = comp["top_tier"]["mean_cross_fraction"]
    mean_rem_frac = comp["remaining_tier"]["mean_cross_fraction"]
    assert mean_top_frac > 0.50  # Over half of top-nodes links cross community lines (~55.8%)
    assert mean_rem_frac < 0.35  # Only ~26.6% for remaining nodes
    assert mean_top_frac > 1.8 * mean_rem_frac

    # 4. Statistical tests confirm strong distributional divergence
    assert comp["mann_whitney_count"]["p_value"] < 1e-20
    assert comp["mann_whitney_fraction"]["p_value"] < 1e-20

    # 5. PageRank correlation with cross-community count is strong
    assert comp["spearman_pagerank_vs_cross_count"]["rho"] > 0.70


def test_real_dataset_case_studies(real_integrated_data):
    """Verify that contrasting individual case study archetypes exist in empirical data."""
    _, _, _, _, df = real_integrated_data
    cases = select_case_study_nodes(df)

    # High PR, High Cross (Global Spanners)
    assert not cases["high_pr_bridge"].empty
    # High PR, Moderate/Lower Cross (Internal Hubs)
    assert not cases["high_pr_hub"].empty
    # Low PR, High Cross Fraction (Peripheral Bridges)
    assert not cases["peripheral_bridge"].empty


def test_real_dataset_integrated_robustness(real_integrated_data):
    """Verify that top-10% cross-connectivity advantage holds across seeds and resolutions."""
    G_analysis, G_undir, _, _, _ = real_integrated_data
    rob = run_integrated_robustness(G_analysis, G_undir, seeds=(42, 123), resolutions=(0.8, 1.0, 1.2))

    for s, metrics in rob["seed_comparisons"].items():
        assert metrics["top_10_mean_cross_count"] > 4.0 * metrics["rem_90_mean_cross_count"]
        assert metrics["top_10_mean_cross_fraction"] > 1.5 * metrics["rem_90_mean_cross_fraction"]

    for r, metrics in rob["resolution_comparisons"].items():
        assert metrics["top_10_mean_cross_count"] > 3.0 * metrics["rem_90_mean_cross_count"]
        assert metrics["top_10_mean_cross_fraction"] > 1.4 * metrics["rem_90_mean_cross_fraction"]


def test_real_dataset_degree_confounding(real_integrated_data):
    """Verify degree confounding analysis and stratified comparisons."""
    _, _, _, _, df = real_integrated_data

    conf = analyze_degree_confounding(df, n_strata=4)

    assert conf["num_evaluated_nodes"] == 986

    # 1. Bivariate correlations confirm strong degree confounding
    biv = conf["bivariate_correlations"]
    assert biv["pr_vs_degree"] > 0.90
    assert biv["cross_count_vs_degree"] > 0.85
    assert biv["cross_fraction_vs_degree"] > 0.50

    # 2. Partial correlation controlling for degree attenuates global association
    part = conf["partial_correlations"]
    assert -0.25 < part["pr_vs_cross_count_given_degree"] < 0.05
    assert -0.25 < part["pr_vs_cross_fraction_given_degree"] < 0.05

    # 3. High-degree stratum Q4 deep-dive
    q4 = conf["q4_comparison"]
    assert q4["q4_total_nodes"] == 247
    assert q4["top10_in_q4_fraction"] > 0.95  # 100 of 101 top PageRank nodes are in Q4
    assert q4["q4_top10_mean_cross_count"] > 2.0 * q4["q4_rem_mean_cross_count"]
    assert q4["q4_top10_mean_cross_fraction"] > q4["q4_rem_mean_cross_fraction"]
    assert q4["q4_mann_whitney_fraction"]["p_value"] < 1e-5


def test_real_dataset_exact_case_study_metrics(real_integrated_data):
    """Regression test ensuring exact case study metrics match the authoritative manifest."""
    _, G_undir, _, _, df = real_integrated_data

    # Node 160: Global Boundary Spanner
    n160 = df[df["node_id"] == 160].iloc[0]
    assert n160["department"] == 36
    assert n160["comm_id"] == 4
    assert n160["pagerank_rank_unique"] == 1
    assert n160["in_degree"] == 211
    assert n160["total_undirected_degree"] == 345
    assert n160["internal_edges_count"] == 51
    assert n160["cross_community_count"] == 294
    assert round(n160["cross_community_fraction"] * 100, 2) == 85.22
    ext_160 = len(set(df[df["node_id"] == v]["comm_id"].iloc[0] for v in G_undir.neighbors(160) if df[df["node_id"] == v]["comm_id"].iloc[0] != 4))
    assert ext_160 == 8

    # Node 451: Internal Hub
    n451 = df[df["node_id"] == 451].iloc[0]
    assert n451["department"] == 14
    assert n451["comm_id"] == 6
    assert n451["pagerank_rank_unique"] == 37
    assert n451["in_degree"] == 8
    assert n451["in_degree_rank_unique"] == 659
    assert n451["in_degree_rank_unique"] - n451["pagerank_rank_unique"] == 622
    assert n451["total_undirected_degree"] == 13
    assert n451["internal_edges_count"] == 13
    assert n451["cross_community_count"] == 0
    assert n451["cross_community_fraction"] == 0.0

    # Node 644: Peripheral Bridge
    n644 = df[df["node_id"] == 644].iloc[0]
    assert n644["department"] == 25
    assert n644["comm_id"] == 7
    assert n644["pagerank_rank_unique"] == 633
    assert n644["in_degree"] == 11
    assert n644["in_degree_rank_unique"] == 606
    assert n644["total_undirected_degree"] == 15
    assert n644["internal_edges_count"] == 2
    assert n644["cross_community_count"] == 13
    assert round(n644["cross_community_fraction"] * 100, 2) == 86.67


