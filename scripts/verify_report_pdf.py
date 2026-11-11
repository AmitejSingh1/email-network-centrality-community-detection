import sys
from pathlib import Path
import pypdf

pdf_path = Path("report.pdf")
if not pdf_path.exists():
    print("report.pdf not found!")
    sys.exit(1)

reader = pypdf.PdfReader(str(pdf_path))
num_pages = len(reader.pages)
print(f"Total PDF pages: {num_pages}")

# 1. Page count verification
assert num_pages == 7, f"Expected 7 pages, got {num_pages}"
print("Page count check PASSED: Exactly 7 pages (Main Report = Pages 1-6, References = Page 7).")

# 2. Dimensions check
for i, page in enumerate(reader.pages):
    box = page.mediabox
    width_pt = float(box.width)
    height_pt = float(box.height)
    # A4 is 595.27 x 841.89 pt
    assert abs(width_pt - 595.27) < 1.0, f"Page {i+1} width {width_pt} != A4 (595.27)"
    assert abs(height_pt - 841.89) < 1.0, f"Page {i+1} height {height_pt} != A4 (841.89)"
print("Page dimensions check PASSED: All pages are exact standard A4 (595.28 x 841.89 pt).")

# 3. Required Headings check
full_text = "\n".join([p.extract_text() for p in reader.pages])

required_headings = [
    "1 Research question and dataset",
    "2 Data preparation",
    "3 Methods and how they connect",
    "4 Evaluation and results",
    "5 Insights and limitations",
    "6 Reproducibility information",
    "References",
]

for h in required_headings:
    assert h in full_text, f"Missing heading: {h}"
    print(f"Heading verified: '{h}'")

# 4. Anonymity check
assert "A0352547Y" in full_text, "Matriculation number A0352547Y missing!"
banned_tokens = ["Amitej", "amitej", "Singh"]
for b in banned_tokens:
    assert b not in full_text, f"Banned name token '{b}' found in report!"
print("Anonymity check PASSED: Matriculation A0352547Y present, zero personal student names found.")

# 5. Appendix check
assert "Appendix" not in full_text and "Appendices" not in full_text.replace("Appendices are not included.", ""), "Forbidden appendix found!"
print("No appendices check PASSED: No appendices present.")

# 6. Check footer labels
for i, page in enumerate(reader.pages):
    txt = page.extract_text()
    if i < 6:
        assert f"Page {i+1} of {num_pages} (Main Report)" in txt, f"Page {i+1} footer incorrect!"
    else:
        assert f"Page {i+1} of {num_pages} (References — Excluded from 8-Page Limit)" in txt, f"Page {i+1} footer incorrect!"
print("Running headers & footers check PASSED: Pages 1-6 marked Main Report, Page 7 marked References.")

# 7. Check key numerical results in report
num_checks = {
    "Reciprocity (71.12%)": "71.12%" in full_text,
    "PageRank vs In-degree (0.9828)": "0.9828" in full_text,
    "Louvain Modularity (0.4130)": "0.4130" in full_text,
    "Louvain Median Conductance (0.4201)": "0.4201" in full_text,
    "Louvain NMI (0.5946)": "0.5946" in full_text,
    "Louvain ARI (0.3505)": "0.3505" in full_text,
    "Partial correlation (-0.1803)": "-0.1803" in full_text,
    "Node 160": "Node 160" in full_text,
    "Node 451": "Node 451" in full_text,
    "Node 644": "Node 644" in full_text,
}

print("\n=== NUMERICAL CONSISTENCY IN REPORT.PDF ===")
for k, v in num_checks.items():
    print(f"Check {k}: {'PASSED' if v else 'FAILED'}")
    assert v, f"Check {k} failed in report.pdf"

print("\nALL REPORT COMPLIANCE AND CONSISTENCY CHECKS PASSED!")
