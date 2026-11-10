# Research Methodology: Email Network Centrality and Community Structure

## 1. Research Question
**Primary Question:**
To what extent do communication communities align with formal department boundaries, and what role do highly central individuals play in connecting different communities?

### Supporting Questions:
- **RQ1 (Centrality Prominence):** How does PageRank-based prominence compare to simple in-degree centrality in a directed email network? Does PageRank prioritize individuals receiving emails from high-volume sources differently than in-degree?
- **RQ2 (Community Structure):** Do communication communities discovered by modularity optimization (Louvain) correspond closely to formal organizational departments, or do they transcend departmental lines?
- **RQ3 (Integrated Analysis):** Are highly ranked individuals primarily internal hubs within their respective communities, or do they act as bridges spanning multiple communities?

---

## 2. Dataset Specification: Email-Eu-core
- **Source:** Stanford Network Analysis Project (SNAP), `https://snap.stanford.edu/data/email-Eu-core.html`.
- **Institution:** Large European research institution.
- **Entities:** 1,005 anonymized members ($V = \{0, 1, \dots, 1004\}$).
- **Communication Links:** 25,571 directed edges $(u, v)$ where person $u$ sent at least one email to person $v$.
- **Department Labels:** Ground-truth department memberships mapping each node to one of 42 departments ($0$ to $41$).
- **Dual Graph Representations:**
  - $G_{\text{raw}}$: Original directed graph containing all 1,005 nodes and 25,571 directed edges (including 642 self-loops).
  - $G_{\text{analysis}}$: Cleaned directed graph containing all 1,005 nodes and 24,929 directed interpersonal edges (self-loops removed). The 19 nodes that only had self-loops are preserved with in-degree = 0, out-degree = 0, and their valid department attributes. This is the primary representation for PageRank, community detection, and cross-community analysis.
- **Directed Density Formulas:**
  - Raw density (with self-loops permitted):
    $$\rho_{\text{raw}} = \frac{|E|}{|V|^2} = \frac{25,571}{1,005^2} \approx 0.025317 \quad \left(\text{or } \frac{|E|}{|V|(|V|-1)} = \frac{25,571}{1,009,020} \approx 0.025342\right)$$
  - Analysis density (strictly interpersonal directed pairs):
    $$\rho_{\text{analysis}} = \frac{|E_{\text{interpersonal}}|}{|V|(|V|-1)} = \frac{24,929}{1,005 \times 1,004} = \frac{24,929}{1,009,020} \approx 0.024706$$
- **Uniform Random Ordered-Pair Reference Model (Department Baseline):**
  Holding empirical department sizes $S_d$ ($d \in \{0, \dots, 41\}$) fixed, the expected fraction of edges falling within the same department under a uniform random allocation across all ordered pairs $(u, v)$ with $u \neq v$ is:
  $$p_{\text{null}} = \frac{\sum_{d=0}^{41} S_d(S_d - 1)}{|V|(|V| - 1)} = \frac{47,088}{1,009,020} \approx 0.046667 \quad (4.67\%)$$
  Empirical within-department communication ($34.68\%$) is evaluated against $p_{\text{null}}$ to determine the homophily enrichment ratio:
  $$\text{Enrichment} = \frac{f_{\text{within}}}{p_{\text{null}}} = \frac{0.346785}{0.046667} \approx 7.43\times$$


---

## 3. Algorithm Classes and Formulations

### Algorithm Class 1: PageRank (Lecture 6)
PageRank models stationary probability under random walk with uniform teleportation:
$$PR(v) = \frac{1 - d}{|V|} + d \sum_{u \in In(v)} \frac{PR(u)}{Out(u)}$$
- Primary damping factor: $d = 0.85$.
- Baseline comparison: In-degree $k_{in}(v) = |In(v)|$.
- Centrality correlation: Spearman rank correlation $\rho_s$ and top-$k$ overlap for $k \in \{10, 20, 50\}$.
- Sensitivity check: $d \in \{0.75, 0.85, 0.95\}$.

### Algorithm Class 2: Louvain Modularity Optimization (Lecture 7)
Louvain optimizes modularity on the unweighted undirected projection of the communication graph:
$$Q = \frac{1}{2m} \sum_{i,j} \left[ A_{ij} - \frac{k_i k_j}{2m} \right] \delta(c_i, c_j)$$
- Primary parameters: Resolution $\gamma = 1.0$, random seed = 42.
- Evaluation metrics: Modularity $Q$, conductance $\phi(S)$, Normalized Mutual Information (NMI), and Adjusted Rand Index (ARI) against department labels.
- Robustness: Multiple random seeds (42, 123, 2026, 7, 99) and resolution checks ($\gamma \in \{0.8, 1.0, 1.2\}$).

### Integrated Metric: Cross-Community Connectivity
For each individual node $v$ in undirected graph $G$:
$$CrossCommunityFraction(v) = \frac{|\{u \in N(v) \mid c_u \neq c_v\}|}{d(v)}$$
with $CrossCommunityCount(v) = |\{u \in N(v) \mid c_u \neq c_v\}|$.
For isolated nodes ($d(v) = 0$), $CrossCommunityFraction(v)$ is undefined (`NaN`).
