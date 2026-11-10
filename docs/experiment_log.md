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
  - Node IDs: 1,005 nodes ($0 \le \text{node\_id} \le 1004$). No unassigned edge nodes; every labeled node appears in the edge list.
  - Self-loops: 642 self-loops $(u, u)$. Directed edges between distinct nodes: $25,571 - 642 = 24,929$.
  - Weakly Connected Components (WCC): 20 components.
    - Giant component: 986 nodes.
    - Peripheral components: 19 components of size 1 (Nodes: `[580, 633, 648, 653, 658, 660, 670, 675, 684, 691, 703, 711, 731, 732, 744, 746, 772, 798, 808]`).
    - Empirical finding on peripheral components: Each of the 19 singleton nodes possesses exactly one self-loop and zero incident edges to other members of the institution.
  - Strongly Connected Components (SCC): 203 components, largest SCC has 803 nodes.
  - Graph density (directed): $0.02534$.
- **Test Suite Status:** 8 passed in 0.58s (`tests/test_data_loader.py`).
- **Status:** Checkpoint 0 verified.

---

## Experiment EXP-01: Checkpoint 1 — Exploratory Network Analysis & Graph Preprocessing
- **Date:** 2026-11-11
- **Objective:** Preprocess directed communication network into dual representations (`G_raw` vs. `G_analysis`), compute comprehensive degree distributions and component decompositions, evaluate departmental communication mixing against a uniform random ordered-pair baseline, and produce publication figures.
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
  - Skewness: Heavy right-tail behavior with significant asymmetry between broadcast capability (max out-degree 333) and inbound contact volume (max in-degree 211).
- **Departmental Structure and Edge Composition:**
  - 42 departments. Size range: Min = 1 (Dept 30), Max = 109 (Dept 14), Mean = 23.93, Median = 14.5.
  - Within-department edges: 8,645 ($34.68\%$).
  - Cross-department edges: 16,284 ($65.32\%$).
  - Uniform Random Reference Model: $p_{\text{null}} = \sum_d S_d(S_d - 1) / [N(N-1)] = 47,088 / 1,009,020 \approx 4.67\%$.
  - Homophily Enrichment Factor: $34.68\% / 4.67\% \approx 7.43\times$.
  - Analytical Insight: While email communication is enriched over sevenfold within formal departments compared to uniform chance, the absolute majority of communication (65.32%) traverses departmental boundaries.
- **Generated Publication Figures:**
  - `reports/figures/fig1_degree_distributions.png` & `.pdf`: Histogram and log-log CCDF of in-degree vs. out-degree.
  - `reports/figures/fig2_department_sizes.png` & `.pdf`: Ranked department size distribution across 42 departments with mean and median thresholds.
  - `reports/figures/fig3_within_vs_cross_edges.png` & `.pdf`: Empirical within vs. cross communication proportions compared against random reference model and per-department breakdown.
- **Test Suite Status:** 17 passed in 1.24s (`tests/test_data_loader.py` and `tests/test_graph_analysis.py`).
- **Status:** Checkpoint 1 verified.
