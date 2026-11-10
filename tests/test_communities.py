"""Automated verification suite for Louvain community detection and department alignment."""

from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from src.data_loader import load_email_network, create_analysis_graph
from src.communities import (
    create_undirected_projection,
    detect_louvain_communities,
    evaluate_community_conductance,
    compare_communities_with_departments,
    run_louvain_robustness,
)


@pytest.fixture
def synthetic_multigraph():
    """Create a 6-node synthetic DiGraph with known communities and department labels.

    Cluster A: Nodes 0, 1, 2 (all Dept 0)
    Cluster B: Nodes 3, 4 (both Dept 1)
    Isolated: Node 5 (Dept 2)

    Directed edges:
    - (0, 1) and (1, 0) -> reciprocal pair (should collapse to 1 undirected edge)
    - (1, 2) -> unreciprocated
    - (2, 0) -> unreciprocated
    - (3, 4) and (4, 3) -> reciprocal pair
    - (0, 3) -> cross-cluster unreciprocated link
    Total directed edges: 7
    Reciprocal pairs: 2 (4 directed edges)
    Unreciprocated: 3 directed edges
    Expected undirected edges: 2 + 3 = 5
    """
    G = nx.DiGraph()
    G.add_nodes_from([0, 1, 2], department=0)
    G.add_nodes_from([3, 4], department=1)
    G.add_node(5, department=2)

    G.add_edge(0, 1)
    G.add_edge(1, 0)
    G.add_edge(1, 2)
    G.add_edge(2, 0)
    G.add_edge(3, 4)
    G.add_edge(4, 3)
    G.add_edge(0, 3)
    return G


def test_synthetic_undirected_projection(synthetic_multigraph):
    """Test reciprocal-edge collapsing and node preservation in undirected projection."""
    G_undir, audit = create_undirected_projection(synthetic_multigraph)

    assert G_undir.number_of_nodes() == 6
    assert G_undir.number_of_edges() == 5
    assert nx.number_of_selfloops(G_undir) == 0
    assert audit["reciprocal_pairs_collapsed"] == 2
    assert audit["unreciprocated_directed_edges"] == 3
    assert G_undir.has_edge(0, 1)
    assert G_undir.has_edge(3, 4)
    assert G_undir.has_edge(0, 3)
    assert G_undir.degree(5) == 0  # Node 5 remains isolated


def test_synthetic_louvain_partition_invariants(synthetic_multigraph):
    """Test partition completeness, non-overlapping assignments, and deterministic IDs."""
    G_undir, _ = create_undirected_projection(synthetic_multigraph)
    comms, node_to_comm, q = detect_louvain_communities(G_undir, resolution=1.0, seed=42)

    # 1. Complete coverage
    all_assigned_nodes = set().union(*comms)
    assert all_assigned_nodes == set(G_undir.nodes())
    assert len(node_to_comm) == 6

    # 2. Non-overlapping partitions
    total_len = sum(len(c) for c in comms)
    assert total_len == 6

    # 3. Deterministic order: community 0 must be largest
    assert len(comms[0]) >= len(comms[-1])

    # 4. Modularity is a valid float
    assert np.isfinite(q)


def test_synthetic_conductance_handling(synthetic_multigraph):
    """Test conductance calculation and graceful handling of degenerate singletons."""
    G_undir, _ = create_undirected_projection(synthetic_multigraph)
    comms, _, _ = detect_louvain_communities(G_undir, resolution=1.0, seed=42)
    cond = evaluate_community_conductance(G_undir, comms)

    # Isolated node 5 should be excluded from non-trivial conductance evaluation
    assert cond["evaluated_communities_count"] >= 1
    assert 0.0 <= cond["min_conductance"] <= 1.0
    assert 0.0 <= cond["max_conductance"] <= 1.0


def test_synthetic_department_comparison_metrics(synthetic_multigraph):
    """Test NMI, ARI, and contingency matrix on synthetic graph."""
    G_undir, _ = create_undirected_projection(synthetic_multigraph)
    comms, node_to_comm, _ = detect_louvain_communities(G_undir, resolution=1.0, seed=42)
    comp = compare_communities_with_departments(G_undir, node_to_comm)

    assert 0.0 <= comp["nmi"] <= 1.0
    assert -1.0 <= comp["ari"] <= 1.0
    assert np.isfinite(comp["department_modularity"])
    assert not comp["contingency_matrix"].empty


# --- Real Dataset Tests ---

@pytest.fixture(scope="session")
def real_undirected_graph():
    """Load real SNAP graphs and construct undirected projection."""
    G_raw, _ = load_email_network()
    G_analysis = create_analysis_graph(G_raw)
    G_undir, audit = create_undirected_projection(G_analysis)
    return G_analysis, G_undir, audit


def test_real_dataset_undirected_projection(real_undirected_graph):
    """Verify invariants of real undirected projection G_undir."""
    G_analysis, G_undir, audit = real_undirected_graph

    # Exactly 1,005 nodes preserved
    assert G_undir.number_of_nodes() == 1005
    # Invariant: 24,929 directed edges collapse to 16,064 undirected edges
    assert G_undir.number_of_edges() == 16064
    assert nx.number_of_selfloops(G_undir) == 0

    # Exactly 19 isolated nodes with degree 0
    isolated_nodes = [n for n in G_undir.nodes() if G_undir.degree(n) == 0]
    assert len(isolated_nodes) == 19

    # Reciprocal directed edge calculations
    # 24,929 - 16,064 = 8,865 reciprocal pairs (17,730 directed edges)
    assert audit["reciprocal_pairs_collapsed"] == 24929 - 16064
    assert audit["reciprocal_directed_edges"] == 2 * (24929 - 16064)


def test_real_dataset_louvain_partition_properties(real_undirected_graph):
    """Verify primary Louvain community detection results on real Email-Eu-core."""
    _, G_undir, _ = real_undirected_graph
    comms, node_to_comm, q = detect_louvain_communities(G_undir, resolution=1.0, seed=42)

    # 1. Total communities: 28 (9 non-trivial communities + 19 isolates)
    assert len(comms) == 28
    non_trivial = [c for c in comms if len(c) > 1]
    singletons = [c for c in comms if len(c) == 1]
    assert len(non_trivial) == 9
    assert len(singletons) == 19

    # 2. Perfect partition coverage
    assert sum(len(c) for c in comms) == 1005
    assert set(node_to_comm.keys()) == set(range(1005))

    # 3. High modularity Q > 0.40
    assert 0.40 <= q <= 0.45


def test_real_dataset_department_alignment(real_undirected_graph):
    """Verify baseline department modularity, NMI, and ARI against official labels."""
    _, G_undir, _ = real_undirected_graph
    comms, node_to_comm, q_louvain = detect_louvain_communities(G_undir, resolution=1.0, seed=42)
    dept_comp = compare_communities_with_departments(G_undir, node_to_comm)

    # 1. Modularity comparison: Louvain optimizes Q, so Q_louvain > Q_dept
    q_dept = dept_comp["department_modularity"]
    assert 0.25 <= q_dept <= 0.32
    assert q_louvain > q_dept

    # 2. External alignment metrics
    assert 0.55 <= dept_comp["nmi"] <= 0.65
    assert 0.30 <= dept_comp["ari"] <= 0.40

    # 3. Department 36 investigation (contains top 5 PageRank nodes)
    dept_36_nodes = [n for n in G_undir.nodes() if G_undir.nodes[n]["department"] == 36]
    assert len(dept_36_nodes) == 22
    # Check that Department 36 is strongly concentrated within dominant Community 0 (18 of 22 members)
    comm_assignments_36 = [node_to_comm[n] for n in dept_36_nodes]
    dominant_comm_36 = max(set(comm_assignments_36), key=comm_assignments_36.count)
    purity_36 = comm_assignments_36.count(dominant_comm_36) / len(dept_36_nodes)
    assert purity_36 > 0.80  # 18 / 22 = 81.8% concentration in Community 0


def test_real_dataset_louvain_robustness(real_undirected_graph):
    """Verify stability across seeds and resolutions."""
    _, G_undir, _ = real_undirected_graph
    rob = run_louvain_robustness(G_undir, seeds=(42, 123, 2026, 7, 99), resolutions=(0.8, 1.0, 1.2))

    # Seed stability: pairwise ARI across all seeds should exceed 0.65 (mean ~0.797)
    for pair_name, ari_val in rob["pairwise_seed_ari"].items():
        assert ari_val > 0.65


    # Resolution sensitivity: higher resolution produces more communities
    res_08_comms = len(rob["resolution_results"][0.8]["sizes"])
    res_12_comms = len(rob["resolution_results"][1.2]["sizes"])
    assert res_08_comms <= res_12_comms

    # Verify distinction between modularity objective and standard modularity (gamma=1.0)
    for gamma in (0.8, 1.0, 1.2):
        res_dict = rob["resolution_results"][gamma]
        assert "modularity_objective" in res_dict
        assert "modularity_standard" in res_dict
        assert 0.35 <= res_dict["modularity_objective"] <= 0.50
        assert 0.35 <= res_dict["modularity_standard"] <= 0.45

    # Standard modularity is maximized at gamma=1.0
    q_std_08 = rob["resolution_results"][0.8]["modularity_standard"]
    q_std_10 = rob["resolution_results"][1.0]["modularity_standard"]
    q_std_12 = rob["resolution_results"][1.2]["modularity_standard"]
    assert q_std_10 >= q_std_08
    assert q_std_10 >= q_std_12

