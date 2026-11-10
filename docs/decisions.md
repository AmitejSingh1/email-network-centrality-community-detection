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
- **Preservation of Zero-Degree Nodes:** When self-loops are removed, the 19 singleton nodes become degree-0 nodes in `G_analysis`. They are strictly retained with their ground-truth department labels. In standard PageRank, degree-0 nodes receive teleportation probability $(1 - d)/N$ and do not distribute probability outwards, correctly reflecting their complete isolation from interpersonal email flows.

## Decision 1.2: Departmental Comparison against Uniform Random Ordered-Pair Reference Model
- **Context:** An empirical within-department communication fraction (e.g. 34.7%) cannot be interpreted in a vacuum without knowing what fraction would be expected purely by chance given the uneven department size distribution.
- **Choice:** Compute an exact analytical reference baseline $p_{\text{null}} = \sum_d S_d(S_d - 1) / [N(N - 1)] \approx 4.67\%$. Compare empirical within-department fraction against $p_{\text{null}}$ to compute the homophily enrichment factor ($7.43\times$).
- **Caution:** Clearly label this as an unconstrained uniform random baseline rather than a degree-preserving stub-matching configuration model. It serves as a benchmark for departmental concentration without implying organizational causality.


