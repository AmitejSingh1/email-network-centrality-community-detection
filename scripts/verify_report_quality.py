"""
verify_report_quality.py - Comprehensive visual and layout QA for report.pdf
"""
import re
import sys
from pathlib import Path
import pymupdf

def main():
    pdf_path = Path("report.pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found.")
        sys.exit(1)

    doc = pymupdf.open(str(pdf_path))
    total_pages = len(doc)
    print(f"Total pages in document: {total_pages}")
    # Main report is 8 pages (Sections 1-6) + 1 page for References (excluded from 8-page limit)
    if total_pages != 9:
        print(f"FAIL: Expected exactly 9 pages (8 main report + 1 references), got {total_pages}")
        all_passed = False

    # Printable area:
    # A4 = 595.27 x 841.89 pt
    # Left margin: 56.69 pt (20 mm)
    # Right margin: 56.69 pt -> Right edge: 538.58 pt
    # Top margin: 56.69 pt -> Top edge: 56.69 pt
    # Bottom margin: 56.69 pt -> Bottom edge: 785.20 pt
    printable_x0 = 56.0
    printable_x1 = 539.0
    content_top_min = 55.0
    content_bottom_max = 788.0

    all_passed = True
    out_dir = Path("reports/page_images")
    out_dir.mkdir(parents=True, exist_ok=True)

    forbidden_names = ["amite", "Amitesh", "Chandra", "user"]
    matric_number = "A0352547Y"
    matric_found = False

    for page_idx, page in enumerate(doc):
        p_num = page_idx + 1
        pix = page.get_pixmap(dpi=150)
        img_file = out_dir / f"page_{p_num}.png"
        pix.save(str(img_file))
        print(f"Saved page image: {img_file}")

        text = page.get_text()

        if matric_number in text:
            matric_found = True

        for name in forbidden_names:
            if name.lower() in text.lower():
                print(f"FAIL on Page {p_num}: Found forbidden author name '{name}'")
                all_passed = False

        # Check for raw LaTeX syntax
        latex_matches = re.findall(r"(\\\\[a-zA-Z]{2,}|\$\$|\$[^$\n]+\$)", text)
        if latex_matches:
            print(f"FAIL on Page {p_num}: Found raw LaTeX strings: {latex_matches[:5]}")
            all_passed = False

        # Check bounding boxes of text blocks
        blocks = page.get_text("blocks")
        for b in blocks:
            bx0, by0, bx1, by1, btext = b[0], b[1], b[2], b[3], b[4].strip()
            # Exclude running header (< 50 pt) and running footer (> 795 pt)
            if by0 < 50 or by1 > 795:
                continue
            if bx0 < printable_x0 - 2.0:
                print(f"WARNING on Page {p_num}: Block starts left of printable margin: bx0={bx0:.1f} ({btext[:30]}...)")
            if bx1 > printable_x1 + 2.0:
                print(f"FAIL on Page {p_num}: Block extends right of printable margin: bx1={bx1:.1f} ({btext[:30]}...)")
                all_passed = False
            if by1 > content_bottom_max:
                print(f"FAIL on Page {p_num}: Block extends below bottom margin: by1={by1:.1f} ({btext[:30]}...)")
                all_passed = False

    if not matric_found:
        print("FAIL: Matriculation number A0352547Y not found in document.")
        all_passed = False
    else:
        print(f"PASS: Matriculation number {matric_number} verified in document.")

    # Check required headings
    required_headings = [
        "1 Research question and dataset",
        "2 Data preparation",
        "3 Methods and how they connect",
        "4 Evaluation and results",
        "5 Insights and limitations",
        "6 Reproducibility information",
        "References"
    ]
    full_text = " ".join(page.get_text() for page in doc)
    for h in required_headings:
        if h in full_text:
            print(f"PASS: Mandatory heading found: '{h}'")
        else:
            print(f"FAIL: Mandatory heading missing: '{h}'")
            all_passed = False

    # Check that equation assets exist
    eq_names = [f"eq{i}" for i in range(1, 6)]
    for eq in eq_names:
        eq_file = Path("reports/equations") / f"{eq}_*.png"
        matches = list(Path("reports/equations").glob(f"{eq}*.png"))
        if matches:
            print(f"PASS: Equation asset found: {matches[0].name}")
        else:
            print(f"FAIL: Equation asset missing for {eq}")
            all_passed = False

    # Check that clean figures exist
    for fig_id in range(1, 6):
        matches = list(Path("reports/figures").glob(f"fig{fig_id}*clean.png"))
        if matches:
            print(f"PASS: Figure asset found: {matches[0].name}")
        else:
            print(f"FAIL: Figure asset missing for fig{fig_id}")
            all_passed = False

    if all_passed:
        print("\n==========================================")
        print("ALL AUDIT AND QUALITY CHECKS PASSED (100%)")
        print("==========================================")
        sys.exit(0)
    else:
        print("\n==========================================")
        print("QUALITY AUDIT FAILED - SEE ERRORS ABOVE")
        print("==========================================")
        sys.exit(1)

if __name__ == "__main__":
    main()
