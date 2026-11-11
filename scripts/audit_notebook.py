"""
audit_notebook.py - Audit analysis.ipynb for compliance and execution integrity
"""
import json
import sys
from pathlib import Path

def main():
    nb_path = Path("analysis.ipynb")
    if not nb_path.exists():
        print("Error: analysis.ipynb not found")
        sys.exit(1)

    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    print(f"Total cells: {len(nb['cells'])}")
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    print(f"Code cells: {len(code_cells)}")
    has_output = sum(1 for c in code_cells if c.get("outputs"))
    print(f"Code cells with outputs: {has_output} / {len(code_cells)}")

    # Check for local src imports
    src_import_found = False
    for i, c in enumerate(code_cells):
        src = "".join(c["source"])
        if "import src" in src or "from src" in src:
            print(f"WARNING: Code cell {i+1} imports from local src: {src[:50]}")
            src_import_found = True

    if not src_import_found:
        print("PASS: No imports from local src/ module found.")

    # Check for forbidden names
    forbidden = ["amite", "Amitesh", "Chandra"]
    forbidden_found = False
    for i, c in enumerate(nb["cells"]):
        txt = "".join(c["source"])
        for name in forbidden:
            if name.lower() in txt.lower():
                print(f"FAIL: Cell {i+1} contains forbidden name: {name}")
                forbidden_found = True

    if not forbidden_found:
        print("PASS: No personal names found in notebook cells.")

    # Check for matriculation number
    matric = "A0352547Y"
    matric_found = False
    for c in nb["cells"]:
        txt = "".join(c["source"])
        if matric in txt:
            matric_found = True
            break
    if matric_found:
        print(f"PASS: Matriculation number {matric} found in notebook.")
    else:
        print(f"WARNING: Matriculation number {matric} not found in notebook.")

if __name__ == "__main__":
    main()
