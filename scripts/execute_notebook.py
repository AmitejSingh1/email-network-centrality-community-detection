"""Execute analysis.ipynb cleanly and save outputs."""

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor


def execute_notebook(nb_path: str = "analysis.ipynb") -> None:
    print(f"Reading {nb_path}...")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = nbf.read(f, as_version=4)

    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")

    print("Executing notebook cells...")
    ep.preprocess(nb, {"metadata": {"path": "."}})
    print("Execution complete!")

    with open(nb_path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"Saved executed notebook to {nb_path}.")


if __name__ == "__main__":
    execute_notebook("analysis.ipynb")
