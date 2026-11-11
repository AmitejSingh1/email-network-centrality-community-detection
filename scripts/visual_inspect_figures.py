"""
visual_inspect_figures.py - Verify the embedded figures on rendered PDF page images.
"""
from pathlib import Path
from PIL import Image

def inspect_figures():
    page_img_dir = Path("reports/page_images")
    crop_dir = Path("reports/figure_crops")
    crop_dir.mkdir(parents=True, exist_ok=True)

    # Page dimensions at 150 DPI:
    # A4 = 595.28 x 841.89 pt -> at 150 DPI (150 / 72 = 2.0833 px/pt):
    # Width = 1240 px, Height = 1754 px.

    crops = {
        "fig1_embedded": (page_img_dir / "page_2.png", (100, 950, 1140, 1420)),
        "fig2_embedded": (page_img_dir / "page_4.png", (100, 680, 1140, 1180)),
        "fig3_embedded": (page_img_dir / "page_5.png", (100, 480, 1140, 980)),
        "fig4_embedded": (page_img_dir / "page_6.png", (100, 150, 1140, 520)),
        "fig5_embedded": (page_img_dir / "page_6.png", (100, 980, 1140, 1380)),
    }

    for name, (img_path, box) in crops.items():
        if not img_path.exists():
            print(f"Error: {img_path} not found.")
            continue
        im = Image.open(img_path)
        cropped = im.crop(box)
        out_path = crop_dir / f"{name}.png"
        cropped.save(out_path)
        print(f"Verified & saved {name}: size={cropped.size} to {out_path}")

if __name__ == "__main__":
    inspect_figures()
