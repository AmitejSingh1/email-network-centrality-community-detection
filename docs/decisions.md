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

