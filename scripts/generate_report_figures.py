"""Generate publication-quality, high-legibility figures for the DSA5101 research report.

Tailored specifically for A4 report width (6.69 inches / 481.9 pt) with 300 DPI resolution,
large typography (11-13 pt), clean high-contrast palettes, and clear annotations.
"""

from __future__ import annotations

import gzip
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy import stats
import seaborn as sns
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

# Output directory
FIG_DIR = Path("reports/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Styling configuration
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
plt.rcParams["axes.edgecolor"] = "#2D3748"
plt.rcParams["axes.linewidth"] = 0.9
plt.rcParams["axes.titlesize"] = 11
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.labelsize"] = 10
plt.rcParams["axes.labelweight"] = "bold"
plt.rcParams["xtick.labelsize"] = 9
plt.rcParams["ytick.labelsize"] = 9
plt.rcParams["legend.fontsize"] = 8.5
plt.rcParams["figure.titlesize"] = 12

DATA_DIR = Path("data/raw")
edge_gz = DATA_DIR / "email-Eu-core.txt.gz"
label_gz = DATA_DIR / "email-Eu-core-department-labels.txt.gz"

# 1. Load data
node_departments = {}
with gzip.open(label_gz, "rt", encoding="utf-8") as f:
    for line in f:
        if line.strip() and not line.startswith("#"):
            p = line.split()
            node_departments[int(p[0])] = int(p[1])

raw_edges = []
seen = set()
with gzip.open(edge_gz, "rt", encoding="utf-8") as f:
    for line in f:
        if line.strip() and not line.startswith("#"):
            u, v = map(int, line.split())
            if (u, v) not in seen:
                seen.add((u, v))
                raw_edges.append((u, v))

G_raw = nx.DiGraph()
G_analysis = nx.DiGraph()
for n in sorted(node_departments.keys()):
    G_raw.add_node(n, department=node_departments[n])
    G_analysis.add_node(n, department=node_departments[n])

for u, v in raw_edges:
    G_raw.add_edge(u, v)
    if u != v:
        G_analysis.add_edge(u, v)

G_undir = G_analysis.to_undirected()

# Algorithms
pr_dict = nx.pagerank(G_analysis, alpha=0.85, tol=1e-6, max_iter=500, weight=None)
in_deg_dict = dict(G_analysis.in_degree())
out_deg_dict = dict(G_analysis.out_degree())

raw_comms = nx.community.louvain_communities(G_undir, weight=None, resolution=1.0, seed=42)
sorted_comms = sorted(raw_comms, key=lambda c: (-len(c), min(c) if c else 0))
non_trivial_comms = [c for c in sorted_comms if len(c) > 1]
node_to_comm = {n: cid for cid, cset in enumerate(sorted_comms) for n in cset}

# Centrality DataFrame
nodes = sorted(list(G_analysis.nodes()))
cent_df = pd.DataFrame({
    "node_id": nodes,
    "department": [G_analysis.nodes[n]["department"] for n in nodes],
    "in_degree": [in_deg_dict[n] for n in nodes],
    "out_degree": [out_deg_dict[n] for n in nodes],
    "pagerank": [pr_dict[n] for n in nodes],
    "community": [node_to_comm[n] for n in nodes],
    "total_degree": [G_undir.degree(n) for n in nodes],
})
cent_df = cent_df.sort_values(by=["pagerank", "node_id"], ascending=[False, True]).reset_index(drop=True)
cent_df["pagerank_rank_unique"] = range(1, len(cent_df) + 1)
cent_df = cent_df.sort_values(by=["in_degree", "node_id"], ascending=[False, True]).reset_index(drop=True)
cent_df["in_degree_rank_unique"] = range(1, len(cent_df) + 1)
cent_df["rank_difference"] = cent_df["in_degree_rank_unique"] - cent_df["pagerank_rank_unique"]
cent_df = cent_df.sort_values(by="pagerank_rank_unique").reset_index(drop=True)

# Boundary connectivity
cross_counts = []
cross_fractions = []
for n in nodes:
    deg = G_undir.degree(n)
    if deg == 0:
        cross_counts.append(0)
        cross_fractions.append(np.nan)
    else:
        c_v = node_to_comm[n]
        cc = sum(1 for u in G_undir.neighbors(n) if node_to_comm[u] != c_v)
        cross_counts.append(cc)
        cross_fractions.append(cc / deg)

cent_df["cross_community_count"] = [cross_counts[n] for n in cent_df["node_id"]]
cent_df["cross_community_fraction"] = [cross_fractions[n] for n in cent_df["node_id"]]


# =============================================================================
# FIGURE 1: Degree Distributions (Linear + Log-Log CCDF)
# =============================================================================
def make_fig1():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7), dpi=300)
    in_degrees = np.array([d for _, d in G_analysis.in_degree()])
    out_degrees = np.array([d for _, d in G_analysis.out_degree()])

    # Panel a: Histogram with clean binning & mean/median markers
    bins = np.linspace(0, max(in_degrees.max(), out_degrees.max()), 35)
    axes[0].hist(in_degrees, bins=bins, color="#2B6CB0", alpha=0.65, label=f"In-Degree (Med={np.median(in_degrees):.0f})", edgecolor="#1A365D", linewidth=0.5)
    axes[0].hist(out_degrees, bins=bins, color="#DD6B20", alpha=0.55, label=f"Out-Degree (Med={np.median(out_degrees):.0f})", edgecolor="#7B341E", linewidth=0.5)
    axes[0].axvline(np.mean(in_degrees), color="#2B6CB0", linestyle="--", linewidth=1.2, label=f"Mean = {np.mean(in_degrees):.1f}")
    axes[0].set_xlabel("Directed Degree (Links)", fontsize=9.5, weight="bold")
    axes[0].set_ylabel("Number of Individuals", fontsize=9.5, weight="bold")
    axes[0].set_title("(a) Degree Frequency Histogram", fontsize=10.5, weight="bold", pad=6)
    axes[0].legend(loc="upper right", frameon=True, fontsize=8, framealpha=0.9)
    axes[0].grid(True, linestyle=":", alpha=0.6)

    # Panel b: CCDF (Complementary Cumulative Distribution Function)
    for degs, label, col, marker in [(in_degrees, "In-Degree", "#2B6CB0", "o"), (out_degrees, "Out-Degree", "#DD6B20", "s")]:
        d_pos = np.sort(degs[degs > 0])
        ccdf = 1.0 - (np.arange(len(d_pos)) / len(d_pos))
        axes[1].loglog(d_pos, ccdf, marker=marker, markersize=3.5, linestyle="none", color=col, alpha=0.75, label=label)

    # Reference guide line showing heavy tail
    x_ref = np.linspace(5, 150, 50)
    y_ref = 3.0 * (x_ref ** -1.2)
    axes[1].loglog(x_ref, y_ref, "k:", alpha=0.5, linewidth=1.0, label=r"Heavy-Tail Guide ($\propto k^{-1.2}$)")

    axes[1].set_xlabel("Degree $k$ (Log Scale)", fontsize=9.5, weight="bold")
    axes[1].set_ylabel(r"$P(X \geq k)$ (Log Scale)", fontsize=9.5, weight="bold")
    axes[1].set_title("(b) Complementary Cumulative Distribution (CCDF)", fontsize=10.5, weight="bold", pad=6)
    axes[1].legend(loc="lower left", frameon=True, fontsize=8, framealpha=0.9)
    axes[1].grid(True, which="both", linestyle=":", alpha=0.5)

    plt.tight_layout()
    p = FIG_DIR / "fig1_degree_distributions_clean.png"
    plt.savefig(p, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {p}")

make_fig1()


# =============================================================================
# FIGURE 2: Department Alignment & Homophily Enrichment
# =============================================================================
def make_fig2():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7), dpi=300)
    
    # Panel a: Department size distribution
    dept_sizes = pd.Series(list(node_departments.values())).value_counts().sort_values(ascending=False)
    axes[0].bar(range(len(dept_sizes)), dept_sizes.values, color="#319795", edgecolor="#234E52", linewidth=0.6, width=0.8)
    axes[0].set_xlabel("Department Rank (Ordered by Size)", fontsize=9.5, weight="bold")
    axes[0].set_ylabel("Affiliated Members", fontsize=9.5, weight="bold")
    axes[0].set_title(f"(a) Department Sizes ($N=42$, Max={dept_sizes.max()}, Min={dept_sizes.min()})", fontsize=10.5, weight="bold", pad=6)
    axes[0].grid(True, axis="y", linestyle=":", alpha=0.6)

    # Panel b: Intra vs Inter communication
    within_edges = sum(1 for u, v in G_analysis.edges() if G_analysis.nodes[u]["department"] == G_analysis.nodes[v]["department"])
    cross_edges = G_analysis.number_of_edges() - within_edges
    within_frac = within_edges / G_analysis.number_of_edges()
    cross_frac = cross_edges / G_analysis.number_of_edges()

    N = G_analysis.number_of_nodes()
    p_null = sum(s * (s - 1) for s in dept_sizes) / (N * (N - 1))
    homophily_ratio = within_frac / p_null

    categories = ["Within-Dept\n(Observed)", "Cross-Dept\n(Observed)", "Within-Dept\n(Null Model)"]
    vals = [within_frac * 100, cross_frac * 100, p_null * 100]
    bar_cols = ["#2B6CB0", "#DD6B20", "#718096"]
    bars = axes[1].bar(categories, vals, color=bar_cols, edgecolor="#1A202C", linewidth=0.7, width=0.55)
    
    for bar, val in zip(bars, vals):
        y = bar.get_height()
        axes[1].text(bar.get_x() + bar.get_width()/2.0, y + 1.5, f"{val:.1f}%", ha="center", va="bottom", weight="bold", fontsize=9)

    # Annotation for homophily enrichment
    axes[1].annotate(
        f"{homophily_ratio:.2f}× Enrichment\nAbove Null Baseline",
        xy=(0, vals[0]), xytext=(0.5, 48),
        arrowprops=dict(arrowstyle="->", color="#1A202C", lw=1.2),
        ha="center", fontsize=8.5, weight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="#FEFCBF", ec="#B7791F", lw=0.8)
    )

    axes[1].set_ylabel("Share of Directed Links (%)", fontsize=9.5, weight="bold")
    axes[1].set_title("(b) Departmental Communication Composition", fontsize=10.5, weight="bold", pad=6)
    axes[1].set_ylim(0, 78)
    axes[1].grid(True, axis="y", linestyle=":", alpha=0.6)

    plt.tight_layout()
    p = FIG_DIR / "fig2_department_homophily_clean.png"
    plt.savefig(p, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {p}")

make_fig2()


# =============================================================================
# FIGURE 3: PageRank vs In-Degree Centrality Disagreements
# =============================================================================
def make_fig3():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.85), dpi=300)

    # Panel a: Scatter plot with regression line & key archetypes
    rho_s, _ = stats.spearmanr(cent_df["pagerank"], cent_df["in_degree"])
    axes[0].scatter(cent_df["in_degree"], cent_df["pagerank"] * 1000, color="#4A5568", alpha=0.45, s=18, edgecolors="none")

    # Archetype highlights
    focal_nodes = [
        (160, "#E53E3E", "Node 160 (PR Rank 1, In-Deg Rank 1)", (180, 6.2)),
        (451, "#805AD5", "Node 451 (+622 PR Boost, In-Deg 8)", (30, 3.8)),
        (83,  "#D69E2E", "Node 83 (In-Deg Rank 45, PR Rank 56)", (105, 1.8)),
    ]
    for nid, color, label, xytext in focal_nodes:
        row = cent_df[cent_df["node_id"] == nid].iloc[0]
        x, y = row["in_degree"], row["pagerank"] * 1000
        axes[0].scatter(x, y, color=color, s=70, edgecolors="#1A202C", linewidth=1.2, zorder=6)
        axes[0].annotate(
            label, xy=(x, y), xytext=xytext,
            arrowprops=dict(arrowstyle="->", color=color, lw=1.1),
            fontsize=8, weight="bold", color="#1A202C",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=color, lw=0.9, alpha=0.95)
        )

    axes[0].set_xlabel("In-Degree (Incoming Senders)", fontsize=9.5, weight="bold")
    axes[0].set_ylabel(r"PageRank Score ($\times 10^{-3}$)", fontsize=9.5, weight="bold")
    axes[0].set_title(f"(a) Global Centrality ($\\rho_s = {rho_s:.4f}$)", fontsize=10.5, weight="bold", pad=6)
    axes[0].grid(True, linestyle=":", alpha=0.6)

    # Panel b: Rank shifts for top 20 PageRank individuals
    top20 = cent_df.head(20).copy()
    x_pos = np.arange(len(top20))
    shift_colors = ["#38A169" if s >= 0 else "#E53E3E" for s in top20["rank_difference"]]
    axes[1].bar(x_pos, top20["rank_difference"], color=shift_colors, edgecolor="#1A202C", linewidth=0.5, width=0.65)
    axes[1].axhline(0, color="#1A202C", linestyle="-", linewidth=0.8)
    axes[1].set_xticks(x_pos)
    axes[1].set_xticklabels(top20["node_id"], rotation=90, fontsize=7.5, weight="bold")
    axes[1].set_xlabel("Node ID (Top 20 PageRank Order)", fontsize=9.5, weight="bold")
    axes[1].set_ylabel("Rank Shift (In-Degree Rank - PR Rank)", fontsize=9.5, weight="bold")
    axes[1].set_title("(b) Top-Tier Rank Shifts ($\Delta R$)", fontsize=10.5, weight="bold", pad=6)
    axes[1].grid(True, axis="y", linestyle=":", alpha=0.6)

    plt.tight_layout()
    p = FIG_DIR / "fig3_pagerank_vs_indegree_clean.png"
    plt.savefig(p, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {p}")

make_fig3()


# =============================================================================
# FIGURE 4: Community-Department Alignment (Contingency Matrix)
# =============================================================================
def make_fig4():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9), dpi=300, gridspec_kw={"width_ratios": [1.1, 1.3]})

    # Panel a: Community sizes bar chart
    c_sizes = [len(c) for c in non_trivial_comms]
    bars = axes[0].bar([f"C{i}" for i in range(len(c_sizes))], c_sizes, color="#2B6CB0", edgecolor="#1A365D", linewidth=0.6, width=0.7)
    for bar in bars:
        h = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width()/2.0, h + 2.5, f"{h}", ha="center", va="bottom", fontsize=8, weight="bold")
    axes[0].set_xlabel("Louvain Community ($\gamma=1.0$)", fontsize=9.5, weight="bold")
    axes[0].set_ylabel("Member Population", fontsize=9.5, weight="bold")
    axes[0].set_title("(a) Cohesive Community Sizes", fontsize=10.5, weight="bold", pad=6)
    axes[0].set_ylim(0, 215)
    axes[0].grid(True, axis="y", linestyle=":", alpha=0.6)

    # Panel b: Overlap contingency matrix for top 8 departments
    top_depts = pd.Series(list(node_departments.values())).value_counts().head(8).index
    dept_labels = [G_undir.nodes[n]["department"] for n in nodes]
    comm_labels = [node_to_comm[n] for n in nodes]
    contingency = pd.crosstab(pd.Series(dept_labels, name="Dept"), pd.Series(comm_labels, name="Comm"))
    sub_ct = contingency.loc[top_depts, list(range(len(non_trivial_comms)))]

    sns.heatmap(sub_ct, annot=True, fmt="d", cmap="Blues", cbar=False, ax=axes[1], linewidths=0.5, linecolor="#E2E8F0", annot_kws={"size": 7.5, "weight": "bold"})
    axes[1].set_xlabel("Louvain Community ID", fontsize=9.5, weight="bold")
    axes[1].set_ylabel("Official Department ID", fontsize=9.5, weight="bold")
    axes[1].set_title("(b) Department-Community Overlap", fontsize=10.5, weight="bold", pad=6)

    plt.tight_layout()
    p = FIG_DIR / "fig4_community_department_clean.png"
    plt.savefig(p, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {p}")

make_fig4()


# =============================================================================
# FIGURE 5: Integrated Centrality & Cross-Community Connectivity
# =============================================================================
def make_fig5():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.85), dpi=300)

    # Panel a: PageRank vs Cross-Community Fraction
    valid_df = cent_df.dropna(subset=["cross_community_fraction"]).copy()
    scatter = axes[0].scatter(
        valid_df["cross_community_fraction"] * 100,
        valid_df["pagerank"] * 1000,
        c=valid_df["total_degree"],
        cmap="viridis", s=22, alpha=0.7, edgecolors="none"
    )
    cbar = fig.colorbar(scatter, ax=axes[0], pad=0.02)
    cbar.set_label("Undirected Degree", fontsize=8.5, weight="bold")
    cbar.ax.tick_params(labelsize=8)

    # Annotate archetypes
    archetypes = [
        (160, "#E53E3E", "Node 160\n(Global Spanner)", (65, 6.8)),
        (451, "#805AD5", "Node 451\n(Internal Hub)", (8, 3.8)),
        (644, "#319795", "Node 644\n(Peripheral Bridge)", (65, 1.2)),
    ]
    for nid, col, label, xytext in archetypes:
        r = valid_df[valid_df["node_id"] == nid].iloc[0]
        x, y = r["cross_community_fraction"] * 100, r["pagerank"] * 1000
        axes[0].scatter(x, y, color=col, s=75, edgecolors="#1A202C", linewidth=1.2, zorder=6)
        axes[0].annotate(
            label, xy=(x, y), xytext=xytext,
            arrowprops=dict(arrowstyle="->", color=col, lw=1.1),
            fontsize=8, weight="bold", color="#1A202C",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=col, lw=0.9, alpha=0.95)
        )

    axes[0].set_xlabel("Cross-Community Edge Share (%)", fontsize=9.5, weight="bold")
    axes[0].set_ylabel(r"PageRank Score ($\times 10^{-3}$)", fontsize=9.5, weight="bold")
    axes[0].set_title("(a) Centrality vs. Boundary Spanning", fontsize=10.5, weight="bold", pad=6)
    axes[0].grid(True, linestyle=":", alpha=0.6)

    # Panel b: Degree Stratified Cross-Community Degree (Q1-Q4)
    cent_df["degree_quartile"] = pd.qcut(cent_df["total_degree"], 4, labels=["Q1 (0-11)", "Q2 (12-25)", "Q3 (26-44)", "Q4 (45-345)"])
    cent_df["top_10_pr"] = cent_df["pagerank_rank_unique"] <= 101

    sns.boxplot(
        data=cent_df[cent_df["total_degree"] > 0],
        x="degree_quartile", y="cross_community_count", hue="top_10_pr",
        palette={False: "#CBD5E0", True: "#E53E3E"},
        ax=axes[1], fliersize=2.0, linewidth=0.8, width=0.65
    )
    axes[1].set_xlabel("Total Degree Stratum", fontsize=9.5, weight="bold")
    axes[1].set_ylabel("Cross-Community Connections", fontsize=9.5, weight="bold")
    axes[1].set_title("(b) Degree-Stratified Boundary Spanning", fontsize=10.5, weight="bold", pad=6)
    
    handles, _ = axes[1].get_legend_handles_labels()
    axes[1].legend(handles, ["Remaining 90%", "Top 10% PageRank"], loc="upper left", fontsize=8, frameon=True, framealpha=0.9)
    axes[1].grid(True, axis="y", linestyle=":", alpha=0.6)

    plt.tight_layout()
    p = FIG_DIR / "fig5_integrated_centrality_clean.png"
    plt.savefig(p, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {p}")

make_fig5()
print("All 5 clean report figures generated successfully.")
