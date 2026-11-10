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
- **Top 5 Prominent Nodes:**
  1. Node 160 (Dept 36): $PR = 0.007495$ (PR Rank 1), In-Degree = 211 (In-Degree Rank 1).
  2. Node 62 (Dept 36): $PR = 0.005897$ (PR Rank 2), In-Degree = 178 (In-Degree Rank 2).
  3. Node 86 (Dept 36): $PR = 0.005711$ (PR Rank 3), In-Degree = 153 (In-Degree Rank 5).
  4. Node 107 (Dept 36): $PR = 0.005568$ (PR Rank 4), In-Degree = 168 (In-Degree Rank 3).
  5. Node 121 (Dept 36): $PR = 0.005232$ (PR Rank 5), In-Degree = 156 (In-Degree Rank 4).
- **Centrality Correlation:** Spearman rank correlation between PageRank and In-Degree: $\rho_s = 0.9828$ ($p < 10^{-300}$).
- **Top-$k$ Overlaps:** Top-10 = $90.0\%$ ($J=0.818$), Top-20 = $85.0\%$ ($J=0.739$), Top-50 = $92.0\%$ ($J=0.852$).
- **Structural Disagreements:**
  - PageRank-Boosted (Node 451, Dept 14): In-degree = 8 (Rank 659) vs. PR = $0.00307$ (Rank 37), $\Delta R = +622$. Senders include Node 365 ($PR = 0.00306$, Rank 39, Out-degree = 1), transferring $100\%$ of endorsement mass directly to Node 451.
  - In-Degree-Boosted (Node 83, Dept 17): In-degree = 85 (Rank 45) vs. PR Rank 56. Receives links from broadcasters with mean out-degree $79.1$, diluting incoming endorsements ($12.8\times$ smaller contribution per link).
- **Damping Factor Sensitivity ($d \in \{0.75, 0.85, 0.95\}$):** High pairwise stability ($\rho_s > 0.996$; top-$k$ overlap $\ge 90\%$).
- **Self-Loop Robustness Check:** $\rho_s = 0.8732$ between $G_{\text{raw}}$ and $G_{\text{analysis}}$. Self-loops in $G_{\text{raw}}$ artificially elevated 19 peripheral singletons from rank 987 to rank 380 via reflexive trapping.
- **Generated Publication Figures:**
  - `reports/figures/fig4_pagerank_vs_indegree.{png,pdf}`
  - `reports/figures/fig5_top_ranked_comparison.{png,pdf}`
  - `reports/figures/fig6_pagerank_sensitivity.{png,pdf}`
- **Test Suite Status:** 26 passed in 2.10s.
- **Status:** Checkpoint 2 verified.

---

## Experiment EXP-03: Checkpoint 3 — Louvain Community Detection & Department Alignment
- **Date:** 2026-11-11
- **Substrate Graph:** $G_{\text{undirected}}$ constructed from $G_{\text{analysis}}$:
  - Nodes: 1,005 (100% preserved, including 19 isolated singletons with degree 0).
  - Undirected edges: 16,064.
  - Reciprocal directed links collapsed: 8,865 pairs ($17,730$ directed edges, $71.12\%$ of all directed edges).
  - Unreciprocated directed links: 7,199 ($28.88\%$).
- **Louvain Community Detection Results ($\gamma = 1.0, \text{seed} = 42$):**
  - Discovered communities: 28 total.
  - Community breakdown: 9 non-trivial cohesive communities + 19 peripheral singletons.
  - Sizes of non-trivial communities:
    - C0: 190 members
    - C1: 157 members
    - C2: 145 members
    - C3: 127 members
    - C4: 125 members
    - C5: 109 members
    - C6: 91 members
    - C7: 32 members
    - C8: 10 members
    - C9–C27: 19 singletons of size 1 (the 19 isolated institution members).
  - Size summary: Min = 1, Max = 190, Mean = 35.89, Median = 1.0 (Non-trivial: Min = 10, Max = 190, Mean = 109.56, Median = 125.0).
- **Community Quality Metrics:**
  - Modularity ($Q_{\text{Louvain}}$): **$0.4130$** (indicates strong internal density relative to degree-product null model).
  - Conductance ($\phi(S)$ across 9 non-trivial communities):
    - Mean: $0.4475$
    - Median: $0.4201$
    - Min: $0.2780$ (Community 6, tightest boundary with only 27.8% boundary cut)
    - Max: $0.6719$ (Community 8, size 10)
    - Conductance for the 19 singletons is mathematically undefined (volume = 0, cut = 0).
- **Department Partition Baseline Comparison (on identical $G_{\text{undirected}}$):**
  - Modularity ($Q_{\text{dept}}$): **$0.2880$** (substantially lower than Louvain modularity $0.4130$).
  - Conductance across 42 departments:
    - Mean: $0.7871$
    - Median: $0.8644$
    - Min: $0.3010$ (Dept 3)
    - Max: $1.0000$ (Multiple small departments have 100% boundary leakage)
  - Key Insight: Formal departments exhibit severe boundary leakage (median conductance $0.864$), whereas Louvain discovers groups with substantially sharper communication boundaries (median conductance $0.420$).
- **External Agreement with Ground-Truth Department Labels:**
  - Normalized Mutual Information (NMI): **$0.5946$** ($\approx 0.595$).
  - Adjusted Rand Index (ARI): **$0.3505$** ($\approx 0.351$).
  - Interpretation: There is moderate mutual information between departments and communication communities ($NMI \approx 0.595$), but partition agreement is partial ($ARI \approx 0.351$). Organic communication does not rigidly respect administrative lines; instead, communication groups consolidate multiple departments or fracture departments across several communication communities.
- **Department 36 Investigation (Top 5 PageRank Nodes):**
  - Department 36 has 22 total members.
  - Dominant Community: 18 of 22 members ($81.82\%$) belong to Community 0 (size 190).
  - Placement of Top 5 PageRank Individuals:
    - Node 62 (Rank 2): Community 0
    - Node 107 (Rank 4): Community 0
    - Node 121 (Rank 5): Community 0
    - Node 86 (Rank 3): Community 1
    - Node 160 (Rank 1): **Community 4!**
  - Critical Observation: The #1 ranked node in the institution (Node 160) does not belong to the dominant community of Department 36 (Community 0); rather, it is anchored in Community 4. This reveals that the most prominent individuals bridge across community boundaries.
- **Random Seed Robustness ($\text{seeds} \in [42, 123, 2026, 7, 99]$ at $\gamma = 1.0$):**
  - Modularity range: $0.4125$ to $0.4166$ ($\Delta Q < 0.0042$).
  - Number of non-trivial communities: 8 or 9 across all runs.
  - NMI range: $0.5910$ to $0.6014$.
  - ARI range: $0.3254$ to $0.3615$.
  - Pairwise ARI across all 10 seed pairs: Min = $0.6906$, Max = $0.9415$, Mean = **$0.7975$**.
  - Conclusion: Discovered community macro-structure is highly robust to algorithm stochasticity.
- **Resolution Parameter Sensitivity ($\gamma \in [0.8, 1.0, 1.2]$ at seed = 42):**
  - $\gamma = 0.8$: 6 non-trivial communities + 19 singletons, $Q = 0.4590$, $NMI = 0.5272$, $ARI = 0.2223$, $ARI(\text{vs } \gamma=1.0) = 0.6245$.
  - $\gamma = 1.0$: 9 non-trivial communities + 19 singletons, $Q = 0.4130$, $NMI = 0.5946$, $ARI = 0.3505$, $ARI(\text{vs } \gamma=1.0) = 1.0000$.
  - $\gamma = 1.2$: 10 non-trivial communities + 19 singletons, $Q = 0.3830$, $NMI = 0.6247$, $ARI = 0.4321$, $ARI(\text{vs } \gamma=1.0) = 0.7618$.
  - Observation: As resolution increases from 0.8 to 1.2, modularity decreases while NMI and ARI relative to departments increase, demonstrating that higher resolution fractures macro-communities into finer groups that align more closely with smaller departmental units.
- **Generated Publication Figures:**
  - `reports/figures/fig7_community_sizes.{png,pdf}`: Ranked Louvain community size distribution.
  - `reports/figures/fig8_department_community_heatmap.{png,pdf}`: Department-community contingency matrix heatmap.
  - `reports/figures/fig9_louvain_robustness.{png,pdf}`: Seed stability ARI heatmap and resolution sensitivity curve.
- **Test Suite Status:** 34 passed in 4.23s.
- **Status:** Checkpoint 3 verified.
