"""Data loader and integrity auditor for SNAP Email-Eu-core network.

Provides reproducible data acquisition, raw record auditing, cryptographic
checksum tracking, and directed graph construction with ground-truth department
labels.
"""

from __future__ import annotations

import gzip
import hashlib
import logging
import shutil
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

logger = logging.getLogger(__name__)

# Official SNAP source URLs
SNAP_EDGE_URL = "https://snap.stanford.edu/data/email-Eu-core.txt.gz"
SNAP_LABEL_URL = "https://snap.stanford.edu/data/email-Eu-core-department-labels.txt.gz"

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def compute_sha256(filepath: Path | str) -> str:
    """Compute and return the hex-encoded SHA-256 checksum of a file."""
    path = Path(filepath)
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def download_dataset(
    data_dir: Optional[Path | str] = None, force: bool = False
) -> Dict[str, Dict[str, Any]]:
    """Download SNAP Email-Eu-core dataset files if not already present.

    Parameters
    ----------
    data_dir : Optional[Path | str]
        Target directory for raw data. Defaults to `data/raw/`.
    force : bool
        If True, re-download even if files already exist.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Metadata dictionary containing local paths, URLs, and recorded SHA-256
        checksums for downloaded and decompressed files.
    """
    target_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    files_info = {
        "edges_gz": {
            "filename": "email-Eu-core.txt.gz",
            "url": SNAP_EDGE_URL,
            "txt_name": "email-Eu-core.txt",
        },
        "labels_gz": {
            "filename": "email-Eu-core-department-labels.txt.gz",
            "url": SNAP_LABEL_URL,
            "txt_name": "email-Eu-core-department-labels.txt",
        },
    }

    results: Dict[str, Dict[str, Any]] = {}

    for key, info in files_info.items():
        gz_path = target_dir / info["filename"]
        txt_path = target_dir / info["txt_name"]

        # Download .gz if absent or forced
        if not gz_path.exists() or force:
            logger.info("Downloading %s from %s ...", info["filename"], info["url"])
            urllib.request.urlretrieve(info["url"], gz_path)

        gz_sha256 = compute_sha256(gz_path)

        # Decompress to .txt if absent or forced
        if not txt_path.exists() or force:
            logger.info("Decompressing %s to %s ...", gz_path.name, txt_path.name)
            with gzip.open(gz_path, "rb") as f_in, open(txt_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        txt_sha256 = compute_sha256(txt_path)

        results[key] = {
            "url": info["url"],
            "gz_path": str(gz_path),
            "gz_sha256": gz_sha256,
            "txt_path": str(txt_path),
            "txt_sha256": txt_sha256,
            "gz_size_bytes": gz_path.stat().st_size,
            "txt_size_bytes": txt_path.stat().st_size,
        }

    return results


def audit_raw_data(
    edge_file: Path | str, label_file: Path | str
) -> Dict[str, Any]:
    """Audit raw edge and department-label files for integrity before graph creation.

    Counts raw records, detects malformed rows, self-loops, duplicate directed
    edges, and node set discrepancies between files.
    """
    edge_path = Path(edge_file)
    label_path = Path(label_file)

    if not edge_path.exists():
        raise FileNotFoundError(f"Edge file not found: {edge_path}")
    if not label_path.exists():
        raise FileNotFoundError(f"Label file not found: {label_path}")

    # Audit department labels
    raw_label_rows = 0
    valid_label_rows = 0
    malformed_label_rows = 0
    node_to_dept: Dict[int, int] = {}
    label_duplicates = 0

    with open(label_path, "r", encoding="utf-8") as f:
        for line in f:
            raw_label_rows += 1
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            parts = line_str.split()
            if len(parts) != 2:
                malformed_label_rows += 1
                continue
            try:
                node_id = int(parts[0])
                dept_id = int(parts[1])
            except ValueError:
                malformed_label_rows += 1
                continue

            if node_id in node_to_dept:
                label_duplicates += 1
            node_to_dept[node_id] = dept_id
            valid_label_rows += 1

    # Audit directed edge records
    raw_edge_rows = 0
    valid_edge_rows = 0
    malformed_edge_rows = 0
    raw_edges: List[Tuple[int, int]] = []
    self_loops_count = 0

    with open(edge_path, "r", encoding="utf-8") as f:
        for line in f:
            raw_edge_rows += 1
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            parts = line_str.split()
            if len(parts) != 2:
                malformed_edge_rows += 1
                continue
            try:
                u = int(parts[0])
                v = int(parts[1])
            except ValueError:
                malformed_edge_rows += 1
                continue

            valid_edge_rows += 1
            if u == v:
                self_loops_count += 1
            raw_edges.append((u, v))

    # Identify duplicate directed edges
    edge_counts = Counter(raw_edges)
    unique_directed_edges = set(edge_counts.keys())
    duplicate_edge_count = sum(count - 1 for count in edge_counts.values())

    edge_nodes: Set[int] = set()
    for u, v in raw_edges:
        edge_nodes.add(u)
        edge_nodes.add(v)

    label_nodes = set(node_to_dept.keys())

    # Nodes appearing in edges but not in labels (if any)
    unlabeled_edge_nodes = edge_nodes - label_nodes
    # Nodes in labels that have no incident edges in raw_edges
    nodes_without_edges = label_nodes - edge_nodes

    unique_depts = set(node_to_dept.values())

    audit_summary: Dict[str, Any] = {
        "raw_edge_rows": raw_edge_rows,
        "valid_edge_rows": valid_edge_rows,
        "malformed_edge_rows": malformed_edge_rows,
        "raw_edges_count": len(raw_edges),
        "unique_directed_edges_count": len(unique_directed_edges),
        "duplicate_directed_edges_count": duplicate_edge_count,
        "self_loops_count": self_loops_count,
        "raw_label_rows": raw_label_rows,
        "valid_label_rows": valid_label_rows,
        "malformed_label_rows": malformed_label_rows,
        "label_duplicates_count": label_duplicates,
        "unique_labeled_nodes_count": len(label_nodes),
        "unique_edge_nodes_count": len(edge_nodes),
        "unlabeled_edge_nodes": sorted(list(unlabeled_edge_nodes)),
        "nodes_without_edges": sorted(list(nodes_without_edges)),
        "unique_departments_count": len(unique_depts),
        "min_node_id": min(label_nodes) if label_nodes else None,
        "max_node_id": max(label_nodes) if label_nodes else None,
        "min_dept_id": min(unique_depts) if unique_depts else None,
        "max_dept_id": max(unique_depts) if unique_depts else None,
    }

    return audit_summary


def load_email_network(
    edge_file: Optional[Path | str] = None,
    label_file: Optional[Path | str] = None,
    auto_download: bool = False,
) -> Tuple[nx.DiGraph, Dict[str, Any]]:
    """Load the Email-Eu-core directed graph and attach department labels.

    Preserves all labeled nodes in the node universe, including nodes with zero
    incident edges. Validates connectivity and component distributions.

    Parameters
    ----------
    edge_file : Optional[Path | str]
        Path to uncompressed edge list file.
    label_file : Optional[Path | str]
        Path to uncompressed department labels file.
    auto_download : bool
        If True, download files from SNAP if absent.

    Returns
    -------
    Tuple[nx.DiGraph, Dict[str, Any]]
        Constructed directed graph G_dir and comprehensive audit/verification summary.
    """
    if edge_file is None:
        edge_file = DEFAULT_DATA_DIR / "email-Eu-core.txt"
    if label_file is None:
        label_file = DEFAULT_DATA_DIR / "email-Eu-core-department-labels.txt"

    edge_path = Path(edge_file)
    label_path = Path(label_file)

    if (not edge_path.exists() or not label_path.exists()) and auto_download:
        download_dataset(edge_path.parent)

    audit = audit_raw_data(edge_path, label_path)

    if audit["unlabeled_edge_nodes"]:
        raise ValueError(
            f"Found {len(audit['unlabeled_edge_nodes'])} nodes in edges without department labels."
        )

    # Read node-to-department mapping
    node_to_dept: Dict[int, int] = {}
    with open(label_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                node_to_dept[int(parts[0])] = int(parts[1])

    # Construct directed graph
    G = nx.DiGraph()

    # Add all labeled nodes to preserve the complete institution population
    for node_id, dept_id in sorted(node_to_dept.items()):
        G.add_node(node_id, department=dept_id)

    # Add edges
    with open(edge_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                u, v = int(parts[0]), int(parts[1])
                G.add_edge(u, v)

    # Compute network verification statistics
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    num_self_loops = nx.number_of_selfloops(G)

    # Weakly and strongly connected components
    wcc = list(nx.weakly_connected_components(G))
    wcc_sizes = sorted([len(c) for c in wcc], reverse=True)
    scc = list(nx.strongly_connected_components(G))
    scc_sizes = sorted([len(c) for c in scc], reverse=True)

    # Isolated nodes (degree 0: in_degree == 0 and out_degree == 0)
    isolated_nodes = [n for n in G.nodes() if G.in_degree(n) == 0 and G.out_degree(n) == 0]

    verification_summary = {
        **audit,
        "graph_nodes_count": num_nodes,
        "graph_edges_count": num_edges,
        "graph_self_loops_count": num_self_loops,
        "graph_density": nx.density(G),
        "wcc_count": len(wcc),
        "largest_wcc_size": wcc_sizes[0] if wcc_sizes else 0,
        "all_wcc_sizes": wcc_sizes,
        "scc_count": len(scc),
        "largest_scc_size": scc_sizes[0] if scc_sizes else 0,
        "isolated_nodes_count": len(isolated_nodes),
        "isolated_nodes_list": sorted(isolated_nodes),
    }

    return G, verification_summary


def create_analysis_graph(G_raw: nx.DiGraph) -> nx.DiGraph:
    """Derive the primary analysis graph by removing self-loops from G_raw.

    Preserves all nodes, their attributes, and directed edge relationships
    between distinct individuals. Peripheral singletons that previously only had
    a self-loop are retained as isolated (degree 0) nodes.

    Parameters
    ----------
    G_raw : nx.DiGraph
        Raw directed email graph (contains 1,005 nodes and 25,571 directed edges).

    Returns
    -------
    nx.DiGraph
        Analysis graph G_analysis (contains 1,005 nodes and 24,929 directed edges).
    """
    G_analysis = G_raw.copy()
    self_loops = list(nx.selfloop_edges(G_analysis))
    G_analysis.remove_edges_from(self_loops)

    # Invariant checks
    if G_analysis.number_of_nodes() != G_raw.number_of_nodes():
        raise RuntimeError("Node count altered during self-loop removal.")
    if nx.number_of_selfloops(G_analysis) != 0:
        raise RuntimeError("Failed to remove all self-loops.")

    return G_analysis

