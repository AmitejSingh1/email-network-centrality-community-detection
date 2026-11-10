# Raw Data: Email-Eu-core

This directory holds the raw dataset files from the Stanford Network Analysis Project (SNAP).

## Dataset Source
- **Official Dataset Page:** https://snap.stanford.edu/data/email-Eu-core.html
- **Edge List URL:** https://snap.stanford.edu/data/email-Eu-core.txt.gz
- **Department Labels URL:** https://snap.stanford.edu/data/email-Eu-core-department-labels.txt.gz

## File Description
1. `email-Eu-core.txt.gz` (and uncompressed `email-Eu-core.txt`):
   - Directed edge list representing email communications.
   - Format: `<from_node_id> <to_node_id>` separated by whitespace.
   - Nodes represent individuals at a large European research institution.
2. `email-Eu-core-department-labels.txt.gz` (and uncompressed `email-Eu-core-department-labels.txt`):
   - Ground-truth department labels.
   - Format: `<node_id> <department_id>` separated by whitespace.
   - 42 departments numbered 0 through 41.

## Download Instructions
You can download and extract the files automatically using Python:

```python
from src.data_loader import download_dataset
download_dataset()
```
or run `python -m src.data_loader --download`.
Raw `.txt` and `.gz` files are excluded from Git version control via `.gitignore`.
