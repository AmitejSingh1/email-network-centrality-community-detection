"""Publication-quality visualization generator for Email-Eu-core network analysis.

Generates focused, interpretable figures saved to reports/figures/ in both PNG
and vector PDF formats.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple, Dict

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns

from src.graph_analysis import (
    compute_degree_statistics,
    compute_department_statistics,
    compute_edge_department_composition,
)

logger = logging.getLogger(__name__)

# Configure clean academic style
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 11,
        "figure.titlesize": 14,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    }
)

DEFAULT_FIG_DIR = Path(__file__).resolve().parent.parent / "reports" / "figures"


def plot_degree_distributions(
    G: nx.DiGraph, output_dir: Optional[Path | str] = None
) -> Tuple[Path, Path]:
    """Plot in-degree and out-degree distributions with histograms and complementary CDFs.

    Figure 1: Degree Distributions (In-Degree vs. Out-Degree).
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_FIG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    in_degrees = np.array([d for _, d in G.in_degree()])
    out_degrees = np.array([d for _, d in G.out_degree()])

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Panel A: Histograms with summary metrics
    sns.histplot(
        in_degrees,
        bins=35,
        color="#1f77b4",
        label=f"In-Degree (Mean: {np.mean(in_degrees):.1f}, Med: {int(np.median(in_degrees))}, Max: {int(np.max(in_degrees))})",
        alpha=0.6,
        ax=axes[0],
    )
    sns.histplot(
        out_degrees,
        bins=35,
        color="#ff7f0e",
        label=f"Out-Degree (Mean: {np.mean(out_degrees):.1f}, Med: {int(np.median(out_degrees))}, Max: {int(np.max(out_degrees))})",
        alpha=0.6,
        ax=axes[0],
    )
    axes[0].set_xlabel("Directed Degree")
    axes[0].set_ylabel("Count of Nodes")
    axes[0].set_title("(a) Degree Frequency Histogram")
    axes[0].legend(loc="upper right")
    axes[0].grid(True, linestyle="--", alpha=0.5)

    # Panel B: Complementary Cumulative Distribution Function (CCDF) on log-log scale
    def get_ccdf(data):
        # Exclude zeros for log scale plotting
        non_zero = data[data > 0]
        sorted_data = np.sort(non_zero)
        ccdf = 1.0 - np.arange(len(sorted_data)) / len(sorted_data)
        return sorted_data, ccdf

    x_in, y_in = get_ccdf(in_degrees)
    x_out, y_out = get_ccdf(out_degrees)

    axes[1].loglog(x_in, y_in, marker="o", markersize=3.5, linestyle="none", color="#1f77b4", alpha=0.75, label="In-Degree CCDF")
    axes[1].loglog(x_out, y_out, marker="s", markersize=3.5, linestyle="none", color="#ff7f0e", alpha=0.75, label="Out-Degree CCDF")
    axes[1].set_xlabel("Degree $k$ (log scale)")
    axes[1].set_ylabel(r"$P(K \geq k)$ (log scale)")
    axes[1].set_title("(b) Complementary Cumulative Distribution Function (CCDF)")
    axes[1].legend(loc="lower left")
    axes[1].grid(True, which="both", linestyle="--", alpha=0.5)

    plt.tight_layout()

    png_path = out_dir / "fig1_degree_distributions.png"
    pdf_path = out_dir / "fig1_degree_distributions.pdf"
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.close()

    logger.info("Saved degree distribution plots to %s and %s", png_path, pdf_path)
    return png_path, pdf_path


def plot_department_size_distribution(
    G: nx.DiGraph, output_dir: Optional[Path | str] = None
) -> Tuple[Path, Path]:
    """Plot sorted department membership size distribution across the 42 departments.

    Figure 2: Department Size Distribution.
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_FIG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    dept_stats = compute_department_statistics(G)
    dept_sizes = pd.Series(dept_stats["department_sizes"]).sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(11, 5))

    x_pos = np.arange(len(dept_sizes))
    bars = ax.bar(x_pos, dept_sizes.values, color="#2ca02c", alpha=0.8, edgecolor="#1b611b", width=0.75)

    mean_val = dept_stats["mean_size"]
    median_val = dept_stats["median_size"]

    ax.axhline(mean_val, color="#d62728", linestyle="--", linewidth=1.5, label=f"Mean Department Size ({mean_val:.1f})")
    ax.axhline(median_val, color="#9467bd", linestyle=":", linewidth=2, label=f"Median Department Size ({median_val:.0f})")

    ax.set_xticks(x_pos)
    ax.set_xticklabels([f"D{d}" for d in dept_sizes.index], rotation=90, fontsize=8)
    ax.set_xlabel("Department Identifier (Ranked by Membership Size)")
    ax.set_ylabel("Number of Affiliated Individuals")
    ax.set_title("Distribution of Department Membership Sizes (42 Departments, 1,005 Individuals)")
    ax.legend(loc="upper right")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()

    png_path = out_dir / "fig2_department_sizes.png"
    pdf_path = out_dir / "fig2_department_sizes.pdf"
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.close()

    logger.info("Saved department size distribution plot to %s and %s", png_path, pdf_path)
    return png_path, pdf_path


def plot_within_vs_cross_department_edges(
    G: nx.DiGraph, output_dir: Optional[Path | str] = None
) -> Tuple[Path, Path]:
    """Plot within-department vs. cross-department edge composition.

    Figure 3: Summary of within-department versus cross-department edges,
    including direct comparison against uniform random reference model.
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_FIG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    edge_comp_no_self = compute_edge_department_composition(G, exclude_self_loops=True)
    dept_stats = compute_department_statistics(G)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Panel A: Comparison between Empirical Network and Uniform Random Reference Model
    p_empirical_within = edge_comp_no_self["within_dept_fraction"] * 100
    p_empirical_cross = edge_comp_no_self["cross_dept_fraction"] * 100
    p_null_within = edge_comp_no_self["reference_model_expected_within_fraction"] * 100
    p_null_cross = edge_comp_no_self["reference_model_expected_cross_fraction"] * 100

    enrichment = edge_comp_no_self["homophily_enrichment_ratio"]

    categories = ["Empirical Network\n(G_analysis, 24,929 edges)", "Uniform Random Reference\n(Fixed Department Sizes)"]
    within_vals = [p_empirical_within, p_null_within]
    cross_vals = [p_empirical_cross, p_null_cross]

    x = np.arange(len(categories))
    width = 0.45

    bars1 = axes[0].bar(x, within_vals, width, label="Within-Department", color="#2b5c8f", alpha=0.9)
    bars2 = axes[0].bar(x, cross_vals, width, bottom=within_vals, label="Cross-Department", color="#e67e22", alpha=0.9)

    # Label percentages inside bars
    axes[0].text(0, within_vals[0] / 2, f"{p_empirical_within:.1f}%\n({edge_comp_no_self['within_dept_edges']:,} edges)", ha="center", va="center", color="white", weight="bold")
    axes[0].text(0, within_vals[0] + cross_vals[0] / 2, f"{p_empirical_cross:.1f}%\n({edge_comp_no_self['cross_dept_edges']:,} edges)", ha="center", va="center", color="white", weight="bold")
    axes[0].text(1, within_vals[1] / 2, f"{p_null_within:.1f}%", ha="center", va="center", color="white", weight="bold")
    axes[0].text(1, within_vals[1] + cross_vals[1] / 2, f"{p_null_cross:.1f}%", ha="center", va="center", color="white", weight="bold")

    axes[0].set_ylabel("Percentage of Directed Edges (%)")
    axes[0].set_title(f"(a) Communication Breakdown vs. Random Reference Model\n({enrichment:.2f}× Within-Department Enrichment)")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(categories)
    axes[0].set_ylim(0, 105)
    axes[0].legend(loc="lower right")
    axes[0].grid(True, axis="y", linestyle="--", alpha=0.5)

    # Panel B: Per-department edge breakdown (Internal vs. Outgoing External for top 15 largest departments)
    largest_depts = pd.Series(dept_stats["department_sizes"]).sort_values(ascending=False).head(15).index.tolist()

    internal_counts = [edge_comp_no_self["dept_internal_edges"].get(d, 0) for d in largest_depts]
    outgoing_counts = [edge_comp_no_self["dept_outgoing_cross"].get(d, 0) for d in largest_depts]

    x_depts = np.arange(len(largest_depts))
    width_depts = 0.55

    axes[1].bar(x_depts, internal_counts, width_depts, label="Within-Dept (Internal)", color="#2b5c8f", alpha=0.85)
    axes[1].bar(x_depts, outgoing_counts, width_depts, bottom=internal_counts, label="Cross-Dept (Outgoing External)", color="#e67e22", alpha=0.85)

    axes[1].set_xticks(x_depts)
    axes[1].set_xticklabels([f"D{d}" for d in largest_depts], rotation=45)
    axes[1].set_xlabel("Top 15 Largest Departments (by Membership)")
    axes[1].set_ylabel("Total Outgoing Directed Edges")
    axes[1].set_title("(b) Internal vs. External Communication for Top Departments")
    axes[1].legend(loc="upper right")
    axes[1].grid(True, axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()

    png_path = out_dir / "fig3_within_vs_cross_edges.png"
    pdf_path = out_dir / "fig3_within_vs_cross_edges.pdf"
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.close()

    logger.info("Saved within vs cross department edge plots to %s and %s", png_path, pdf_path)
    return png_path, pdf_path


def generate_all_exploratory_figures(
    G: nx.DiGraph, output_dir: Optional[Path | str] = None
) -> Dict[str, Tuple[Path, Path]]:
    """Generate all three primary exploratory figures."""
    return {
        "fig1": plot_degree_distributions(G, output_dir),
        "fig2": plot_department_size_distribution(G, output_dir),
        "fig3": plot_within_vs_cross_department_edges(G, output_dir),
    }
