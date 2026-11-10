# Experiment and Validation Log

## Experiment EXP-00: Checkpoint 0 — Dataset Verification and Environment Initialization
- **Date:** 2026-11-10
- **Environment:** Windows, Python 3.10.6
- **Objective:** Establish reproducible environment, acquire official SNAP Email-Eu-core dataset, calculate cryptographic checksums, validate raw record counts against graph invariants, and implement unit test suite.
- **Data Source:** SNAP (`https://snap.stanford.edu/data/email-Eu-core.html`)
  - `email-Eu-core.txt.gz` (SHA-256: `4b47acdb80197b085fe63c819c357ae488131ee904ed93d1b219a68b0f9e245f`, 79,754 bytes)
  - `email-Eu-core.txt` (SHA-256: `23e0ca0bce21a053025e78f7e9691ac9210ae806a0689bd5edff3c3bac572d4c`, 192,698 bytes)
  - `email-Eu-core-department-labels.txt.gz` (SHA-256: `e5abe5b4581a480032a63adcf2576c161785f45692642c6ebb0b1276f0f33669`, 2,663 bytes)
  - `email-Eu-core-department-labels.txt` (SHA-256: `91a089f21ee35eb224066456fa5322c8ad57c0f07b2da7a58a3220c72b5d54b5`, 6,537 bytes)
- **Verified Dataset Properties:**
  - Raw edge rows: 25,571 (0 malformed rows, 0 duplicate directed edges).
  - Raw label rows: 1,005 (0 malformed rows, 0 duplicate labels).
  - Department labels: Exactly 42 departments ($0 \le \text{dept\_id} \le 41$).
  - Node IDs: 1,005 nodes ($0 \le \text{node\_id} \le 1004$).
  - Self-loops: 642 self-loops $(u, u)$. Directed edges between distinct nodes: $25,571 - 642 = 24,929$.
  - Weakly Connected Components (WCC): 20 components.
    - Giant component: 986 nodes.
    - Peripheral components: 19 components of size 1.
  - Strongly Connected Components (SCC): 203 components, largest SCC has 803 nodes.
  - Graph density (directed): $0.02534$.
- **Test Suite Status:** 8 passed in 0.58s (`tests/test_data_loader.py`).
- **Status:** Checkpoint 0 verified.

---

## Experiment EXP-01: Checkpoint 1 — Exploratory Network Analysis & Graph Preprocessing
- **Date:** 2026-11-11
- **Objective:** Preprocess directed communication network into dual representations (`G_raw` vs. `G_analysis`), compute degree distributions and component decompositions, evaluate departmental communication mixing against a uniform random ordered-pair baseline, and produce publication figures.
- **Dual Representation Comparison:**
  | Metric | $G_{\text{raw}}$ (Raw Directed Graph) | $G_{\text{analysis}}$ (Analysis Directed Graph) |
  | :--- | :--- | :--- |
  | **Nodes** | 1,005 | 1,005 (preserved, no node dropped) |
  | **Edges** | 25,571 | 24,929 (interpersonal, self-loops removed) |
  | **Self-loops** | 642 | 0 |
  | **Directed Density** | $0.025317$ ($|E|/|V|^2$) | $0.024706$ ($|E|/(|V|(|V|-1))$) |
  | **WCCs (Count / Giant)** | 20 / 986 nodes | 20 / 986 nodes |
  | **SCCs (Count / Giant)** | 203 / 803 nodes | 203 / 803 nodes |
  | **Zero-Degree Nodes** | 0 | 19 (the 19 singletons preserved with labels) |
  | **Overall Reciprocity** | $0.2974$ | $0.2801$ (interpersonal pairs) |
- **Degree Distribution Findings ($G_{\text{analysis}}$):**
  - In-degree: Mean = 24.80, Std = 27.77, Median = 17.0, Min = 0, Max = 211. Percentiles: P25 = 5.0, P75 = 35.0, P95 = 81.8.
  - Out-degree: Mean = 24.80, Std = 33.12, Median = 14.0, Min = 0, Max = 333. Percentiles: P25 = 1.0, P75 = 34.0, P95 = 88.0.
  - Asymmetry: Heavy right-tail behavior with significant asymmetry between broadcast capability (max out-degree 333) and inbound contact volume (max in-degree 211).
- **Departmental Structure and Edge Composition:**
  - 42 departments. Size range: Min = 1 (Dept 30), Max = 109 (Dept 14), Mean = 23.93, Median = 14.5.
  - Within-department directed communication links: 8,645 ($34.68\%$).
  - Cross-department directed communication links: 16,284 ($65.32\%$).
  - Uniform Random Reference Model: $p_{\text{null}} = \sum_d S_d(S_d - 1) / [N(N-1)] = 47,088 / 1,009,020 \approx 4.67\%$.
  - Homophily Enrichment Factor: $34.68\% / 4.67\% \approx 7.43\times$.
- **Generated Publication Figures:**
  - `reports/figures/fig1_degree_distributions.{png,pdf}`
  - `reports/figures/fig2_department_sizes.{png,pdf}`
  - `reports/figures/fig3_within_vs_cross_edges.{png,pdf}`
- **Test Suite Status:** 17 passed in 1.24s (`tests/test_data_loader.py` and `tests/test_graph_analysis.py`).
- **Status:** Checkpoint 1 verified.

---

## Experiment EXP-02: Checkpoint 2 — PageRank & Centrality Robustness Analysis
- **Date:** 2026-11-11
- **Substrate Graph:** $G_{\text{analysis}}$ (1,005 nodes, 24,929 directed interpersonal edges, zero self-loops).
- **PageRank Parameters:** NetworkX 3.4.2 `nx.pagerank()`, $\alpha = 0.85$, $\text{tol} = 10^{-6}$, $\text{max\_iter} = 500$, uniform personalization, standard dangling redistribution.
- **Scores Verification:** Min = $0.0001976$ (isolated singletons), Max = $0.007495$ (Node 160), $\sum PR = 1.000000$ ($\pm 10^{-6}$), finite and non-negative across all 1,005 nodes.
- **Top 5 Prominent Nodes:**
  1. Node 160 (Dept 36): $PR = 0.007495$ (PR Rank 1), In-Degree = 211 (In-Degree Rank 1).
  2. Node 62 (Dept 36): $PR = 0.005897$ (PR Rank 2), In-Degree = 178 (In-Degree Rank 2).
  3. Node 86 (Dept 36): $PR = 0.005711$ (PR Rank 3), In-Degree = 153 (In-Degree Rank 5).
  4. Node 107 (Dept 36): $PR = 0.005568$ (PR Rank 4), In-Degree = 168 (In-Degree Rank 3).
  5. Node 121 (Dept 36): $PR = 0.005232$ (PR Rank 5), In-Degree = 156 (In-Degree Rank 4).
  *Note:* All top 5 most prominent nodes belong to Department 36.
- **Centrality Correlation:**
  - Spearman rank correlation between PageRank and In-Degree: $\rho_s = 0.9828$ ($p < 10^{-300}$).
  - While monotonic alignment is high overall, notable structural disagreements occur due to incoming link topology.
- **Top-$k$ Overlap ($|\text{TopK}_{PR} \cap \text{TopK}_{InDeg}| / k$):**
  - $k = 10$: $9 / 10 = 90.0\%$ (Jaccard = $0.818$). Disagreement: Node 5 in PR Top-10 (PR Rank 6, In-Deg Rank 13); Node 128 in In-Deg Top-10 (In-Deg Rank 10, PR Rank 11).
  - $k = 20$: $17 / 20 = 85.0\%$ (Jaccard = $0.739$).
  - $k = 50$: $46 / 50 = 92.0\%$ (Jaccard = $0.852$).
- **Structural Disagreement Analysis:**
  - **PageRank-Boosted Case (Node 451, Dept 14):**
    - In-degree = 8 (Rank 659 out of 1,005 — bottom third).
    - PageRank = $0.00307$ (Rank 37 out of 1,005 — top 4%).
    - Rank difference: $+622$ positions.
    - Structural Cause: Receives an email from Node 365 (Dept 14), who has an out-degree of 1 ($L(365)=1$) and a high PageRank ($PR = 0.00306$, Rank 39). Node 365 concentrates $100\%$ of their outgoing probability mass directly into Node 451.
  - **In-Degree-Boosted Case (Node 83, Dept 17):**
    - In-degree = 85 (Rank 45).
    - PageRank Rank = 56.
    - Structural Cause: Receives emails from high-volume broadcasters whose average out-degree is $79.1$ (median 65.0). Senders dilute their endorsement across dozens of individuals, giving a mean contribution of only $3.35 \times 10^{-5}$ per sender ($12.8\times$ smaller than Node 451's senders).
- **Damping Factor Sensitivity ($d \in \{0.75, 0.85, 0.95\}$):**
  - Pairwise Spearman correlation: $\rho_s(0.75, 0.85) = 0.9991$, $\rho_s(0.85, 0.95) = 0.9988$, $\rho_s(0.75, 0.95) = 0.9961$.
  - Top-$k$ Overlap with $d=0.85$:
    - $d = 0.75$: Top-10 = $90\%$, Top-20 = $100\%$, Top-50 = $96\%$.
    - $d = 0.95$: Top-10 = $100\%$, Top-20 = $95\%$, Top-50 = $96\%$.
  - Conclusion: Prominence rankings are exceptionally robust to choice of damping factor.
- **Self-Loop Robustness Check ($G_{\text{raw}}$ vs. $G_{\text{analysis}}$ at $d=0.85$):**
  - Spearman rank correlation: $\rho_s = 0.8732$ ($p < 10^{-314}$).
  - Top-$k$ overlap: Top-10 = $70.0\%$ (7/10), Top-20 = $80.0\%$ (16/20), Top-50 = $90.0\%$ (45/50).
  - Key finding: In $G_{\text{raw}}$, 19 peripheral singletons loop $85\%$ of their mass back to themselves, artificially inflating their PageRank from $0.0001976$ (rank 987) to $0.001209$ (rank 380). Excluding self-loops corrects this distortion.
- **Generated Publication Figures:**
  - `reports/figures/fig4_pagerank_vs_indegree.{png,pdf}`: Scatter and rank-rank plot with highlighted structural disagreement cases.
  - `reports/figures/fig5_top_ranked_comparison.{png,pdf}`: Slopegraph comparing top-20 individuals under both measures.
  - `reports/figures/fig6_pagerank_sensitivity.{png,pdf}`: Bump chart tracking top-15 node rank trajectories and top-$k$ overlap bar chart across $d \in \{0.75, 0.85, 0.95\}$.
- **Test Suite Status:** 26 passed in 2.10s (`tests/test_data_loader.py`, `tests/test_graph_analysis.py`, and `tests/test_centrality.py`).
- **Status:** Checkpoint 2 verified.
