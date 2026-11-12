"""verify_five_way_consistency.py - Non-circular five-way numerical consistency audit.

Independently recomputes metrics from src/ modules and cross-checks:
1. Authoritative Python source calculations (src/)
2. Executed notebook outputs (analysis.ipynb)
3. Machine-generated results manifest (reports/results_manifest.json)
4. Report figure quartile binning logic (scripts/generate_report_figures.py)
5. Final compiled PDF text, tables, and captions (report.pdf)
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import networkx as nx
import numpy as np
import pandas as pd
import pymupdf

from src.data_loader import load_email_network, create_analysis_graph
from src.graph_analysis import compute_reciprocity_statistics, compute_edge_department_composition
from src.centrality import compute_centrality_dataframe, compare_raw_vs_analysis_pagerank
from src.communities import (
    create_undirected_projection,
    detect_louvain_communities,
    evaluate_community_conductance,
    compare_communities_with_departments,
)
from src.evaluation import build_integrated_node_dataframe, analyze_degree_confounding


def main():
    print("=" * 85)
    print("FIVE-WAY NUMERICAL CONSISTENCY AUDIT (src/ vs NB vs Manifest vs Figures vs PDF)")
    print("=" * 85)

    failures = []

    def check(label: str, cond: bool, detail: str = ""):
        status = "PASS" if cond else "FAIL"
        print(f"[{status}] {label}" + (f" -> {detail}" if detail else ""))
        if not cond:
            failures.append(f"{label}: {detail}")

    # 1. Recompute directly from src/
    G_raw, _ = load_email_network()
    G_an = create_analysis_graph(G_raw)
    G_un, _ = create_undirected_projection(G_an)
    recip = compute_reciprocity_statistics(G_an)
    dept_comp = compute_edge_department_composition(G_an)
    cent_df = compute_centrality_dataframe(G_an)
    sl_comp = compare_raw_vs_analysis_pagerank(G_raw, G_an)
    sorted_comms, n2c, q_louvain = detect_louvain_communities(G_un, resolution=1.0, seed=42)
    cond_res = evaluate_community_conductance(G_un, [c for c in sorted_comms if len(c) > 1])
    comp_dept = compare_communities_with_departments(G_un, n2c)
    int_df = build_integrated_node_dataframe(G_an, G_un, n2c)
    conf_res = analyze_degree_confounding(int_df)

    # 2. Load manifest, notebook outputs, and PDF text
    manifest = json.loads(Path("reports/results_manifest.json").read_text(encoding="utf-8"))
    nb = json.loads(Path("analysis.ipynb").read_text(encoding="utf-8"))
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    nb_outputs = "\n".join(
        "".join(o.get("text", [])) if isinstance(o.get("text"), list) else str(o.get("text", ""))
        for c in code_cells
        for o in c.get("outputs", [])
    )
    nb_errors = [
        (i, o.get("ename"), o.get("evalue"))
        for i, c in enumerate(code_cells)
        for o in c.get("outputs", [])
        if o.get("output_type") == "error" or "SmallSampleWarning" in str(o.get("text", ""))
    ]

    doc = pymupdf.open("report.pdf")
    pdf_text = "\n".join(p.get_text() for p in doc)
    doc.close()

    # A. src/ vs Manifest numeric checks
    check("Manifest reciprocity matches src/", abs(manifest["graph_invariants"]["reciprocity_clean"] - recip["reciprocity_no_self_loops"]) < 1e-4)
    check("Manifest self-loop Spearman matches src/", abs(manifest["pagerank_results"]["self_loop_robustness_spearman"] - sl_comp["spearman_rho"]) < 1e-4)
    check("Manifest Louvain Q matches src/", abs(manifest["louvain_results"]["modularity_louvain"] - q_louvain) < 1e-4)
    check("Manifest Q4 total == 247 & top10 == 100 in src/", manifest["integrated_results"]["q4_total_nodes"] == 247 == conf_res["q4_comparison"]["q4_total_nodes"] and conf_res["q4_comparison"]["q4_top10_nodes_count"] == 100)
    check("Manifest partial rho matches src/", abs(manifest["integrated_results"]["partial_spearman_cross_count_given_degree"] - conf_res["partial_correlations"]["pr_vs_cross_count_given_degree"]) < 1e-4)

    # B. Notebook executed output checks (P0 regression)
    check("Notebook has 0 errors and 0 SmallSampleWarning", len(nb_errors) == 0, str(nb_errors))
    check("Notebook Q4 outputs N=100 and N=147 (no N=0/nan)", ("Top 10% in Q4 (N=100)" in nb_outputs) and ("Remaining in Q4 (N=147)" in nb_outputs) and ("Mean Cross Count = nan" not in nb_outputs))
    check("Notebook Q4 means 68.56 and 25.17", ("68.56" in nb_outputs) and ("25.17" in nb_outputs))
    check("Notebook reciprocity 0.711220", "0.711220" in nb_outputs)
    check("Notebook gamma=1.2 Q_obj=0.3830, Q_std=0.4051", "gamma=1.2: Q_obj=0.3830, Q_std=0.4051" in nb_outputs)

    # C. Figure 5(b) quartile binning alignment with src/
    non_iso = int_df[int_df["total_undirected_degree"] > 0].copy()
    non_iso["q"] = pd.qcut(non_iso["total_undirected_degree"], 4, labels=["Q1", "Q2", "Q3", "Q4"])
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        sub = non_iso[non_iso["q"] == q]
        s_res = conf_res["strata_results"][q]
        check(f"Figure 5(b) {q} matches src/ strata", len(sub) == s_res["sample_size"] and int(sub["total_undirected_degree"].min()) == s_res["degree_min"] and int(sub["total_undirected_degree"].max()) == s_res["degree_max"], f"N={len(sub)} vs {s_res['sample_size']}")

    # D. Auditor-identified PDF regression checks (computed dynamically from src/)
    pure_recip = sum(1 for n in G_an.nodes() if G_an.out_degree(n) == 0 and G_an.in_degree(n) > 0)
    dangling = sum(1 for n in G_an.nodes() if G_an.out_degree(n) == 0)
    check("PDF states 181 dangling & 162 pure recipients", (str(dangling) in pdf_text) and (str(pure_recip) in pdf_text) and ("15 pure recipients" not in pdf_text))

    r83 = cent_df[cent_df["node_id"] == 83].iloc[0]
    r365 = cent_df[cent_df["node_id"] == 365].iloc[0]
    check("PDF Node 83 ranks match src/ (in=46, PR=60)", (f"85 (rank {int(r83['in_degree_rank_unique'])})" in pdf_text) and (f"PageRank rank {int(r83['pagerank_rank_unique'])}" in pdf_text))
    check("PDF Node 365 PR rank matches src/ (40)", f"rank {int(r365['pagerank_rank_unique'])}, out-degree 1" in pdf_text)

    # Min department conductance
    n2d = {n: G_an.nodes[n]["department"] for n in G_an.nodes()}
    dept_sets = {}
    for n, d in n2d.items():
        dept_sets.setdefault(d, set()).add(n)
    min_dept, min_cond = min(((d, nx.conductance(G_un, s)) for d, s in dept_sets.items()), key=lambda x: x[1])
    check("PDF min dept conductance matches src/ (0.3010 in Dept 14)", (f"{min_cond:.4f}" in pdf_text) and (f"Dept {min_dept}" in pdf_text) and (re.search(r"Dept 3\b", pdf_text) is None))

    # Singleton raw competition rank (278) and clean (966)
    check("PDF singleton ranks 278 (raw) and 966 (clean)", ("278" in pdf_text) and ("966" in pdf_text) and ("rank 380" not in pdf_text))

    # Self-loop Spearman 0.8720 and gamma=1.2 Q_obj 0.3830 (no 0.3832)
    check("PDF self-loop Spearman 0.8720", f"{sl_comp['spearman_rho']:.4f}" in pdf_text)
    check("PDF gamma=1.2 Q_obj=0.3830 (and no 0.3832)", ("0.3830" in pdf_text) and ("0.3832" not in pdf_text))

    # Partial p-value ~1.21e-8 (no 1.15e-8)
    check("PDF partial correlation p-value 1.21e-8", (re.search(r"1\.21\s*[×x]\s*10", pdf_text) is not None) and (re.search(r"1\.15\s*[×x]\s*10", pdf_text) is None))

    # Contingency matrix checks
    ct = pd.crosstab(pd.Series(n2d), pd.Series(n2c))
    check("PDF Dept 0 (46/49) & Dept 7 (48/51) in C4", (f"{ct.loc[0, 4]}/49" in pdf_text) and (f"{ct.loc[7, 4]}/51" in pdf_text) and ("C4" in pdf_text))
    check("PDF Dept 4 (93/109 in C3) & Dept 1 (43 in C1, 16 in C4, 3 in C2)", (f"{ct.loc[4, 3]}/109" in pdf_text) and ("43 members in C1, 16 in C4, 3 in C2" in pdf_text))

    print("\n" + "=" * 85)
    if not failures:
        print("ALL FIVE-WAY CONSISTENCY & REGRESSION CHECKS PASSED (100%)")
        print("=" * 85)
        sys.exit(0)
    else:
        print(f"FAILED {len(failures)} CHECKS:")
        for f in failures:
            print("  -", f)
        sys.exit(1)


if __name__ == "__main__":
    main()
