import os
import shutil
import sys
from pathlib import Path
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

os.environ["JUPYTER_PATH"] = r"C:\dsa5101_project\.venv\share\jupyter"
os.environ["PYTHONNOUSERSITE"] = "1"

project_root = Path(__file__).resolve().parent.parent
clean_dir = Path(os.environ["TEMP"]) / "dsa5101_clean_room"

# Clean directory
if clean_dir.exists():
    shutil.rmtree(clean_dir)
clean_dir.mkdir(parents=True)

# Generate fresh notebook directly into clean_dir
sys.path.insert(0, str(project_root))
from scripts.generate_notebook import generate_analysis_notebook
nb_path = clean_dir / "analysis.ipynb"
generate_analysis_notebook(nb_path)

# Copy requirements.txt
shutil.copy(project_root / "requirements.txt", clean_dir / "requirements.txt")
print("Clean-room setup complete with strictly analysis.ipynb and requirements.txt.")

# Execute notebook inside clean_dir
with open(nb_path, "r", encoding="utf-8") as f:
    nb = nbformat.read(f, as_version=4)

print("Starting clean-room execution of analysis.ipynb...")
ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
ep.preprocess(nb, {"metadata": {"path": str(clean_dir)}})

with open(nb_path, "w", encoding="utf-8") as f:
    nbformat.write(nb, f)

print(f"Clean-room notebook successfully executed and saved to {nb_path}.")
