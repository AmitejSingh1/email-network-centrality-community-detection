import json
import os
import shutil
from pathlib import Path

clean_dir = Path(os.environ['TEMP']) / 'dsa5101_clean_room'
nb_path = clean_dir / 'analysis.ipynb'
raw_dir = clean_dir / 'data' / 'raw'

print("=== CLEAN-ROOM DIRECTORY STATUS ===")
raw_files = [f.name for f in raw_dir.iterdir()]
print("Downloaded files in clean-room data/raw:", raw_files)

with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

cell_count = len(nb["cells"])
print("Total notebook cells:", cell_count)
errors = []
images = []
text_outputs = []

for i, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        for out in cell.get("outputs", []):
            if out.get("output_type") == "error":
                errors.append((i, out.get("ename"), out.get("evalue")))
            if "data" in out:
                for k in out["data"]:
                    if "image" in k:
                        images.append(i)
                    if "text/plain" in k:
                        text_outputs.append("".join(out["data"]["text/plain"]))
            if "text" in out:
                text_outputs.append("".join(out["text"]))

print("Errors found:", len(errors))
print("Images generated:", len(images))
assert len(errors) == 0, f"Errors occurred: {errors}"
assert len(images) == 5, f"Expected 5 figures, got {len(images)}"

full_stdout = "\n".join(text_outputs)

checks = {
    "Reciprocity (71.12%)": "71.12%" in full_stdout or "0.7112" in full_stdout,
    "PageRank vs In-degree (0.9828)": "0.9828" in full_stdout,
    "Louvain NMI (0.5946)": "0.5946" in full_stdout,
    "Louvain ARI (0.3505)": "0.3505" in full_stdout,
    "Partial Rank Correlation (-0.1803)": "-0.1803" in full_stdout,
    "Node 160 present": "160" in full_stdout,
    "Node 451 present": "451" in full_stdout,
    "Node 644 present": "644" in full_stdout,
}

print("\n=== NUMERICAL CONSISTENCY IN CLEAN-ROOM NOTEBOOK ===")
for k, v in checks.items():
    status = "PASSED" if v else "FAILED"
    print(f"Check {k}: {status}")
    assert v, f"Check {k} failed!"

dest_path = Path("c:/dsa5101_project/analysis.ipynb")
shutil.copy(nb_path, dest_path)
print(f"\nCopied cleanly executed notebook to {dest_path} ({dest_path.stat().st_size:,} bytes).")
