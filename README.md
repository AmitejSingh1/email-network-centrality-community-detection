# Beyond Department Boundaries: Centrality and Communication Communities in an Email Network

## DSA5101 — Introduction to Big Data (National University of Singapore)

### Project Overview
This repository contains the complete, reproducible research project investigating communication patterns within a large European research institution using the **Email-Eu-core** network dataset from the Stanford Network Analysis Project (SNAP).

The research focuses on the intersection of two fundamental algorithm classes:
1. **PageRank (Lecture 6):** Analyzing directed structural prominence and comparing it with degree-based metrics.
2. **Graph Clustering / Community Detection (Louvain Modularity Optimization, Lecture 7):** Uncovering organic communication communities and quantifying their correspondence to formal departmental divisions.
3. **Integrated Role Analysis:** Determining whether structurally prominent individuals primarily function as internal cohesion centers within their communities or as cross-community boundary spanners.

### Research Questions
- **Primary RQ:** To what extent do communication communities align with formal department boundaries, and what role do highly central individuals play in connecting different communities?
- **RQ1 (Centrality Prominence):** How does PageRank-based prominence compare to simple in-degree centrality in a directed email network?
- **RQ2 (Community Structure):** Do communication communities discovered by modularity optimization correspond closely to formal organizational departments?
- **RQ3 (Integrated Position):** Are highly ranked individuals primarily internal community hubs or cross-community bridges?

### Repository Structure
```text
dsa5101-email-network/
|-- README.md
|-- .gitignore
|-- requirements.txt
|
|-- data/
|   |-- raw/                # Raw SNAP dataset files (excluded from Git)
|   |   |-- README.md       # Provenance and download instructions
|   |-- processed/          # Derived data matrices
|
|-- src/                    # Modular research codebase
|   |-- __init__.py
|   |-- data_loader.py      # Validated data acquisition, auditing, and graph loader
|
|-- tests/                  # Automated verification and unit test suite
|   |-- __init__.py
|   |-- test_data_loader.py # Invariant tests on synthetic fixtures and real data
|
|-- docs/                   # Methodological documentation and experiment logs
|   |-- methodology.md
|   |-- decisions.md
|   |-- experiment_log.md
|
|-- reports/                # Report artifacts, figures, and publication tables
    |-- figures/
    |-- tables/
```

### Setup and Environment
This project requires Python 3.10. To set up the virtual environment and install dependencies:

```bash
# Create virtual environment
python -m venv .venv

# Activate environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install pinned dependencies
pip install -r requirements.txt
```

### Running Tests
To run the automated test suite:
```bash
pytest
```
