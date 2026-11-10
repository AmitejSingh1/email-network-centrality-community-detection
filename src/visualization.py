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


def plot_pagerank_vs_indegree(
    df: pd.DataFrame,
    rho: float,
    disagreements: Optional[Dict[str, pd.DataFrame]] = None,
    output_dir: Optional[Path | str] = None,
) -> Tuple[Path, Path]:
    """Plot PageRank score vs In-Degree with rank disagreement highlights.

    Figure 4: Centrality Comparison (PageRank vs. In-Degree).
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_FIG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    # Panel A: Raw Metric Values (Scatter with density)
    axes[0].scatter(
        df["in_degree"],
        df["pagerank"] * 1000,  # Scaled for readability
        alpha=0.55,
        color="#1f77b4",
        edgecolors="none",
        s=28,
        label="Instituion Members (N=1,005)",
    )

    # Highlight top disagreements if provided
    if disagreements:
        pr_boosted = disagreements.get("pagerank_boosted")
        in_boosted = disagreements.get("in_degree_boosted")

        if pr_boosted is not None and not pr_boosted.empty:
            axes[0].scatter(
                pr_boosted["in_degree"],
                pr_boosted["pagerank"] * 1000,
                color="#2ca02c",
                s=70,
                marker="^",
                label="PageRank Boosted (High PR / Lower In-Deg)",
                edgecolors="black",
                linewidth=0.8,
            )
            # Annotate a few
            for _, r in pr_boosted.head(3).iterrows():
                axes[0].annotate(
                    f"N{int(r['node_id'])}",
                    (r["in_degree"], r["pagerank"] * 1000),
                    textcoords="offset points",
                    xytext=(-15, 8),
                    fontsize=8,
                    weight="bold",
                )

        if in_boosted is not None and not in_boosted.empty:
            axes[0].scatter(
                in_boosted["in_degree"],
                in_boosted["pagerank"] * 1000,
                color="#d62728",
                s=70,
                marker="v",
                label="In-Degree Boosted (High In-Deg / Lower PR)",
                edgecolors="black",
                linewidth=0.8,
            )
            for _, r in in_boosted.head(3).iterrows():
                axes[0].annotate(
                    f"N{int(r['node_id'])}",
                    (r["in_degree"], r["pagerank"] * 1000),
                    textcoords="offset points",
                    xytext=(8, -10),
                    fontsize=8,
                    weight="bold",
                )

    axes[0].set_xlabel("In-Degree ($k_{in}$)")
    axes[0].set_ylabel(r"PageRank Score ($\times 10^{-3}$)")
    axes[0].set_title(f"(a) PageRank vs. In-Degree Centrality\n(Spearman Rank Correlation: $\\rho_s = {rho:.4f}$)")
    axes[0].legend(loc="upper left", fontsize=9)
    axes[0].grid(True, linestyle="--", alpha=0.5)

    # Panel B: Rank-Rank Comparison (1 = Highest Centrality)
    axes[1].scatter(
        df["in_degree_rank"],
        df["pagerank_rank"],
        alpha=0.45,
        color="#4b2e83",
        s=20,
        edgecolors="none",
    )
    # 45-degree identity line
    axes[1].plot([1, 1005], [1, 1005], color="gray", linestyle="--", linewidth=1.2, label="Identity ($y = x$)")

    if disagreements:
        if pr_boosted is not None and not pr_boosted.empty:
            axes[1].scatter(
                pr_boosted["in_degree_rank"],
                pr_boosted["pagerank_rank"],
                color="#2ca02c",
                s=60,
                marker="^",
                label="PR Boosted",
                edgecolors="black",
            )
        if in_boosted is not None and not in_boosted.empty:
            axes[1].scatter(
                in_boosted["in_degree_rank"],
                in_boosted["pagerank_rank"],
                color="#d62728",
                s=60,
                marker="v",
                label="In-Degree Boosted",
                edgecolors="black",
            )

    axes[1].set_xlabel("In-Degree Rank (1 = Most Contacted)")
    axes[1].set_ylabel("PageRank Rank (1 = Highest Prominence)")
    axes[1].set_title("(b) Rank-Rank Comparison (N = 1,005)")
    axes[1].legend(loc="upper left", fontsize=9)
    axes[1].grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()

    png_path = out_dir / "fig4_pagerank_vs_indegree.png"
    pdf_path = out_dir / "fig4_pagerank_vs_indegree.pdf"
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.close()

    logger.info("Saved PageRank vs In-Degree plots to %s and %s", png_path, pdf_path)
    return png_path, pdf_path


def plot_top_ranked_comparison(
    df: pd.DataFrame, k: int = 20, output_dir: Optional[Path | str] = None
) -> Tuple[Path, Path]:
    """Plot ranking slopegraph comparing the top-k individuals under PageRank and In-Degree.

    Figure 5: Top-k Centrality Ranking Shifts.
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_FIG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Union of top-k under both metrics
    top_pr = set(df.sort_values(by="pagerank_rank")["node_id"].head(k))
    top_in = set(df.sort_values(by="in_degree_rank")["node_id"].head(k))
    union_nodes = top_pr.union(top_in)

    sub_df = df[df["node_id"].isin(union_nodes)].copy()
    sub_df = sub_df.sort_values(by="pagerank_rank")

    fig, ax = plt.subplots(figsize=(9, 8))

    for _, row in sub_df.iterrows():
        node_id = int(row["node_id"])
        pr_r = int(row["pagerank_rank"])
        in_r = int(row["in_degree_rank"])

        # Determine color
        if node_id in top_pr and node_id in top_in:
            color = "#2b5c8f"  # Prominent in both
            alpha = 0.85
            lw = 1.8
        elif node_id in top_pr:
            color = "#2ca02c"  # Top only in PR
            alpha = 0.95
            lw = 2.2
        else:
            color = "#d62728"  # Top only in In-Degree
            alpha = 0.95
            lw = 2.2

        ax.plot([0, 1], [pr_r, in_r], marker="o", markersize=6, color=color, alpha=alpha, linewidth=lw)

        # Labels
        if pr_r <= 25:
            ax.text(-0.03, pr_r, f"N{node_id} (R{pr_r})", ha="right", va="center", fontsize=8, color=color)
        if in_r <= 25:
            ax.text(1.03, in_r, f"N{node_id} (R{in_r})", ha="left", va="center", fontsize=8, color=color)

    ax.set_xlim(-0.35, 1.35)
    ax.set_ylim(max(sub_df["pagerank_rank"].max(), sub_df["in_degree_rank"].max()) + 2, 0.5)  # Inverted so rank 1 is top
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["PageRank Rank", "In-Degree Rank"], fontsize=12, weight="bold")
    ax.set_ylabel("Rank (1 = Highest Centrality)")
    ax.set_title(f"Rank Comparison for Top-{k} Prominent Individuals\n(Blue: Both, Green: Top in PR only, Red: Top in In-Degree only)")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()

    png_path = out_dir / "fig5_top_ranked_comparison.png"
    pdf_path = out_dir / "fig5_top_ranked_comparison.pdf"
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.close()

    logger.info("Saved top-ranked comparison plot to %s and %s", png_path, pdf_path)
    return png_path, pdf_path


def plot_pagerank_sensitivity(
    sensitivity_data: Dict[str, Any], output_dir: Optional[Path | str] = None
) -> Tuple[Path, Path]:
    """Plot PageRank ranking trajectories of top nodes across damping factors d in {0.75, 0.85, 0.95}.

    Figure 6: PageRank Sensitivity Analysis.
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_FIG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    damping_factors = sensitivity_data["damping_factors"]
    rankings_by_damping = sensitivity_data["rankings_by_damping"]

    # Select top 15 nodes under baseline d=0.85
    base_top15 = rankings_by_damping[0.85].nsmallest(15).index.tolist()

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    # Panel A: Trajectory Bump Chart for Top-15 Nodes
    x_indices = np.arange(len(damping_factors))
    for node in base_top15:
        ranks = [rankings_by_damping[d][node] for d in damping_factors]
        axes[0].plot(
            x_indices,
            ranks,
            marker="o",
            linewidth=2,
            alpha=0.8,
            label=f"N{node}",
        )
        axes[0].text(x_indices[-1] + 0.04, ranks[-1], f"N{node} (#{ranks[-1]})", va="center", fontsize=8)

    axes[0].set_xticks(x_indices)
    axes[0].set_xticklabels([f"d = {d}" for d in damping_factors], fontsize=11, weight="bold")
    axes[0].set_ylabel("PageRank Rank (Inverted: 1 = Top)")
    axes[0].set_ylim(22, 0.5)  # Inverted
    axes[0].set_title("(a) Rank Stability of Top-15 Nodes Across Damping Factors")
    axes[0].grid(True, linestyle="--", alpha=0.5)

    # Panel B: Top-k Overlap Stability Bar Chart
    k_vals = [10, 20, 50]
    comparisons = [d for d in damping_factors if d != 0.85]
    x_b = np.arange(len(k_vals))
    width = 0.35

    overlap_075 = [sensitivity_data["top_k_overlaps"]["d=0.85_vs_d=0.75"][f"top_{k}"]["overlap_fraction"] * 100 for k in k_vals]
    overlap_095 = [sensitivity_data["top_k_overlaps"]["d=0.85_vs_d=0.95"][f"top_{k}"]["overlap_fraction"] * 100 for k in k_vals]

    bars1 = axes[1].bar(x_b - width/2, overlap_075, width, label="d = 0.85 vs. d = 0.75", color="#3498db", alpha=0.85)
    bars2 = axes[1].bar(x_b + width/2, overlap_095, width, label="d = 0.85 vs. d = 0.95", color="#9b59b6", alpha=0.85)

    for bar in bars1:
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() - 7, f"{bar.get_height():.0f}%", ha="center", color="white", weight="bold")
    for bar in bars2:
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() - 7, f"{bar.get_height():.0f}%", ha="center", color="white", weight="bold")

    axes[1].set_xticks(x_b)
    axes[1].set_xticklabels([f"Top {k}\n(Elite {k/10.05:.1f}%)" for k in k_vals], fontsize=10)
    axes[1].set_ylabel("Overlap Fraction (%)")
    axes[1].set_ylim(0, 110)
    axes[1].set_title("(b) Top-k Rank Set Overlap Relative to d = 0.85")
    axes[1].legend(loc="lower right")
    axes[1].grid(True, axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()

    png_path = out_dir / "fig6_pagerank_sensitivity.png"
    pdf_path = out_dir / "fig6_pagerank_sensitivity.pdf"
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.close()

    logger.info("Saved PageRank sensitivity plots to %s and %s", png_path, pdf_path)
    return png_path, pdf_path


def plot_louvain_community_sizes(
    communities: List[Set[int]], output_dir: Optional[Path | str] = None
) -> Tuple[Path, Path]:
    """Plot ranked size distribution of discovered Louvain communities.

    Figure 7: Louvain Community Size Distribution.
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_FIG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    non_trivial = [len(c) for c in communities if len(c) > 1]
    singletons_count = sum(1 for c in communities if len(c) == 1)

    fig, ax = plt.subplots(figsize=(10, 5))

    x = np.arange(len(non_trivial) + 1)
    heights = non_trivial + [singletons_count]
    labels = [f"C{i} ({sz})" for i, sz in enumerate(non_trivial)] + [f"Singletons\n(19 nodes)"]

    colors = ["#2b5c8f"] * len(non_trivial) + ["#7f7f7f"]
    bars = ax.bar(x, heights, color=colors, width=0.65, edgecolor="black", linewidth=0.8)

    for bar, h in zip(bars, heights):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + 3,
            str(h),
            ha="center",
            va="bottom",
            fontsize=9,
            weight="bold",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("Number of Members")
    ax.set_title(
        f"Discovered Louvain Communication Communities (N = 1,005 Members)\n"
        f"({len(non_trivial)} Non-Trivial Communities + 19 Peripheral Singletons, Resolution $\\gamma = 1.0$)"
    )
    ax.set_ylim(0, max(heights) + 25)
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()

    png_path = out_dir / "fig7_community_sizes.png"
    pdf_path = out_dir / "fig7_community_sizes.pdf"
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.close()

    logger.info("Saved community size distribution to %s and %s", png_path, pdf_path)
    return png_path, pdf_path


def plot_department_community_contingency(
    contingency_df: pd.DataFrame, output_dir: Optional[Path | str] = None
) -> Tuple[Path, Path]:
    """Plot department-community contingency matrix heatmap.

    Figure 8: Department-Community Contingency Heatmap.
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_FIG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Focus on non-trivial communities (columns with size > 1)
    non_trivial_cols = [c for c in contingency_df.columns if contingency_df[c].sum() > 1]
    matrix = contingency_df[non_trivial_cols].copy()

    # Sort departments by their dominant community, then by department size descending
    dominant_comm = matrix.idxmax(axis=1)
    dept_sizes = matrix.sum(axis=1)
    sorted_depts = pd.DataFrame({"dominant": dominant_comm, "size": dept_sizes}).sort_values(
        by=["dominant", "size"], ascending=[True, False]
    ).index

    sorted_matrix = matrix.loc[sorted_depts]

    fig, ax = plt.subplots(figsize=(11, 10))

    sns.heatmap(
        sorted_matrix,
        cmap="YlGnBu",
        annot=True,
        fmt="d",
        cbar_kws={"label": "Member Count"},
        linewidths=0.5,
        linecolor="#e0e0e0",
        ax=ax,
    )

    ax.set_xlabel("Discovered Louvain Community (Ranked by Size)", fontsize=11, weight="bold")
    ax.set_ylabel("Formal Department ID (Grouped by Dominant Community)", fontsize=11, weight="bold")
    ax.set_title(
        "Department-Community Contingency Matrix\n"
        "(Rows: 42 Formal Departments; Columns: Discovered Louvain Communities)",
        fontsize=12,
        weight="bold",
    )

    plt.tight_layout()

    png_path = out_dir / "fig8_department_community_heatmap.png"
    pdf_path = out_dir / "fig8_department_community_heatmap.pdf"
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.close()

    logger.info("Saved department-community contingency heatmap to %s and %s", png_path, pdf_path)
    return png_path, pdf_path


def plot_louvain_robustness(
    robustness_data: Dict[str, Any], output_dir: Optional[Path | str] = None
) -> Tuple[Path, Path]:
    """Plot Louvain stability across random seeds and resolution sensitivity.

    Figure 9: Louvain Robustness and Resolution Sensitivity.
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_FIG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    seeds = robustness_data["seeds"]
    resolutions = robustness_data["resolutions"]
    res_results = robustness_data["resolution_results"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    # Panel A: Pairwise ARI Matrix across Seeds
    n_seeds = len(seeds)
    ari_matrix = np.ones((n_seeds, n_seeds))
    for i in range(n_seeds):
        for j in range(i + 1, n_seeds):
            s1, s2 = seeds[i], seeds[j]
            key = f"seed_{s1}_vs_seed_{s2}"
            val = robustness_data["pairwise_seed_ari"].get(key, 0.0)
            ari_matrix[i, j] = val
            ari_matrix[j, i] = val

    seed_labels = [f"Seed {s}" for s in seeds]
    sns.heatmap(
        ari_matrix,
        annot=True,
        fmt=".3f",
        cmap="Blues",
        vmin=0.6,
        vmax=1.0,
        xticklabels=seed_labels,
        yticklabels=seed_labels,
        cbar_kws={"label": "Adjusted Rand Index (ARI)"},
        ax=axes[0],
    )
    axes[0].set_title("(a) Partition Stability Across Random Seeds (ARI at $\\gamma=1.0$)")

    # Panel B: Resolution Sensitivity (Modularity and Communities Count)
    res_vals = list(resolutions)
    mods = [res_results[r]["modularity"] for r in res_vals]
    n_comms = [len(res_results[r]["sizes"]) for r in res_vals]  # Non-trivial communities

    color_mod = "#1f77b4"
    color_comm = "#d62728"

    ax_b1 = axes[1]
    line1 = ax_b1.plot(res_vals, mods, marker="o", color=color_mod, linewidth=2, label="Modularity Q")
    ax_b1.set_xlabel("Resolution Parameter ($\gamma$)", fontsize=11, weight="bold")
    ax_b1.set_ylabel("Modularity $Q$", color=color_mod, fontsize=11, weight="bold")
    ax_b1.tick_params(axis="y", labelcolor=color_mod)
    ax_b1.set_ylim(0.35, 0.48)

    ax_b2 = ax_b1.twinx()
    line2 = ax_b2.plot(res_vals, n_comms, marker="s", color=color_comm, linewidth=2, linestyle="--", label="Non-Trivial Communities")
    ax_b2.set_ylabel("Number of Non-Trivial Communities", color=color_comm, fontsize=11, weight="bold")
    ax_b2.tick_params(axis="y", labelcolor=color_comm)
    ax_b2.set_ylim(4, 16)
    ax_b2.grid(False)

    lines = line1 + line2
    labels_leg = [l.get_label() for l in lines]
    ax_b1.legend(lines, labels_leg, loc="center right")
    ax_b1.set_title("(b) Effect of Resolution Parameter on Granularity & Modularity")

    plt.tight_layout()

    png_path = out_dir / "fig9_louvain_robustness.png"
    pdf_path = out_dir / "fig9_louvain_robustness.pdf"
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.close()

    logger.info("Saved Louvain robustness plots to %s and %s", png_path, pdf_path)
    return png_path, pdf_path


def plot_pagerank_vs_cross_community_fraction(
    df: pd.DataFrame,
    case_studies: Optional[Dict[str, pd.DataFrame]] = None,
    output_dir: Optional[Path | str] = None,
) -> Tuple[Path, Path]:
    """Plot PageRank score vs Cross-Community Connection Fraction.

    Figure 10: PageRank Centrality vs. Cross-Community Position.
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_FIG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    valid_df = df.dropna(subset=["cross_community_fraction"]).copy()
    top_101 = valid_df.head(101)
    remaining = valid_df.iloc[101:]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Remaining nodes
    ax.scatter(
        remaining["cross_community_fraction"],
        remaining["pagerank"] * 1000,
        color="#7f7f7f",
        alpha=0.45,
        s=25,
        label="Remaining 90% Individuals (N=885)",
    )

    # Top 10% PageRank nodes
    ax.scatter(
        top_101["cross_community_fraction"],
        top_101["pagerank"] * 1000,
        color="#1f77b4",
        alpha=0.85,
        s=55,
        edgecolors="black",
        linewidth=0.7,
        label="Top 10% PageRank Individuals (N=101)",
    )

    # Annotate key case study nodes if available
    if case_studies:
        bridge_df = case_studies.get("high_pr_bridge")
        hub_df = case_studies.get("high_pr_hub")
        periph_df = case_studies.get("peripheral_bridge")

        if bridge_df is not None and not bridge_df.empty:
            for _, r in bridge_df.head(2).iterrows():
                ax.scatter(r["cross_community_fraction"], r["pagerank"] * 1000, color="#2ca02c", s=100, marker="*", edgecolors="black", zorder=5)
                ax.annotate(f"N{int(r['node_id'])} (Global Spanner)", (r["cross_community_fraction"], r["pagerank"] * 1000), textcoords="offset points", xytext=(-25, 10), fontsize=8.5, weight="bold", color="#1b611b")

        if hub_df is not None and not hub_df.empty:
            for _, r in hub_df.head(2).iterrows():
                ax.scatter(r["cross_community_fraction"], r["pagerank"] * 1000, color="#d62728", s=90, marker="D", edgecolors="black", zorder=5)
                ax.annotate(f"N{int(r['node_id'])} (Internal Hub)", (r["cross_community_fraction"], r["pagerank"] * 1000), textcoords="offset points", xytext=(8, -12), fontsize=8.5, weight="bold", color="#8b0000")

    ax.set_xlabel("Cross-Community Connection Fraction (Cross / Total Undirected Degree)", fontsize=11, weight="bold")
    ax.set_ylabel(r"PageRank Score ($\times 10^{-3}$)", fontsize=11, weight="bold")
    ax.set_title("PageRank Centrality vs. Cross-Community Connection Fraction\n(Distinguishing Global Boundary Spanners from Internal Cohesion Hubs)", fontsize=12, weight="bold")
    ax.set_xlim(-0.02, 1.02)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()

    png_path = out_dir / "fig10_pagerank_vs_cross_fraction.png"
    pdf_path = out_dir / "fig10_pagerank_vs_cross_fraction.pdf"
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.close()

    logger.info("Saved PageRank vs cross fraction plot to %s and %s", png_path, pdf_path)
    return png_path, pdf_path


def plot_cross_connectivity_distributions(
    df: pd.DataFrame, output_dir: Optional[Path | str] = None
) -> Tuple[Path, Path]:
    """Plot boxplot comparison of cross-community edge counts and fractions for Top 10% vs. Remaining 90%.

    Figure 11: Cross-Community Connectivity Comparison.
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_FIG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    valid_df = df.dropna(subset=["cross_community_fraction"]).copy()
    valid_df["Tier"] = ["Top 10% PageRank\n(N=101)" if i < 101 else "Remaining 90%\n(N=885)" for i in range(len(valid_df))]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    palette = {"Top 10% PageRank\n(N=101)": "#1f77b4", "Remaining 90%\n(N=885)": "#e67e22"}

    # Panel A: Absolute Cross-Community Edge Count
    sns.boxplot(
        data=valid_df,
        x="Tier",
        y="cross_community_count",
        hue="Tier",
        legend=False,
        palette=palette,
        ax=axes[0],
        width=0.45,
        fliersize=3,
    )
    axes[0].set_ylabel("Cross-Community Connections Count", fontsize=11, weight="bold")
    axes[0].set_xlabel("")
    axes[0].set_title("(a) Cross-Community Degree (Connections Count)", fontsize=11, weight="bold")
    axes[0].grid(True, axis="y", linestyle="--", alpha=0.5)

    # Panel B: Cross-Community Connection Fraction
    sns.boxplot(
        data=valid_df,
        x="Tier",
        y="cross_community_fraction",
        hue="Tier",
        legend=False,
        palette=palette,
        ax=axes[1],
        width=0.45,
        fliersize=3,
    )
    axes[1].set_ylabel("Cross-Community Connection Fraction", fontsize=11, weight="bold")
    axes[1].set_xlabel("")
    axes[1].set_title("(b) Cross-Community Connection Fraction", fontsize=11, weight="bold")
    axes[1].set_ylim(-0.05, 1.05)
    axes[1].grid(True, axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()

    png_path = out_dir / "fig11_cross_connectivity_distributions.png"
    pdf_path = out_dir / "fig11_cross_connectivity_distributions.pdf"
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.close()

    logger.info("Saved cross connectivity distributions to %s and %s", png_path, pdf_path)
    return png_path, pdf_path


def plot_community_profiles(
    summary_df: pd.DataFrame, output_dir: Optional[Path | str] = None
) -> Tuple[Path, Path]:
    """Plot community-level summary metrics (Conductance vs Mean PageRank and Department Diversity).

    Figure 12: Community-Level Profile Summary.
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_FIG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Focus on non-trivial communities (size > 1)
    non_trivial = summary_df[summary_df["size"] > 1].copy()

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Panel A: Conductance vs Mean PageRank
    scatter = axes[0].scatter(
        non_trivial["conductance"],
        non_trivial["mean_pagerank"] * 1000,
        s=non_trivial["size"] * 2.5,
        c=non_trivial["dominant_dept_fraction"] * 100,
        cmap="viridis",
        alpha=0.85,
        edgecolors="black",
        linewidth=1.0,
    )
    cbar = plt.colorbar(scatter, ax=axes[0])
    cbar.set_label("Dominant Dept Share (%)", fontsize=10)

    for _, r in non_trivial.iterrows():
        axes[0].annotate(
            f"C{int(r['comm_id'])} (N={int(r['size'])})",
            (r["conductance"], r["mean_pagerank"] * 1000),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=8.5,
            weight="bold",
        )

    axes[0].set_xlabel("Community Conductance ($\phi$)", fontsize=11, weight="bold")
    axes[0].set_ylabel(r"Mean PageRank ($\times 10^{-3}$)", fontsize=11, weight="bold")
    axes[0].set_title("(a) Conductance vs. Mean PageRank\n(Bubble size = Community Membership)", fontsize=11, weight="bold")
    axes[0].grid(True, linestyle="--", alpha=0.5)

    # Panel B: Number of Departments Represented per Community
    x = np.arange(len(non_trivial))
    axes[1].bar(
        x,
        non_trivial["num_departments"],
        color="#2b5c8f",
        width=0.6,
        edgecolor="black",
        alpha=0.85,
    )
    for i, row in non_trivial.reset_index().iterrows():
        axes[1].text(
            i,
            row["num_departments"] + 0.6,
            f"{row['num_departments']}",
            ha="center",
            va="bottom",
            fontsize=9,
            weight="bold",
        )

    axes[1].set_xticks(x)
    axes[1].set_xticklabels([f"C{int(cid)}" for cid in non_trivial["comm_id"]], fontsize=10)
    axes[1].set_xlabel("Louvain Community", fontsize=11, weight="bold")
    axes[1].set_ylabel("Distinct Departments Represented", fontsize=11, weight="bold")
    axes[1].set_title("(b) Departmental Diversity Across Communities", fontsize=11, weight="bold")
    axes[1].set_ylim(0, max(non_trivial["num_departments"]) + 4)
    axes[1].grid(True, axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()

    png_path = out_dir / "fig12_community_profiles.png"
    pdf_path = out_dir / "fig12_community_profiles.pdf"
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.close()

    logger.info("Saved community profile plot to %s and %s", png_path, pdf_path)
    return png_path, pdf_path
