"""Generate publication-quality, high-legibility figures for the DSA5101 research report.

Tailored specifically for A4 report width (6.69 inches / 481.88 pt) with 300 DPI resolution,
rigorous constrained_layout management, non-overlapping annotations, distinct markers, and clean typography.
"""

from __future__ import annotations

import gzip
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy import stats
import seaborn as sns

# Output directory
FIG_DIR = Path("reports/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Styling configuration
plt.rcParams.update({
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.family": "sans-serif",
    "mathtext.fontset": "dejavusans",
    "figure.autolayout": False,
    "axes.edgecolor": "#4A5568",
    "axes.linewidth": 0.8,
    "grid.color": "#E2E8F0",
    "grid.linewidth": 0.6,
})

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

# Build graph representations
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
    # Width: 6.69 inches matches printable width 481.88 pt
    fig, axes = plt.subplots(1, 2, figsize=(6.69, 2.30), dpi=300, constrained_layout=True)

    in_degrees = np.array([d for _, d in G_analysis.in_degree()])
    out_degrees = np.array([d for _, d in G_analysis.out_degree()])

    # Panel a: Linear Histogram
    bins = np.linspace(0, max(in_degrees.max(), out_degrees.max()), 32)
    axes[0].hist(in_degrees, bins=bins, color="#2B6CB0", alpha=0.65, label=f"In-Degree (Median={np.median(in_degrees):.0f})", edgecolor="#1A365D", linewidth=0.5)
    axes[0].hist(out_degrees, bins=bins, color="#DD6B20", alpha=0.55, label=f"Out-Degree (Median={np.median(out_degrees):.0f})", edgecolor="#7B341E", linewidth=0.5)
    axes[0].axvline(np.mean(in_degrees), color="#1A202C", linestyle="--", linewidth=1.2, label=f"Mean = {np.mean(in_degrees):.1f}")
    axes[0].set_xlabel("Directed Degree (Number of Links)", fontsize=8.8, weight="bold", labelpad=3)
    axes[0].set_ylabel("Number of Individuals", fontsize=8.8, weight="bold", labelpad=3)
    axes[0].set_title("(a) Degree Frequency Histogram", fontsize=9.6, weight="bold", pad=5)
    axes[0].tick_params(axis="both", labelsize=7.5)
    axes[0].legend(loc="upper right", frameon=True, fontsize=7.2, framealpha=0.92, edgecolor="#CBD5E0")
    axes[0].grid(True, linestyle=":", alpha=0.6)
    axes[0].set_xlim(-5, 225)

    # Panel b: CCDF (Complementary Cumulative Distribution Function)
    for degs, label, col, marker in [(in_degrees, "In-Degree", "#2B6CB0", "o"), (out_degrees, "Out-Degree", "#DD6B20", "s")]:
        d_pos = np.sort(degs[degs > 0])
        ccdf = 1.0 - (np.arange(len(d_pos)) / len(d_pos))
        axes[1].loglog(d_pos, ccdf, marker=marker, markersize=3.0, linestyle="none", color=col, alpha=0.75, label=label)

    # Reference guide line showing heavy tail
    x_ref = np.linspace(6, 160, 50)
    y_ref = 3.2 * (x_ref ** -1.2)
    axes[1].loglog(x_ref, y_ref, "k:", alpha=0.6, linewidth=1.1, label=r"Heavy-Tail Guide ($\propto k^{-1.2}$)")

    axes[1].set_xlabel("Degree $k$ (Log Scale)", fontsize=8.8, weight="bold", labelpad=3)
    axes[1].set_ylabel(r"$P(X \geq k)$ (Log Scale)", fontsize=8.8, weight="bold", labelpad=3)
    axes[1].set_title("(b) Complementary Cumulative Distribution (CCDF)", fontsize=9.6, weight="bold", pad=5)
    axes[1].tick_params(axis="both", labelsize=7.5)
    axes[1].legend(loc="lower left", frameon=True, fontsize=7.2, framealpha=0.92, edgecolor="#CBD5E0")
    axes[1].grid(True, which="both", linestyle=":", alpha=0.5)

    p = FIG_DIR / "fig1_degree_distributions_clean.png"
    plt.savefig(p, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {p}")

make_fig1()


# =============================================================================
# FIGURE 2: Department Alignment & Homophily Enrichment
# =============================================================================
def make_fig2():
    fig, axes = plt.subplots(1, 2, figsize=(6.69, 2.30), dpi=300, constrained_layout=True)

    # Panel a: Clean top 12 departments bar chart + Median reference line
    dept_sizes = pd.Series(list(node_departments.values())).value_counts().sort_values(ascending=False)
    top12 = dept_sizes.head(12)

    labels = [f"D{d}" for d in top12.index]
    vals = list(top12.values)

    bars = axes[0].bar(range(len(labels)), vals, color="#2B6CB0", edgecolor="#1A365D", linewidth=0.6, width=0.65)
    for bar in bars:
        h = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width()/2.0, h + 1.5, f"{h}", ha="center", va="bottom", fontsize=6.8, weight="bold")

    axes[0].axhline(dept_sizes.median(), color="#DD6B20", linestyle="--", linewidth=1.1, label=f"Median = {dept_sizes.median():.1f}")
    axes[0].set_xticks(range(len(labels)))
    axes[0].set_xticklabels(labels, fontsize=7.2, weight="bold")
    axes[0].set_xlabel("Department Identifier (Top 12 by Population)", fontsize=8.8, weight="bold", labelpad=3)
    axes[0].set_ylabel("Affiliated Members", fontsize=8.8, weight="bold", labelpad=3)
    axes[0].set_title("(a) Department Size Distribution", fontsize=9.6, weight="bold", pad=5)
    axes[0].set_ylim(0, 125)
    axes[0].tick_params(axis="both", labelsize=7.5)
    axes[0].legend(loc="upper right", fontsize=7.2, frameon=True, framealpha=0.92, edgecolor="#CBD5E0")
    axes[0].grid(True, axis="y", linestyle=":", alpha=0.6)

    # Panel b: Intra vs Inter communication
    within_edges = sum(1 for u, v in G_analysis.edges() if G_analysis.nodes[u]["department"] == G_analysis.nodes[v]["department"])
    cross_edges = G_analysis.number_of_edges() - within_edges
    within_frac = within_edges / G_analysis.number_of_edges()
    cross_frac = cross_edges / G_analysis.number_of_edges()

    N = G_analysis.number_of_nodes()
    p_null = sum(s * (s - 1) for s in dept_sizes) / (N * (N - 1))
    homophily_ratio = within_frac / p_null

    # Ordered: Within Observed, Within Null Model, Cross Observed
    categories = ["Within-Dept\n(Observed)", "Within-Dept\n(Null Model)", "Cross-Dept\n(Observed)"]
    comp_vals = [within_frac * 100, p_null * 100, cross_frac * 100]
    bar_cols = ["#2B6CB0", "#718096", "#DD6B20"]
    bars2 = axes[1].bar(range(len(categories)), comp_vals, color=bar_cols, edgecolor="#1A202C", linewidth=0.6, width=0.55)
    
    for bar, val in zip(bars2, comp_vals):
        y = bar.get_height()
        axes[1].text(bar.get_x() + bar.get_width()/2.0, y + 1.5, f"{val:.1f}%", ha="center", va="bottom", weight="bold", fontsize=7.5)

    # Clean non-overlapping annotation placed above null model bar (x=1) pointing to observed within bar (x=0)
    axes[1].annotate(
        f"{homophily_ratio:.2f}× Enrichment\nOver Null Baseline",
        xy=(0.15, 34.68), xytext=(0.85, 42.0),
        arrowprops=dict(arrowstyle="->", color="#975A16", lw=1.2),
        ha="center", fontsize=7.8, weight="bold",
        bbox=dict(boxstyle="round,pad=0.25", fc="#FEFCBF", ec="#B7791F", lw=0.8)
    )

    axes[1].set_xticks(range(len(categories)))
    axes[1].set_xticklabels(categories, fontsize=7.8, weight="bold")
    axes[1].set_ylabel("Share of Directed Links (%)", fontsize=8.8, weight="bold", labelpad=3)
    axes[1].set_title("(b) Departmental Communication Composition", fontsize=9.6, weight="bold", pad=5)
    axes[1].set_ylim(0, 80)
    axes[1].tick_params(axis="y", labelsize=7.5)
    axes[1].grid(True, axis="y", linestyle=":", alpha=0.6)

    p = FIG_DIR / "fig2_department_homophily_clean.png"
    plt.savefig(p, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {p}")

make_fig2()


# =============================================================================
# FIGURE 3: PageRank vs In-Degree Centrality Disagreements
# =============================================================================
def make_fig3():
    fig, axes = plt.subplots(1, 2, figsize=(6.69, 2.22), dpi=300, constrained_layout=True)

    # Panel a: Scatter plot with concise, non-overlapping callouts
    rho_s, _ = stats.spearmanr(cent_df["pagerank"], cent_df["in_degree"])
    axes[0].scatter(cent_df["in_degree"], cent_df["pagerank"] * 1000, color="#4A5568", alpha=0.40, s=14, edgecolors="none")

    # Archetype highlights with concise labels
    focal_nodes = [
        (160, "#E53E3E", "Node 160\nRank 1 (Both)", (145, 6.4)),
        (451, "#805AD5", "Node 451\nΔR = +622", (28, 4.3)),
        (83,  "#D69E2E", "Node 83\nIn-Deg Diluted", (110, 1.3)),
    ]
    for nid, color, label, xytext in focal_nodes:
        row = cent_df[cent_df["node_id"] == nid].iloc[0]
        x, y = row["in_degree"], row["pagerank"] * 1000
        axes[0].scatter(x, y, color=color, s=55, edgecolors="#1A202C", linewidth=1.0, zorder=6)
        axes[0].annotate(
            label, xy=(x, y), xytext=xytext,
            arrowprops=dict(arrowstyle="->", color=color, lw=1.0),
            fontsize=7.2, weight="bold", color="#1A202C",
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec=color, lw=0.8, alpha=0.95)
        )

    axes[0].set_xlabel("In-Degree (Incoming Senders)", fontsize=8.8, weight="bold", labelpad=3)
    axes[0].set_ylabel(r"PageRank Score ($\times 10^{-3}$)", fontsize=8.8, weight="bold", labelpad=3)
    axes[0].set_title(f"(a) Global Centrality (Spearman $\\rho_s = {rho_s:.4f}$)", fontsize=9.6, weight="bold", pad=5)
    axes[0].tick_params(axis="both", labelsize=7.5)
    axes[0].set_xlim(-5, 230)
    axes[0].set_ylim(-0.2, 8.2)
    axes[0].grid(True, linestyle=":", alpha=0.6)

    # Panel b: Clean horizontal bar chart of rank shifts for Top 15 PageRank individuals
    top15 = cent_df.head(15).copy().sort_values(by="pagerank_rank_unique", ascending=False)
    y_pos = np.arange(len(top15))
    shift_colors = ["#38A169" if s >= 0 else "#E53E3E" for s in top15["rank_difference"]]

    axes[1].barh(y_pos, top15["rank_difference"], color=shift_colors, edgecolor="#1A202C", linewidth=0.5, height=0.65)
    axes[1].axvline(0, color="#1A202C", linestyle="-", linewidth=0.8)
    axes[1].set_yticks(y_pos)
    axes[1].set_yticklabels([f"Node {nid} (PR {r})" for nid, r in zip(top15["node_id"], top15["pagerank_rank_unique"])], fontsize=6.8, weight="bold")
    axes[1].set_xlabel("Rank Shift ΔR (In-Degree Rank − PR Rank)", fontsize=8.8, weight="bold", labelpad=3)
    axes[1].set_title("(b) Rank Shifts for Top 15 PageRank Individuals", fontsize=9.6, weight="bold", pad=5)
    axes[1].tick_params(axis="x", labelsize=7.5)
    axes[1].grid(True, axis="x", linestyle=":", alpha=0.6)

    p = FIG_DIR / "fig3_pagerank_vs_indegree_clean.png"
    plt.savefig(p, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {p}")

make_fig3()


# =============================================================================
# FIGURE 4: Community-Department Alignment (Contingency Matrix)
# =============================================================================
def make_fig4():
    fig, axes = plt.subplots(1, 2, figsize=(6.69, 2.05), dpi=300, gridspec_kw={"width_ratios": [1.0, 1.25]}, constrained_layout=True)

    # Panel a: Community sizes bar chart
    c_sizes = [len(c) for c in non_trivial_comms]
    comm_names = [f"C{i}" for i in range(len(c_sizes))]
    bars = axes[0].bar(comm_names, c_sizes, color="#2B6CB0", edgecolor="#1A365D", linewidth=0.6, width=0.65)
    for bar in bars:
        h = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width()/2.0, h + 2.0, f"{h}", ha="center", va="bottom", fontsize=6.8, weight="bold")

    axes[0].set_xlabel("Louvain Community ($\gamma=1.0$)", fontsize=8.8, weight="bold", labelpad=3)
    axes[0].set_ylabel("Member Population", fontsize=8.8, weight="bold", labelpad=3)
    axes[0].set_title("(a) Cohesive Community Sizes", fontsize=9.6, weight="bold", pad=5)
    axes[0].set_ylim(0, 220)
    axes[0].tick_params(axis="both", labelsize=7.5)
    axes[0].grid(True, axis="y", linestyle=":", alpha=0.6)

    # Panel b: Overlap contingency matrix for top 8 departments
    top_depts = pd.Series(list(node_departments.values())).value_counts().head(8).index
    dept_labels = [G_undir.nodes[n]["department"] for n in nodes]
    comm_labels = [node_to_comm[n] for n in nodes]
    contingency = pd.crosstab(pd.Series(dept_labels, name="Dept"), pd.Series(comm_labels, name="Comm"))
    sub_ct = contingency.loc[top_depts, list(range(len(non_trivial_comms)))]

    # Explicit labels
    sub_ct.index = [f"Dept {d}" for d in sub_ct.index]
    sub_ct.columns = [f"C{c}" for c in sub_ct.columns]

    sns.heatmap(
        sub_ct, annot=True, fmt="d", cmap="Blues", cbar=True,
        cbar_kws={"label": "Members", "pad": 0.03, "shrink": 0.85},
        ax=axes[1], linewidths=0.5, linecolor="#E2E8F0",
        annot_kws={"size": 6.8, "weight": "bold"}
    )
    axes[1].figure.axes[-1].yaxis.label.set_size(7.5)
    axes[1].figure.axes[-1].yaxis.label.set_weight("bold")
    axes[1].figure.axes[-1].tick_params(labelsize=6.8)

    axes[1].set_xlabel("Louvain Community", fontsize=8.8, weight="bold", labelpad=3)
    axes[1].set_ylabel("Official Department", fontsize=8.8, weight="bold", labelpad=3)
    axes[1].set_title("(b) Department-Community Overlap", fontsize=9.6, weight="bold", pad=5)
    axes[1].tick_params(axis="both", labelsize=7.2)

    p = FIG_DIR / "fig4_community_department_clean.png"
    plt.savefig(p, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {p}")

make_fig4()


# =============================================================================
# FIGURE 5: Integrated Centrality & Cross-Community Connectivity
# =============================================================================
def make_fig5():
    fig, axes = plt.subplots(1, 2, figsize=(6.69, 2.05), dpi=300, constrained_layout=True)

    # Panel a: PageRank vs Cross-Community Fraction
    valid_df = cent_df.dropna(subset=["cross_community_fraction"]).copy()
    scatter = axes[0].scatter(
        valid_df["cross_community_fraction"] * 100,
        valid_df["pagerank"] * 1000,
        c=valid_df["total_degree"],
        cmap="viridis", s=16, alpha=0.65, edgecolors="none"
    )
    cbar = fig.colorbar(scatter, ax=axes[0], pad=0.02, shrink=0.88)
    cbar.set_label("Undirected Degree", fontsize=7.5, weight="bold")
    cbar.ax.tick_params(labelsize=6.8)

    # Annotate archetypes with distinct markers and separated coordinates
    archetypes = [
        (160, "#E53E3E", "*", 110, "Node 160\nGlobal Spanner", (46, 6.5)),
        (451, "#805AD5", "D", 50, "Node 451\nInternal Hub", (12, 4.0)),
        (644, "#319795", "^", 50, "Node 644\nPeripheral Bridge", (50, 1.4)),
    ]
    for nid, col, marker, sz, label, xytext in archetypes:
        r = valid_df[valid_df["node_id"] == nid].iloc[0]
        x, y = r["cross_community_fraction"] * 100, r["pagerank"] * 1000
        axes[0].scatter(x, y, color=col, marker=marker, s=sz, edgecolors="#1A202C", linewidth=1.0, zorder=6)
        axes[0].annotate(
            label, xy=(x, y), xytext=xytext,
            arrowprops=dict(arrowstyle="->", color=col, lw=1.0),
            fontsize=7.2, weight="bold", color="#1A202C",
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec=col, lw=0.8, alpha=0.95)
        )

    axes[0].set_xlabel("Cross-Community Edge Share (%)", fontsize=8.8, weight="bold", labelpad=3)
    axes[0].set_ylabel(r"PageRank Score ($\times 10^{-3}$)", fontsize=8.8, weight="bold", labelpad=3)
    axes[0].set_title("(a) Centrality vs. Boundary Spanning", fontsize=9.6, weight="bold", pad=5)
    axes[0].tick_params(axis="both", labelsize=7.5)
    axes[0].set_xlim(-5, 105)
    axes[0].set_ylim(-0.3, 8.2)
    axes[0].grid(True, linestyle=":", alpha=0.6)

    # Panel b: Degree Stratified Cross-Community Degree (Q1-Q4)
    cent_df["degree_quartile"] = pd.qcut(
        cent_df["total_degree"], 4,
        labels=["Q1 (0-11)\nN=244", "Q2 (12-25)\nN=253", "Q3 (26-44)\nN=261", "Q4 (≥45)\nN=247"]
    )
    cent_df["top_10_pr"] = cent_df["pagerank_rank_unique"] <= 101

    sns.boxplot(
        data=cent_df[cent_df["total_degree"] > 0],
        x="degree_quartile", y="cross_community_count", hue="top_10_pr",
        palette={False: "#CBD5E0", True: "#E53E3E"},
        ax=axes[1], fliersize=1.6, linewidth=0.7, width=0.60
    )
    axes[1].set_xlabel("Undirected Degree Stratum", fontsize=8.8, weight="bold", labelpad=3)
    axes[1].set_ylabel("Cross-Community Connections", fontsize=8.8, weight="bold", labelpad=3)
    axes[1].set_title("(b) Degree-Stratified Boundary Spanning", fontsize=9.6, weight="bold", pad=5)
    axes[1].tick_params(axis="both", labelsize=7.2)
    axes[1].set_ylim(-8, 315)

    handles, _ = axes[1].get_legend_handles_labels()
    axes[1].legend(handles, ["Remaining 90%", "Top 10% PageRank"], loc="upper left", fontsize=7.2, frameon=True, framealpha=0.92, edgecolor="#CBD5E0")
    axes[1].grid(True, axis="y", linestyle=":", alpha=0.6)

    p = FIG_DIR / "fig5_integrated_centrality_clean.png"
    plt.savefig(p, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {p}")

make_fig5()
print("All 5 clean report figures generated successfully.")
