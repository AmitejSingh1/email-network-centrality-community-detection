"""Regression tests for independent external audit findings."""

import pytest
import networkx as nx
import pandas as pd

from src.data_loader import load_email_network, create_analysis_graph
from src.centrality import compute_centrality_dataframe, compare_raw_vs_analysis_pagerank, compute_pagerank
from src.communities import create_undirected_projection, detect_louvain_communities
from src.evaluation import build_integrated_node_dataframe, analyze_degree_confounding


@pytest.fixture(scope="module")
def real_analysis_graph():
    G_raw, _ = load_email_network()
    G_an = create_analysis_graph(G_raw)
    return G_raw, G_an


def test_dangling_and_pure_recipient_counts(real_analysis_graph):
    """Verify exact counts of isolates, pure recipients, and total dangling nodes."""
    _, G_an = real_analysis_graph
    isolates = sum(1 for n in G_an.nodes() if G_an.in_degree(n) == 0 and G_an.out_degree(n) == 0)
    pure_recip = sum(1 for n in G_an.nodes() if G_an.out_degree(n) == 0 and G_an.in_degree(n) > 0)
    dangling = sum(1 for n in G_an.nodes() if G_an.out_degree(n) == 0)
    assert isolates == 19
    assert pure_recip == 162
    assert dangling == 181


def test_node_83_and_365_exact_ranks_and_singleton_raw_rank(real_analysis_graph):
    """Verify exact deterministic ranks for Nodes 83, 365 and tied singleton ranks."""
    G_raw, G_an = real_analysis_graph
    cent_df = compute_centrality_dataframe(G_an)

    r83 = cent_df[cent_df["node_id"] == 83].iloc[0]
    assert int(r83["in_degree"]) == 85
    assert int(r83["in_degree_rank_unique"]) == 46
    assert int(r83["pagerank_rank_unique"]) == 60

    r365 = cent_df[cent_df["node_id"] == 365].iloc[0]
    assert int(r365["pagerank_rank_unique"]) == 40
    assert G_an.out_degree(365) == 1

    comp = compare_raw_vs_analysis_pagerank(G_raw, G_an)
    assert abs(comp["spearman_rho"] - 0.8720) < 1e-3

    pr_raw = compute_pagerank(G_raw)
    isolates = [n for n in G_an.nodes() if G_an.degree(n) == 0]
    iso_pr = pr_raw[isolates[0]]
    # Competition rank of tied isolates in G_raw is 278 (277 nodes strictly higher)
    strictly_higher = sum(1 for v in pr_raw.values() if v > iso_pr + 1e-12)
    assert strictly_higher + 1 == 278


def test_min_department_conductance_and_contingency(real_analysis_graph):
    """Verify min department conductance (Dept 14: 0.3010) and Louvain contingency counts."""
    _, G_an = real_analysis_graph
    G_un, _ = create_undirected_projection(G_an)
    n2d = {n: G_an.nodes[n]["department"] for n in G_an.nodes()}
    dept_sets = {}
    for n, d in n2d.items():
        dept_sets.setdefault(d, set()).add(n)

    min_dept, min_cond = min(((d, nx.conductance(G_un, s)) for d, s in dept_sets.items()), key=lambda x: x[1])
    assert min_dept == 14
    assert abs(min_cond - 0.3010) < 1e-3

    _, n2c, _ = detect_louvain_communities(G_un, resolution=1.0, seed=42)
    ct = pd.crosstab(pd.Series(n2d), pd.Series(n2c))
    assert ct.loc[0, 4] == 46
    assert ct.loc[7, 4] == 48
    assert ct.loc[10, 5] == 38
    assert ct.loc[4, 3] == 93
    assert ct.loc[1, 1] == 43
    assert ct.loc[1, 4] == 16
    assert ct.loc[1, 2] == 3


def test_degree_quartile_strata_and_q4_counts(real_analysis_graph):
    """Verify non-isolated quartile sizes (N=986) and Q4 Top-10% counts (100 vs 147)."""
    _, G_an = real_analysis_graph
    G_un, _ = create_undirected_projection(G_an)
    _, n2c, _ = detect_louvain_communities(G_un, resolution=1.0, seed=42)
    int_df = build_integrated_node_dataframe(G_an, G_un, n2c)
    conf = analyze_degree_confounding(int_df)

    assert conf["num_evaluated_nodes"] == 986
    assert conf["strata_results"]["Q1"]["sample_size"] == 247
    assert conf["strata_results"]["Q2"]["sample_size"] == 252
    assert conf["strata_results"]["Q3"]["sample_size"] == 240
    assert conf["strata_results"]["Q4"]["sample_size"] == 247
    assert conf["q4_comparison"]["q4_top10_nodes_count"] == 100
    assert conf["q4_comparison"]["q4_remaining_nodes_count"] == 147
    assert abs(conf["partial_correlations"]["pr_vs_cross_count_given_degree"] - (-0.1803)) < 1e-3
