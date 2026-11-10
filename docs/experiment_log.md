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
    - Empirical finding on peripheral components: Each of the 19 singleton nodes possesses exactly one self-loop and zero incident edges to other members of the institution. When self-loops are retained, their in-degree and out-degree are 1; when self-loops are excluded, their degree is 0.
  - Strongly Connected Components (SCC): 203 components, largest SCC has 803 nodes.
  - Graph density (directed): $0.02534$.
- **Test Suite Status:** 8 passed in 0.58s (`tests/test_data_loader.py`).
- **Status:** Checkpoint 0 verified.

