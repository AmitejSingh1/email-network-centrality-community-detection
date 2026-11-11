"""
package_submission.py - Package and validate the final submission archive A0352547Y.zip
"""
import hashlib
import sys
import tempfile
import zipfile
from pathlib import Path
import pymupdf

MATRIC_NUM = "A0352547Y"
ZIP_FILENAME = f"{MATRIC_NUM}.zip"
EXPECTED_FILES = ["report.pdf", "analysis.ipynb", "requirements.txt"]
FORBIDDEN_NAMES = ["amite", "Amitesh", "Chandra", "user"]

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print(f"=== Creating Submission Archive: {ZIP_FILENAME} ===")
    
    # 1. Verify existence of source files
    for fname in EXPECTED_FILES:
        p = Path(fname)
        if not p.exists():
            print(f"ERROR: Required file {fname} not found!")
            sys.exit(1)
        print(f"Found source: {fname} ({p.stat().st_size:,} bytes, sha256: {sha256_file(p)[:16]}...)")

    # 2. Build ZIP archive
    zip_path = Path(ZIP_FILENAME)
    if zip_path.exists():
        zip_path.unlink()
        print(f"Removed existing {ZIP_FILENAME}")

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fname in EXPECTED_FILES:
            zf.write(fname, arcname=fname)
            print(f"Added to ZIP root: {fname}")

    print(f"\nCreated {ZIP_FILENAME} ({zip_path.stat().st_size:,} bytes)")
    zip_hash = sha256_file(zip_path)
    print(f"SHA-256 of {ZIP_FILENAME}: {zip_hash}")

    # 3. Inspect and validate ZIP structure
    print("\n=== Validating ZIP Structure ===")
    with zipfile.ZipFile(zip_path, "r") as zf:
        infolist = zf.infolist()
        namelist = zf.namelist()
        print(f"Total entries in ZIP: {len(infolist)}")
        
        if sorted(namelist) != sorted(EXPECTED_FILES):
            print(f"ERROR: Expected exactly {EXPECTED_FILES}, got {namelist}")
            sys.exit(1)
        print("PASS: Exactly the 3 required files are present at the root of the ZIP.")

        for info in infolist:
            print(f"  - {info.filename}: size={info.file_size:,} bytes, compressed={info.compress_size:,} bytes")
            # Verify no directory prefixes
            if "/" in info.filename or "\\" in info.filename:
                print(f"ERROR: File {info.filename} is not at the root level!")
                sys.exit(1)

    # 4. Test extraction to temporary directory
    print("\n=== Testing Clean Extraction ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_path)
        
        for fname in EXPECTED_FILES:
            extracted_file = tmp_path / fname
            if not extracted_file.exists():
                print(f"ERROR: Extracted file {fname} missing!")
                sys.exit(1)
            
            orig_hash = sha256_file(Path(fname))
            ext_hash = sha256_file(extracted_file)
            if orig_hash != ext_hash:
                print(f"ERROR: Hash mismatch for {fname}!")
                sys.exit(1)
            print(f"PASS: {fname} extracted cleanly with identical SHA-256.")

        # 5. Check report.pdf inside ZIP for compliance
        ext_pdf = tmp_path / "report.pdf"
        doc = pymupdf.open(str(ext_pdf))
        num_pages = len(doc)
        print(f"PASS: report.pdf in ZIP has {num_pages} pages (8 main report + 1 references).")
        if num_pages != 9:
            print(f"ERROR: Expected 9 pages in report.pdf, got {num_pages}")
            doc.close()
            sys.exit(1)

        pdf_text = " ".join(page.get_text() for page in doc)
        doc.close()
        if MATRIC_NUM not in pdf_text:
            print(f"ERROR: Matriculation number {MATRIC_NUM} not found in extracted report.pdf")
            sys.exit(1)
        print(f"PASS: Matriculation number {MATRIC_NUM} present in report.pdf.")

        for name in FORBIDDEN_NAMES:
            if name.lower() in pdf_text.lower():
                print(f"ERROR: Forbidden author name '{name}' found in extracted report.pdf")
                sys.exit(1)
        print("PASS: Anonymity verified in extracted report.pdf (no author names).")

    print("\n==========================================")
    print("SUBMISSION ZIP VALIDATION COMPLETE: 100% PASS")
    print("==========================================")

if __name__ == "__main__":
    main()
