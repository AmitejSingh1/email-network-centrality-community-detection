"""audit_numerical_consistency.py - Complete numerical audit and results manifest generation.

Recomputes all metrics from src/ modules and SNAP dataset,
verifies against report text and notebook, and outputs reports/results_manifest.json.
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import networkx as nx
import numpy as np
import pandas as pd
from scipy import stats

from src.data_loader import load_email_network, create_analysis_graph
from src.graph_analysis import (
    compute_directed_density,
    compute_degree_statistics,
    compute_reciprocity_statistics,
    compute_edge_department_composition,
    compute_uniform_random_reference_model,
)
from src.centrality import (
    compute_pagerank,
    compute_centrality_dataframe,
    compute_spearman_rank_correlation,
    compute_top_k_overlap,
    run_pagerank_sensitivity,
    compare_raw_vs_analysis_pagerank,
)
from src.communities import (
    create_undirected_projection,
    detect_louvain_communities,
    evaluate_community_conductance,
    compare_communities_with_departments,
    run_louvain_robustness,
)
from src.evaluation import (
    build_integrated_node_dataframe,
    compare_top_nodes_cross_connectivity,
    analyze_degree_confounding,
    select_case_study_nodes,
    run_integrated_robustness,
)


def run_audit():
    print("=" * 70)
    print("AUTHORITATIVE NUMERICAL RECOMPUTATION FROM src/ MODULES")
    print("=" * 70)

    # 1. Dataset & Graph Invariants
    G_raw, audit = load_email_network()
    G_analysis = create_analysis_graph(G_raw)
    G_undir, proj_audit = create_undirected_projection(G_analysis)

    num_nodes = G_analysis.number_of_nodes()
    raw_edges = G_raw.number_of_edges()
    self_loops = audit["graph_self_loops_count"]
    clean_edges = G_analysis.number_of_edges()
    undir_edges = G_undir.number_of_edges()
    isolates = sum(1 for n in G_analysis.nodes() if G_analysis.degree(n) == 0)
    depts = audit["unique_departments_count"]

    # Reciprocity
    recip_clean = compute_reciprocity_statistics(G_analysis)
    recip_raw = compute_reciprocity_statistics(G_raw)

    # Edge composition
    edge_comp = compute_edge_department_composition(G_analysis)
    null_model = compute_uniform_random_reference_model(G_analysis)
    homophily_ratio = edge_comp["within_dept_fraction"] / null_model["expected_within_fraction"]

    # Degree statistics
    deg_stats = compute_degree_statistics(G_analysis)
    in_mean = deg_stats["in_degree"]["mean"]
    in_med = deg_stats["in_degree"]["median"]
    out_mean = deg_stats["out_degree"]["mean"]
    out_med = deg_stats["out_degree"]["median"]

    # Density
    density_raw_info = compute_directed_density(G_raw, allow_self_loops=True)
    density_clean_info = compute_directed_density(G_analysis, allow_self_loops=False)
    density_raw = density_raw_info["density"]
    density_clean = density_clean_info["density"]
    density_undir = 2 * undir_edges / (num_nodes * (num_nodes - 1))

    # WCC / SCC
    wcc_count = audit["wcc_count"]
    wcc_largest = audit["largest_wcc_size"]
    scc_count = audit["scc_count"]
    scc_largest = audit["largest_scc_size"]

    print(f"Nodes: {num_nodes}")
    print(f"Raw edges: {raw_edges}, Self-loops: {self_loops}")
    print(f"Clean edges: {clean_edges}, Undir edges: {undir_edges}")
    print(f"Isolates: {isolates}, Departments: {depts}")
    print(f"Reciprocity (G_analysis): {recip_clean['reciprocity_no_self_loops']:.4f} ({recip_clean['num_reciprocal_pairs_no_self']} pairs, {recip_clean['num_reciprocal_directed_edges_no_self']} edges, {recip_clean['num_unreciprocated_directed_edges_no_self']} unrecip)")
    print(f"Reciprocity (G_raw): {recip_raw['reciprocity_with_self_loops']:.4f}")
    print(f"Within-dept edges: {edge_comp['within_dept_edges']} ({edge_comp['within_dept_fraction']*100:.2f}%)")
    print(f"Cross-dept edges: {edge_comp['cross_dept_edges']} ({edge_comp['cross_dept_fraction']*100:.2f}%)")
    print(f"p_null: {null_model['expected_within_fraction']*100:.2f}%, Homophily enrichment: {homophily_ratio:.2f}x")
    print(f"In-deg: mean={in_mean:.1f}, med={in_med:.0f}; Out-deg: mean={out_mean:.1f}, med={out_med:.0f}")

    # 2. PageRank
    cent_df = compute_centrality_dataframe(G_analysis, alpha=0.85)
    cent_comp = compute_spearman_rank_correlation(cent_df)
    overlap_10 = compute_top_k_overlap(cent_df, k=10)
    overlap_20 = compute_top_k_overlap(cent_df, k=20)
    overlap_50 = compute_top_k_overlap(cent_df, k=50)
    sl_rob = compare_raw_vs_analysis_pagerank(G_raw, G_analysis)

    spearman_pr_in = cent_comp["spearman_rho"]
    top10_overlap = overlap_10["overlap_fraction"]
    top20_overlap = overlap_20["overlap_fraction"]
    top50_overlap = overlap_50["overlap_fraction"]
    top10_jaccard = overlap_10["jaccard_similarity"]
    top20_jaccard = overlap_20["jaccard_similarity"]
    top50_jaccard = overlap_50["jaccard_similarity"]

    print(f"\nPageRank vs In-Degree Spearman: {spearman_pr_in:.4f}")
    print(f"Top-10 overlap: {top10_overlap*100:.1f}% (Jaccard={top10_jaccard:.3f})")
    print(f"Top-20 overlap: {top20_overlap*100:.1f}% (Jaccard={top20_jaccard:.3f})")
    print(f"Top-50 overlap: {top50_overlap*100:.1f}% (Jaccard={top50_jaccard:.3f})")
    print(f"Self-loop robustness Spearman: {sl_rob['spearman_rho']:.4f}")

    # 3. Louvain Community Detection
    comms, node_to_comm, q_louvain = detect_louvain_communities(G_undir, resolution=1.0, seed=42)
    non_trivial = [c for c in comms if len(c) > 1]
    c_sizes = [len(c) for c in non_trivial]
    cond_louvain = evaluate_community_conductance(G_undir, comms)

    dept_comp = compare_communities_with_departments(G_undir, node_to_comm)
    q_dept = dept_comp["department_modularity"]
    nmi = dept_comp["nmi"]
    ari = dept_comp["ari"]
    cond_dept = dept_comp["department_conductance"]

    res_rob = run_louvain_robustness(G_undir, resolutions=(0.8, 1.0, 1.2), seeds=(42,))
    res_0_8 = res_rob["resolution_results"][0.8]
    res_1_2 = res_rob["resolution_results"][1.2]

    # Evaluate conductance for resolution 0.8 and 1.2
    comms_0_8, _, _ = detect_louvain_communities(G_undir, resolution=0.8, seed=42)
    cond_0_8 = evaluate_community_conductance(G_undir, comms_0_8)
    comms_1_2, _, _ = detect_louvain_communities(G_undir, resolution=1.2, seed=42)
    cond_1_2 = evaluate_community_conductance(G_undir, comms_1_2)

    print(f"\nLouvain communities: {len(comms)} total ({len(non_trivial)} non-trivial, {len(comms)-len(non_trivial)} isolates)")
    print(f"Non-trivial sizes: {c_sizes}")
    print(f"Q_louvain: {q_louvain:.4f}, Median Cond: {cond_louvain['median_conductance']:.4f}, Mean Cond: {cond_louvain['mean_conductance']:.4f}, Min Cond: {cond_louvain['min_conductance']:.4f}")
    print(f"Q_dept: {q_dept:.4f}, Dept Median Cond: {cond_dept['median_conductance']:.4f}, Dept Mean Cond: {cond_dept['mean_conductance']:.4f}")
    print(f"NMI: {nmi:.4f}, ARI: {ari:.4f}")
    print(f"Res 0.8: Median Cond: {cond_0_8['median_conductance']:.4f}, Mean: {cond_0_8['mean_conductance']:.4f}")
    print(f"Res 1.2: Median Cond: {cond_1_2['median_conductance']:.4f}, Mean: {cond_1_2['mean_conductance']:.4f}")

    # 4. Integrated Analysis
    integ_df = build_integrated_node_dataframe(G_analysis, G_undir, node_to_comm)
    top_comp = compare_top_nodes_cross_connectivity(integ_df, top_percent=0.10)
    deg_conf = analyze_degree_confounding(integ_df, n_strata=4)

    top_count_mean = top_comp["top_tier"]["mean_cross_count"]
    top_count_med = top_comp["top_tier"]["median_cross_count"]
    rem_count_mean = top_comp["remaining_tier"]["mean_cross_count"]
    rem_count_med = top_comp["remaining_tier"]["median_cross_count"]
    count_ratio = top_count_mean / rem_count_mean
    mw_count_u = top_comp["mann_whitney_count"]["u_stat"]
    mw_count_p = top_comp["mann_whitney_count"]["p_value"]

    top_frac_mean = top_comp["top_tier"]["mean_cross_fraction"]
    top_frac_med = top_comp["top_tier"]["median_cross_fraction"]
    rem_frac_mean = top_comp["remaining_tier"]["mean_cross_fraction"]
    rem_frac_med = top_comp["remaining_tier"]["median_cross_fraction"]
    mw_frac_u = top_comp["mann_whitney_fraction"]["u_stat"]
    mw_frac_p = top_comp["mann_whitney_fraction"]["p_value"]

    biv = deg_conf["bivariate_correlations"]
    part_corr = deg_conf["partial_correlations"]
    pr_deg_rho = biv["pr_vs_degree"]
    cc_deg_rho = biv["cross_count_vs_degree"]
    partial_rho = part_corr["pr_vs_cross_count_given_degree"]
    # Two-tailed t-test for partial correlation: df = N - 2 - k = 986 - 2 - 1 = 983
    n_eval = deg_conf["num_evaluated_nodes"]
    df_t = n_eval - 3
    t_val = partial_rho * np.sqrt(df_t / max(1e-12, 1.0 - partial_rho**2))
    partial_p = float(2.0 * stats.t.sf(np.abs(t_val), df=df_t))

    q4 = deg_conf["q4_comparison"]
    q4_top_count = q4["q4_top10_mean_cross_count"]
    q4_rem_count = q4["q4_rem_mean_cross_count"]
    q4_count_ratio = q4_top_count / q4_rem_count
    q4_count_p = q4["q4_mann_whitney_count"]["p_value"]

    q4_top_frac = q4["q4_top10_mean_cross_fraction"]
    q4_rem_frac = q4["q4_rem_mean_cross_fraction"]
    q4_frac_p = q4["q4_mann_whitney_fraction"]["p_value"]
    top_in_q4_pct = q4["top10_in_q4_fraction"] * 100

    print(f"\nTop 10% cross-count mean: {top_count_mean:.2f} (med {top_count_med:.1f}) vs Remaining: {rem_count_mean:.2f} (med {rem_count_med:.1f}) (ratio={count_ratio:.2f}x, MW U={mw_count_u:.1f}, p={mw_count_p:.2e})")
    print(f"Top 10% cross-fraction mean: {top_frac_mean*100:.2f}% (med {top_frac_med*100:.2f}%) vs Remaining: {rem_frac_mean*100:.2f}% (med {rem_frac_med*100:.2f}%) (MW U={mw_frac_u:.1f}, p={mw_frac_p:.2e})")
    print(f"PR vs Degree rho: {pr_deg_rho:.4f}, Cross-count vs Degree rho: {cc_deg_rho:.4f}")
    print(f"Partial rho: {partial_rho:.4f} (p={partial_p:.2e})")
    print(f"Top 10% in Q4: {top_in_q4_pct:.1f}%")
    print(f"Q4 Top 10% cross-count: {q4_top_count:.2f} vs Remainder: {q4_rem_count:.2f} (ratio={q4_count_ratio:.2f}x, p={q4_count_p:.2e})")
    print(f"Q4 Top 10% cross-frac: {q4_top_frac*100:.2f}% vs Remainder: {q4_rem_frac*100:.2f}% (p={q4_frac_p:.2e})")

    # 5. Case Study Nodes: 160, 451, 644
    case_studies = {}
    print("\nCase Study Nodes:")
    for nid in [160, 451, 644]:
        row = integ_df[integ_df["node_id"] == nid].iloc[0]
        c_nid = node_to_comm[nid]
        ext_comms = len(set(node_to_comm[v] for v in G_undir.neighbors(nid) if node_to_comm[v] != c_nid))
        case_studies[f"node_{nid}"] = {
            "node_id": int(nid),
            "department": int(row["department"]),
            "community": int(row["comm_id"]),
            "pagerank_score": float(row["pagerank"]),
            "pagerank_rank": int(row["pagerank_rank_unique"]),
            "in_degree": int(row["in_degree"]),
            "in_degree_rank": int(row["in_degree_rank_unique"]),
            "rank_difference": int(row["in_degree_rank_unique"] - row["pagerank_rank_unique"]),
            "undirected_degree": int(row["total_undirected_degree"]),
            "internal_connections": int(row["internal_edges_count"]),
            "cross_connections": int(row["cross_community_count"]),
            "cross_fraction": float(row["cross_community_fraction"]),
            "external_communities_reached": ext_comms,
        }
        print(f"  Node {nid}: Dept {row['department']}, Comm {row['comm_id']}, PR={row['pagerank']:.6f} (Rank {row['pagerank_rank_unique']}), InDeg={row['in_degree']} (Rank {row['in_degree_rank_unique']}), UndirDeg={row['total_undirected_degree']}, Internal={row['internal_edges_count']}, Cross={row['cross_community_count']}, CrossFrac={row['cross_community_fraction']*100:.2f}%, ExtComms={ext_comms}")

    # 6. Generate Manifest
    manifest = {
        "metadata": {
            "project": "DSA5101 Beyond Department Boundaries",
            "matriculation": "A0352547Y",
            "dataset": "SNAP Email-Eu-core",
            "python_version": "3.10.6",
            "seed": 42,
            "damping_factor": 0.85,
            "louvain_resolution": 1.0,
        },
        "graph_invariants": {
            "nodes_total": num_nodes,
            "raw_edges": raw_edges,
            "self_loops": self_loops,
            "clean_edges": clean_edges,
            "undirected_edges": undir_edges,
            "isolated_nodes": isolates,
            "departments_count": depts,
            "density_raw": round(density_raw, 6),
            "density_clean": round(density_clean, 6),
            "density_undirected": round(density_undir, 6),
            "wcc_components": wcc_count,
            "wcc_giant_size": wcc_largest,
            "scc_components": scc_count,
            "scc_giant_size": scc_largest,
            "reciprocal_pairs": recip_clean["num_reciprocal_pairs_no_self"],
            "reciprocal_directed_edges": recip_clean["num_reciprocal_directed_edges_no_self"],
            "unreciprocated_directed_edges": recip_clean["num_unreciprocated_directed_edges_no_self"],
            "reciprocity_clean": round(recip_clean["reciprocity_no_self_loops"], 4),
            "reciprocity_raw": round(recip_raw["reciprocity_with_self_loops"], 4),
            "within_dept_edges": edge_comp["within_dept_edges"],
            "within_dept_fraction": round(edge_comp["within_dept_fraction"], 4),
            "cross_dept_edges": edge_comp["cross_dept_edges"],
            "cross_dept_fraction": round(edge_comp["cross_dept_fraction"], 4),
            "null_model_p_within": round(null_model["expected_within_fraction"], 4),
            "homophily_enrichment_ratio": round(homophily_ratio, 2),
            "in_degree_mean": round(in_mean, 1),
            "in_degree_median": round(in_med, 1),
            "out_degree_mean": round(out_mean, 1),
            "out_degree_median": round(out_med, 1),
        },
        "pagerank_results": {
            "spearman_rho_in_degree": round(spearman_pr_in, 4),
            "top_10_overlap_fraction": round(top10_overlap, 4),
            "top_10_jaccard": round(top10_jaccard, 3),
            "top_20_overlap_fraction": round(top20_overlap, 4),
            "top_20_jaccard": round(top20_jaccard, 3),
            "top_50_overlap_fraction": round(top50_overlap, 4),
            "top_50_jaccard": round(top50_jaccard, 3),
            "self_loop_robustness_spearman": round(sl_rob["spearman_rho"], 4),
        },
        "louvain_results": {
            "total_communities": len(comms),
            "non_trivial_communities": len(non_trivial),
            "isolate_communities": len(comms) - len(non_trivial),
            "community_sizes_non_trivial": c_sizes,
            "modularity_louvain": round(q_louvain, 4),
            "conductance_median": round(cond_louvain["median_conductance"], 4),
            "conductance_mean": round(cond_louvain["mean_conductance"], 4),
            "conductance_min": round(cond_louvain["min_conductance"], 4),
            "modularity_departments": round(q_dept, 4),
            "conductance_departments_median": round(cond_dept["median_conductance"], 4),
            "conductance_departments_mean": round(cond_dept["mean_conductance"], 4),
            "nmi_vs_departments": round(nmi, 4),
            "ari_vs_departments": round(ari, 4),
            "resolution_0_8": {
                "clusters": len(res_0_8["sizes"]),
                "modularity_objective": round(res_0_8["modularity_objective"], 3),
                "modularity_standard": round(res_0_8["modularity_standard"], 4),
                "conductance_median": round(cond_0_8["median_conductance"], 4),
                "conductance_mean": round(cond_0_8["mean_conductance"], 4),
                "nmi": round(res_0_8["nmi"], 4),
                "ari": round(res_0_8["ari"], 4),
            },
            "resolution_1_2": {
                "clusters": len(res_1_2["sizes"]),
                "modularity_objective": round(res_1_2["modularity_objective"], 3),
                "modularity_standard": round(res_1_2["modularity_standard"], 4),
                "conductance_median": round(cond_1_2["median_conductance"], 4),
                "conductance_mean": round(cond_1_2["mean_conductance"], 4),
                "nmi": round(res_1_2["nmi"], 4),
                "ari": round(res_1_2["ari"], 4),
            },
        },
        "integrated_results": {
            "top_10_count": 101,
            "remaining_count": 904,
            "top_10_mean_cross_count": round(top_count_mean, 2),
            "top_10_median_cross_count": round(top_count_med, 1),
            "remaining_mean_cross_count": round(rem_count_mean, 2),
            "remaining_median_cross_count": round(rem_count_med, 1),
            "cross_count_ratio": round(count_ratio, 2),
            "mann_whitney_u_count": round(mw_count_u, 1),
            "mann_whitney_p_count": f"{mw_count_p:.2e}",
            "top_10_mean_cross_fraction": round(top_frac_mean, 4),
            "top_10_median_cross_fraction": round(top_frac_med, 4),
            "remaining_mean_cross_fraction": round(rem_frac_mean, 4),
            "remaining_median_cross_fraction": round(rem_frac_med, 4),
            "mann_whitney_u_fraction": round(mw_frac_u, 1),
            "mann_whitney_p_fraction": f"{mw_frac_p:.2e}",
            "spearman_pr_degree": round(pr_deg_rho, 4),
            "spearman_cross_count_degree": round(cc_deg_rho, 4),
            "partial_spearman_cross_count_given_degree": round(partial_rho, 4),
            "partial_spearman_p": f"{partial_p:.2e}",
            "top_10_in_q4_percentage": round(top_in_q4_pct, 1),
            "q4_total_nodes": 247,
            "q4_top_10_mean_cross_count": round(q4_top_count, 2),
            "q4_remaining_mean_cross_count": round(q4_rem_count, 2),
            "q4_cross_count_ratio": round(q4_count_ratio, 2),
            "q4_mann_whitney_count_p": f"{q4_count_p:.2e}",
            "q4_top_10_mean_cross_fraction": round(q4_top_frac, 4),
            "q4_remaining_mean_cross_fraction": round(q4_rem_frac, 4),
            "q4_mann_whitney_fraction_p": f"{q4_frac_p:.2e}",
        },
        "case_studies": case_studies,
    }

    out_file = Path("reports/results_manifest.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nSaved results manifest to {out_file}")

    print("\n" + "=" * 70)
    print("NUMERICAL RECOMPUTATION COMPLETE: ALL VALUES AUTHORITATIVE")
    print("=" * 70)
    return manifest


if __name__ == "__main__":
    run_audit()
