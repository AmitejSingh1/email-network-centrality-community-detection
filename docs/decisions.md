# Architectural and Methodological Decisions

## Decision 0.1: Universe of Nodes Defined by Ground-Truth Department Labels
- **Context:** SNAP provides both an edge list (`email-Eu-core.txt.gz`) and a department membership file (`email-Eu-core-department-labels.txt.gz`).
- **Choice:** Establish the universe of nodes strictly as the set of nodes present in the department label file (1,005 nodes). Nodes with no incoming or outgoing edges will be preserved in the NetworkX graph with degree 0 and their official department label.
- **Rationale:** Discarding nodes that lack observed edges biases organizational analysis and alters relative community proportions.

## Decision 0.2: Preservation of Directionality vs. Undirected Projection
- **Context:** Email communication is inherently directed. However, standard Louvain community detection assumes undirected edges.
- **Choice:** Maintain a directed `nx.DiGraph` as the primary graph representation for PageRank (Lecture 6) and in-degree centrality. Derive an unweighted undirected `nx.Graph` projection for Louvain community detection (Lecture 7), collapsing reciprocal edges $(u, v)$ and $(v, u)$ into a single undirected edge $\{u, v\}$.
- **Rationale:** PageRank fundamentally relies on directed endorsement flow. Modularity optimization in standard Louvain relies on symmetric adjacency matrices to evaluate within-community edge density relative to degree product expectations.

## Decision 0.3: Explicit Quantification of Raw Records vs. Graph Features
- **Context:** Raw files may contain duplicate lines, self-loops, or isolated nodes.
- **Choice:** In the data loading pipeline, count and report raw records, duplicate directed edges, and self-loops prior to graph construction. Distinguish published SNAP statistics from independently verified counts.
- **Rationale:** Strict data provenance and auditability prevent silent mutation or misinterpretation of graph properties.

## Decision 0.4: Treatment of Peripheral Components and Self-Loops
- **Context:** The official SNAP summary reports 986 nodes in the largest WCC out of 1,005 nodes. Empirical analysis reveals that the remaining 19 nodes (`[580, 633, 648, 653, 658, 660, 670, 675, 684, 691, 703, 711, 731, 732, 744, 746, 772, 798, 808]`) each possess exactly one self-loop and zero communication with any other node in the network.
- **Choice:** The primary directed graph maintains all 25,571 edges as provided by SNAP (including the 642 self-loops), ensuring exact reproduction of SNAP edge counts. In exploratory and algorithm phases, we explicitly report metrics both with and without self-loops to clearly differentiate interpersonal communication from reflexive activity.
- **Rationale:** Preserving self-loops in raw representation maintains raw data fidelity, while distinguishing them during analysis prevents skewing community detection and PageRank dynamics.

## Decision 1.1: Maintenance of Dual Graph Representations (G_raw vs. G_analysis)
- **Context:** Self-loops represent an individual emailing themselves (e.g. personal notes, draft storage, automated calendar echoes) rather than interpersonal exchange. Retaining 642 self-loops inflates within-department communication counts and introduces artificial self-endorsement loops in PageRank.
- **Choice:** Explicitly instantiate `G_raw` (1,005 nodes, 25,571 edges) for baseline auditing and exact SNAP reproduction, and `G_analysis` (1,005 nodes, 24,929 edges) as the primary graph for all subsequent algorithms.
- **Preservation of Zero-Degree Nodes & Dangling Redistribution:** When self-loops are removed, the 19 singleton nodes become degree-0 nodes in `G_analysis`. They are strictly retained with their ground-truth department labels. In NetworkX PageRank, dangling nodes (out-degree = 0) do not sink probability; their mass is redistributed uniformly across all $|V|=1,005$ nodes at each iteration. Thus, isolated nodes receive their teleportation baseline $(1-d)/N$ plus a uniform fraction of the redistributed dangling mass from all dangling nodes in the network, converging to a non-zero stationary score ($0.0001976$) without biasing the rankings.

## Decision 1.2: Departmental Comparison against Uniform Random Ordered-Pair Reference Model
- **Context:** An empirical within-department communication fraction (e.g. 34.7%) cannot be interpreted in a vacuum without knowing what fraction would be expected purely by chance given the uneven department size distribution.
- **Choice:** Compute an exact analytical reference baseline $p_{\text{null}} = \sum_d S_d(S_d - 1) / [N(N - 1)] \approx 4.67\%$. Compare empirical within-department fraction against $p_{\text{null}}$ to compute the homophily enrichment factor ($7.43\times$).
- **Caution:** Clearly label this as an unconstrained uniform random baseline rather than a degree-preserving stub-matching configuration model. It serves as a benchmark for departmental concentration without implying organizational causality.

## Decision 1.3: Directed Reciprocity Definition and Edge Decomposition
- **Context:** Reciprocity is commonly defined as the proportion of directed edges that belong to a mutual pair: $r = |\{(u, v) \in E \mid (v, u) \in E\}| / |E|$.
- **Choice:** Standardize on NetworkX's definition ($r = 0.7112$ in $G_{\text{analysis}}$, $0.6934$ in $G_{\text{raw}}$). Explicitly document that $G_{\text{analysis}}$ contains exactly 8,865 reciprocal pairs ($17,730$ directed edges, $71.12\%$) and 7,199 unreciprocated directed edges ($28.88\%$).
- **Rationale:** Clarifies the complement relationship ($71.12\% + 28.88\% = 100\%$) and avoids confusing reciprocity with the unreciprocated edge fraction.

## Decision 2.1: Deterministic Centrality Ranking and Tie-Handling Convention
- **Context:** Discrete in-degree integers frequently produce identical degree ties across different nodes.
- **Choice:** Maintain two ranking representations in `src/centrality.py`:
  1. `rank(method='min')` for standard competition ranking where identical values share the minimum rank.
  2. `rank_unique` where ties are deterministically broken by ascending `node_id`.
- **Rationale:** Ensures complete reproducibility across operating systems and prevents non-deterministic ranking shifts during top-$k$ set evaluations.

## Decision 2.2: Analytical Rationale for Self-Loop Exclusion in PageRank
- **Context:** In $G_{\text{raw}}$, a singleton node with a self-loop acts as a sink that circulates $85\%$ of its mass back into itself, achieving $PR \approx 0.001209$ (competition rank 278 out of 1,005; competition rank 966 in $G_{\text{analysis}}$). An individual who never communicated with anyone else is artificially elevated above $72\%$ of the institution.
- **Choice:** By removing self-loops in $G_{\text{analysis}}$, singleton nodes become true dangling nodes, correctly placing them at the bottom of the prominence distribution ($PR \approx 0.0001976$, competition rank 966 out of 1,005, tied with 39 other zero-in-degree nodes).

## Decision 3.1: Unweighted Undirected Projection for Louvain Modularity Optimization
- **Context:** Standard Louvain (Lecture 7) optimizes modularity under a symmetric adjacency matrix assumption. Directed modularity exists but is less standard and alters the definition of community boundaries.
- **Choice:** Construct an unweighted undirected graph $G_{\text{undirected}}$ from $G_{\text{analysis}}$, collapsing reciprocal edges into a single undirected edge $\{u, v\}$.
- **Information Trade-off:** Direction of communication and reciprocity strength are collapsed into binary reachability. However, this preserves the fundamental topological density of interaction while enabling direct application of modularity and conductance benchmarks.
- **Preservation of Isolates:** All 1,005 nodes are preserved. The 19 isolated singletons naturally form 19 single-node communities without distorting the non-trivial communication clusters.

## Decision 3.2: Objective Comparison against Department Baseline
- **Context:** Louvain discovers 9 non-trivial communities with modularity $Q = 0.413$, compared to the 42 formal departments with $Q = 0.288$.
- **Interpretation Rule:** Do not interpret higher Louvain modularity as proof that discovered communities are "superior" or "ground truth" organizational units. Modularity is directly optimized by Louvain by construction. The comparison demonstrates that organic communication reorganizes the 42 administrative units into larger cross-departmental communication alliances.

## Decision 3.3: Mathematical Definition of Conductance and Modularity Convention Across Resolutions
- **Context:** Conductance is sometimes informally described as the fraction of cut links. Furthermore, varying the Louvain resolution parameter $\gamma$ optimizes a resolution-dependent objective $Q_\gamma$.
- **Choice:** Explicitly document conductance as $\phi(S) = |\partial(S)| / \min(\text{vol}(S), \text{vol}(V \setminus S))$ where $\text{vol}(S) = \sum_{u \in S} d(u)$, noting that internal edges contribute twice to volume. For resolution sensitivity, report both the optimization objective $Q_\gamma$ and standard modularity $Q_{\text{standard}}$ evaluated at $\gamma = 1.0$.
- **Rationale:** Ensures consistent benchmark comparisons and makes clear that standard modularity is maximized at $\gamma = 1.0$ ($Q = 0.4130$) while $Q_\gamma$ shifts monotonically due to the null-model penalty weight.

## Decision 4.1: Dual Formulation of Cross-Community Connectivity and Handling of Isolates
- **Context:** Examining whether prominent individuals act as boundary spanners requires measuring their connectivity across community boundaries. Relying solely on raw count favors high-degree nodes; relying solely on fraction overemphasizes peripheral nodes with one out-of-community link (100% fraction). Furthermore, isolated nodes have degree 0.
- **Choice:** Evaluate both `cross_community_count` and `cross_community_fraction = cross_community_count / degree` on the undirected projection $G_{\text{undirected}}$. For isolated nodes with degree 0 (the 19 singletons), set `cross_community_count = 0` and `cross_community_fraction = NaN` (strictly omitted from fractional distributions without imputing 0 or 1).
- **Rationale:** The dual representation distinguishes true structural brokers (high PageRank, high count, high fraction) from internal hubs (high PageRank, high count, low fraction) and peripheral bridges (low PageRank, low count, high fraction).

## Decision 4.2: Interpretation of Statistical Tests Under Network Autocorrelation
- **Context:** Comparing the Top 10% PageRank tier against the Remaining 90% yields $p < 10^{-50}$ on the two-sample Mann-Whitney U test.
- **Choice:** Explicitly document that network nodes violate the i.i.d. assumption underlying classical inferential statistics due to dyadic dependence, structural equivalence, and homophily.
- **Rationale:** The Mann-Whitney U test and Spearman p-values are reported strictly as descriptive indicators of large distributional separation, not as rigorous hypothesis tests confirming statistical independence or causal institutional authority.

## Decision 4.3: Methodological Treatment of Degree Confounding and Non-Causal Structural Archetypes
- **Context:** PageRank and total degree are highly correlated ($\rho_s = 0.9614$), as are total degree and cross-community count ($\rho_s = 0.9155$). We must establish whether PageRank provides information about cross-community connectivity beyond simple degree.
- **Choice:** Implement partial rank correlation controlling for total undirected degree and degree-stratified quartile analysis. Interpret individual case studies (Nodes 160, 451, 644) strictly as descriptive structural archetypes.
- **Rationale:** Controlling globally for degree attenuates rank correlation ($\rho_s \approx -0.18$) because internal endorsement concentration (as in Node 451) yields high PageRank without boundary spanning. However, within the high-degree tier (Q4, degree $\ge 45$), Top 10% PageRank nodes exhibit significantly higher cross-community count (68.56 vs. 25.17) and fraction (56.34% vs. 41.30%), demonstrating that PageRank distinguishes broad multi-cluster brokers from internal hubs among well-connected nodes. Case studies are explicitly labeled as structural archetypes rather than verified organizational roles.






