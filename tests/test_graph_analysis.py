"""Unit tests for graph analysis and exploratory metrics."""

from __future__ import annotations

import networkx as nx
import pytest

from src.data_loader import load_email_network, create_analysis_graph
from src.graph_analysis import (
    compute_degree_statistics,
    compute_department_statistics,
    compute_edge_department_composition,
    compute_reciprocity_statistics,
    compute_component_statistics,
    compute_directed_density,
    compute_uniform_random_reference_model,
    compare_raw_vs_analysis_graphs,
)


@pytest.fixture
def synthetic_graph():
    """Create a minimal synthetic DiGraph with known departmental mappings.

    Nodes:
    - 0: dept 0
    - 1: dept 0
    - 2: dept 1
    - 3: dept 2 (isolated)

    Edges:
    - (0, 1): within dept 0
    - (1, 2): cross dept (0 -> 1)
    - (2, 2): self-loop in dept 1
    """
    G = nx.DiGraph()
    G.add_node(0, department=0)
    G.add_node(1, department=0)
    G.add_node(2, department=1)
    G.add_node(3, department=2)

    G.add_edge(0, 1)
    G.add_edge(1, 2)
    G.add_edge(2, 2)
    return G


def test_synthetic_self_loop_removal(synthetic_graph):
    """Test that create_analysis_graph removes self-loops without losing nodes."""
    G_analysis = create_analysis_graph(synthetic_graph)

    assert G_analysis.number_of_nodes() == 4
    assert G_analysis.number_of_edges() == 2
    assert nx.number_of_selfloops(G_analysis) == 0
    assert G_analysis.has_node(2)
    assert G_analysis.degree(2) == 1  # (1, 2) incoming edge
    assert G_analysis.degree(3) == 0  # isolated node preserved


def test_synthetic_degree_statistics(synthetic_graph):
    """Test degree computation on synthetic graph."""
    stats = compute_degree_statistics(synthetic_graph)

    assert stats["num_nodes"] == 4
    # In-degrees: 0: 0, 1: 1, 2: 2, 3: 0
    assert stats["in_degree"]["max"] == 2
    assert stats["in_degree"]["min"] == 0
    assert stats["in_degree"]["mean"] == 0.75

    # Out-degrees: 0: 1, 1: 1, 2: 1, 3: 0
    assert stats["out_degree"]["max"] == 1
    assert stats["out_degree"]["min"] == 0
    assert stats["out_degree"]["mean"] == 0.75


def test_synthetic_department_statistics(synthetic_graph):
    """Test departmental membership size distributions on synthetic graph."""
    stats = compute_department_statistics(synthetic_graph)

    assert stats["num_departments"] == 3
    assert stats["department_sizes"][0] == 2
    assert stats["department_sizes"][1] == 1
    assert stats["department_sizes"][2] == 1
    assert stats["min_size"] == 1
    assert stats["max_size"] == 2


def test_synthetic_edge_composition_with_and_without_self_loops(synthetic_graph):
    """Test within-dept vs cross-dept breakdown with and without self loops."""
    # With self-loops: (0, 1) within, (1, 2) cross, (2, 2) within
    comp_with = compute_edge_department_composition(synthetic_graph, exclude_self_loops=False)
    assert comp_with["total_evaluated_edges"] == 3
    assert comp_with["within_dept_edges"] == 2
    assert comp_with["cross_dept_edges"] == 1
    assert comp_with["self_loops_count"] == 1
    assert comp_with["within_dept_fraction"] == pytest.approx(2 / 3)
    assert comp_with["cross_dept_fraction"] == pytest.approx(1 / 3)

    # Without self-loops: (0, 1) within, (1, 2) cross
    comp_no = compute_edge_department_composition(synthetic_graph, exclude_self_loops=True)
    assert comp_no["total_evaluated_edges"] == 2
    assert comp_no["within_dept_edges"] == 1
    assert comp_no["cross_dept_edges"] == 1
    assert comp_no["self_loops_count"] == 1
    assert comp_no["within_dept_fraction"] == pytest.approx(0.5)
    assert comp_no["cross_dept_fraction"] == pytest.approx(0.5)


def test_synthetic_uniform_random_reference_model(synthetic_graph):
    """Test analytical uniform random reference model on synthetic graph.

    Nodes = 4. Dept sizes: S_0 = 2, S_1 = 1, S_2 = 1.
    Total ordered pairs: 4 * 3 = 12.
    Same dept ordered pairs: 2*(2-1) + 1*(0) + 1*(0) = 2.
    Expected within fraction: 2 / 12 = 1/6 ~ 0.1667.
    """
    ref = compute_uniform_random_reference_model(synthetic_graph)
    assert ref["total_possible_ordered_pairs"] == 12
    assert ref["within_dept_possible_pairs"] == 2
    assert ref["expected_within_fraction"] == pytest.approx(1 / 6)
    assert ref["expected_cross_fraction"] == pytest.approx(5 / 6)


def test_synthetic_density_calculation(synthetic_graph):
    """Test directed density with and without self-loops."""
    # 4 nodes, 3 edges (one self-loop)
    dens_raw = compute_directed_density(synthetic_graph, allow_self_loops=True)
    assert dens_raw["max_possible_edges"] == 16
    assert dens_raw["density"] == pytest.approx(3 / 16)

    dens_analysis = compute_directed_density(synthetic_graph, allow_self_loops=False)
    assert dens_analysis["max_possible_edges"] == 12
    assert dens_analysis["density"] == pytest.approx(3 / 12)


# --- Real Dataset Tests ---

@pytest.fixture(scope="session")
def real_graphs():
    """Load real SNAP graphs G_raw and G_analysis."""
    G_raw, _ = load_email_network()
    G_analysis = create_analysis_graph(G_raw)
    return G_raw, G_analysis


def test_real_dataset_self_loop_removal(real_graphs):
    """Verify that G_analysis correctly removes all 642 self-loops and retains all 1,005 nodes."""
    G_raw, G_analysis = real_graphs

    assert G_raw.number_of_nodes() == 1005
    assert G_raw.number_of_edges() == 25571
    assert nx.number_of_selfloops(G_raw) == 642

    assert G_analysis.number_of_nodes() == 1005
    assert G_analysis.number_of_edges() == 24929
    assert nx.number_of_selfloops(G_analysis) == 0

    # Invariant: exactly 25,571 - 642 = 24,929 edges
    assert G_raw.number_of_edges() - G_analysis.number_of_edges() == 642


def test_real_dataset_zero_degree_nodes(real_graphs):
    """Verify that G_analysis has exactly 19 zero-degree nodes with preserved department labels."""
    G_raw, G_analysis = real_graphs

    # In G_raw, all nodes have degree >= 1 because the 19 singletons have self-loops
    raw_zero_degree = [n for n in G_raw.nodes() if G_raw.degree(n) == 0]
    assert len(raw_zero_degree) == 0

    # In G_analysis, the 19 singletons become zero-degree nodes
    analysis_zero_degree = [n for n in G_analysis.nodes() if G_analysis.degree(n) == 0]
    assert len(analysis_zero_degree) == 19

    # Verify that all 19 zero-degree nodes retain valid department attributes
    for n in analysis_zero_degree:
        assert "department" in G_analysis.nodes[n]
        assert isinstance(G_analysis.nodes[n]["department"], int)


def test_real_dataset_exploratory_metrics(real_graphs):
    """Verify that exploratory metrics on real Email-Eu-core satisfy exact mathematical identities."""
    G_raw, G_analysis = real_graphs

    degree_stats = compute_degree_statistics(G_analysis)
    assert degree_stats["num_nodes"] == 1005
    assert sum(degree_stats["in_degree"]["values"]) == 24929
    assert sum(degree_stats["out_degree"]["values"]) == 24929

    # Department analysis
    dept_stats = compute_department_statistics(G_analysis)
    assert dept_stats["num_departments"] == 42
    assert sum(dept_stats["department_sizes"].values()) == 1005

    # Edge composition
    comp = compute_edge_department_composition(G_analysis, exclude_self_loops=True)
    assert comp["total_evaluated_edges"] == 24929
    assert comp["within_dept_edges"] + comp["cross_dept_edges"] == 24929

    # Check homophily enrichment
    ref_model = compute_uniform_random_reference_model(G_analysis)
    assert 0.04 < ref_model["expected_within_fraction"] < 0.05
    assert comp["within_dept_fraction"] == pytest.approx(8645 / 24929, rel=1e-4)
    assert comp["cross_dept_fraction"] == pytest.approx(16284 / 24929, rel=1e-4)
    assert comp["homophily_enrichment_ratio"] > 7.0  # Greater than 7x enrichment over uniform random


def test_real_dataset_reciprocity_identities(real_graphs):
    """Verify directed reciprocity calculations and edge-level decomposition on Email-Eu-core."""
    G_raw, G_analysis = real_graphs

    recip_stats = compute_reciprocity_statistics(G_raw)

    # G_raw reciprocity: 17,730 / 25,571 = 0.69336...
    assert 0.693 < recip_stats["reciprocity_with_self_loops"] < 0.694

    # G_analysis reciprocity: 17,730 / 24,929 = 0.71122...
    assert 0.711 < recip_stats["reciprocity_no_self_loops"] < 0.712
    assert recip_stats["num_self_loops"] == 642

    # Exact pair counts in G_analysis
    assert recip_stats["num_reciprocal_pairs_no_self"] == 8865
    assert recip_stats["num_reciprocal_directed_edges_no_self"] == 17730
    assert recip_stats["num_unreciprocated_directed_edges_no_self"] == 7199

    # Partition identity: reciprocal + unreciprocated = total edges (24,929)
    assert (
        recip_stats["num_reciprocal_directed_edges_no_self"]
        + recip_stats["num_unreciprocated_directed_edges_no_self"]
        == 24929
    )

    # Fractions sum to exactly 1.0
    recip_frac = recip_stats["reciprocity_no_self_loops"]
    unrecip_frac = recip_stats["unreciprocated_fraction_no_self"]
    assert abs((recip_frac + unrecip_frac) - 1.0) < 1e-9


