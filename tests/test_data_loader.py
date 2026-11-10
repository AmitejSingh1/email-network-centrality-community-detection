"""Automated verification suite for Email-Eu-core data loader.

Tests include synthetic fixtures for edge cases (isolated nodes, self-loops,
duplicate edges, directionality, and malformed records) as well as full invariant
checks against the real SNAP dataset.
"""

from __future__ import annotations

from pathlib import Path
import pytest
import networkx as nx

from src.data_loader import (
    audit_raw_data,
    compute_sha256,
    download_dataset,
    load_email_network,
    DEFAULT_DATA_DIR,
)


@pytest.fixture
def synthetic_dataset(tmp_path: Path):
    """Create a minimal synthetic dataset fixture with known properties."""
    edge_file = tmp_path / "synthetic_edges.txt"
    label_file = tmp_path / "synthetic_labels.txt"

    # Nodes: 0, 1, 2, 3 (node 3 is isolated: no incoming or outgoing edges)
    # Self loop: (2, 2)
    # Duplicate edge: (0, 1) appears twice
    # Directed edge: (1, 2)
    edges_content = "0 1\n0 1\n1 2\n2 2\n"
    labels_content = "0 0\n1 0\n2 1\n3 2\n"

    edge_file.write_text(edges_content, encoding="utf-8")
    label_file.write_text(labels_content, encoding="utf-8")

    return edge_file, label_file


def test_synthetic_isolated_nodes_preserved(synthetic_dataset):
    """Test that nodes listed in department labels with 0 edges are retained in the graph."""
    edge_file, label_file = synthetic_dataset
    G, audit = load_email_network(edge_file, label_file)

    assert G.number_of_nodes() == 4
    assert 3 in G.nodes
    assert G.in_degree(3) == 0
    assert G.out_degree(3) == 0
    assert G.degree(3) == 0
    assert G.nodes[3]["department"] == 2
    assert 3 in audit["nodes_without_edges"]
    assert 3 in audit["isolated_nodes_list"]


def test_synthetic_duplicate_edge_detection(synthetic_dataset):
    """Test that duplicate directed edges are detected and counted in audit."""
    edge_file, label_file = synthetic_dataset
    audit = audit_raw_data(edge_file, label_file)

    assert audit["raw_edges_count"] == 4
    assert audit["unique_directed_edges_count"] == 3  # (0, 1), (1, 2), (2, 2)
    assert audit["duplicate_directed_edges_count"] == 1


def test_synthetic_self_loops_counted(synthetic_dataset):
    """Test that self-loops are identified and counted."""
    edge_file, label_file = synthetic_dataset
    audit = audit_raw_data(edge_file, label_file)
    assert audit["self_loops_count"] == 1


def test_synthetic_graph_directionality(synthetic_dataset):
    """Test that graph is strictly directed and does not implicitly mirror edges."""
    edge_file, label_file = synthetic_dataset
    G, _ = load_email_network(edge_file, label_file)

    assert nx.is_directed(G)
    assert G.has_edge(0, 1)
    assert not G.has_edge(1, 0)
    assert G.has_edge(1, 2)
    assert not G.has_edge(2, 1)


def test_synthetic_unlabeled_edge_node_raises_error(tmp_path: Path):
    """Test that an edge referencing a node without a department label raises ValueError."""
    edge_file = tmp_path / "invalid_edges.txt"
    label_file = tmp_path / "valid_labels.txt"

    # Edge references node 99, which is not in labels
    edge_file.write_text("0 1\n1 99\n", encoding="utf-8")
    label_file.write_text("0 0\n1 0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="nodes in edges without department labels"):
        load_email_network(edge_file, label_file)


def test_synthetic_malformed_rows(tmp_path: Path):
    """Test that malformed lines are flagged during audit."""
    edge_file = tmp_path / "malformed_edges.txt"
    label_file = tmp_path / "malformed_labels.txt"

    edge_file.write_text("0 1\nnot_a_number 2\n0 1 2 extra\n", encoding="utf-8")
    label_file.write_text("0 0\n1\n2 not_int\n", encoding="utf-8")

    audit = audit_raw_data(edge_file, label_file)
    assert audit["malformed_edge_rows"] == 2
    assert audit["valid_edge_rows"] == 1
    assert audit["malformed_label_rows"] == 2
    assert audit["valid_label_rows"] == 1


# --- Real Dataset Invariant Tests ---

@pytest.fixture(scope="session")
def real_data_paths():
    """Ensure real SNAP dataset files are present before testing."""
    edge_path = DEFAULT_DATA_DIR / "email-Eu-core.txt"
    label_path = DEFAULT_DATA_DIR / "email-Eu-core-department-labels.txt"

    if not edge_path.exists() or not label_path.exists():
        download_dataset(DEFAULT_DATA_DIR)

    return edge_path, label_path


def test_real_dataset_node_and_edge_invariants(real_data_paths):
    """Verify that real dataset satisfies all published and structural invariants."""
    edge_path, label_path = real_data_paths
    G, summary = load_email_network(edge_path, label_path)

    # 1. Node universe: exactly 1,005 members labeled 0 to 1,004
    assert G.number_of_nodes() == 1005
    assert summary["unique_labeled_nodes_count"] == 1005
    assert summary["min_node_id"] == 0
    assert summary["max_node_id"] == 1004

    # 2. Every node must have an integer department attribute
    for node, data in G.nodes(data=True):
        assert "department" in data
        assert isinstance(data["department"], int)
        assert 0 <= data["department"] < 42

    # 3. Department universe: exactly 42 departments labeled 0 to 41
    assert summary["unique_departments_count"] == 42
    assert summary["min_dept_id"] == 0
    assert summary["max_dept_id"] == 41

    # 4. Directed edge count invariant
    assert nx.is_directed(G)
    # SNAP reports 25,571 directed edges
    assert G.number_of_edges() == 25571

    # 5. Connected components calculation
    # Largest WCC benchmark is 986 nodes
    assert summary["largest_wcc_size"] == 986

    # 6. Check that isolated nodes are explicitly quantified
    assert summary["isolated_nodes_count"] >= 0
    assert len(summary["all_wcc_sizes"]) == summary["wcc_count"]


def test_real_dataset_peripheral_components_and_self_loops(real_data_paths):
    """Verify peripheral component structure and self-loop distribution."""
    edge_path, label_path = real_data_paths
    G, summary = load_email_network(edge_path, label_path)

    # 1. Total self-loops in graph is 642
    assert summary["graph_self_loops_count"] == 642

    # 2. 20 WCCs: 1 giant component of size 986, and 19 components of size 1
    wccs = list(nx.weakly_connected_components(G))
    assert len(wccs) == 20
    singletons = [list(c)[0] for c in wccs if len(c) == 1]
    assert len(singletons) == 19

    # 3. Each of the 19 singleton components consists of a node with only a self-loop
    for node in singletons:
        edges_out = list(G.out_edges(node))
        edges_in = list(G.in_edges(node))
        assert edges_out == [(node, node)]
        assert edges_in == [(node, node)]
        # Degree without self-loop is 0
        neighbors = [nbr for nbr in G.predecessors(node)] + [nbr for nbr in G.successors(node)]
        assert set(neighbors) == {node}

