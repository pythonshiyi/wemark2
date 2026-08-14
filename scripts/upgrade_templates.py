"""Batch upgrade all templates with h5/h6 styles and refined typography."""
import json
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "assets" / "templates"

H5_DEFAULT = "font-size:14px;font-weight:600;color:#666;margin:12px 0 6px 0;"
H6_DEFAULT = "font-size:13px;font-weight:600;color:#888;margin:10px 0 4px 0;text-transform:uppercase;letter-spacing:0.5px;"

IMG_IMPROVED = "max-width:100%;height:auto;border-radius:4px;margin:12px auto;display:block;"

for fpath in sorted(TEMPLATES_DIR.glob("*.json")):
    with open(fpath, "r", encoding="utf-8") as f:
        tmpl = json.load(f)

    changed = False
    original_img = tmpl.get("img", "")
    if "display:block" not in original_img:
        tmpl["img"] = IMG_IMPROVED
        changed = True

    if "h5" not in tmpl:
        tmpl["h5"] = H5_DEFAULT
        changed = True

    if "h6" not in tmpl:
        tmpl["h6"] = H6_DEFAULT
        changed = True

    for h_tag in ["h1", "h2", "h3", "h4"]:
        styles = tmpl.get(h_tag, "")
        if "margin" in styles and "margin-bottom" not in styles:
            pass

    page_style = tmpl.get("_page_style", "")
    if "img" not in page_style and "img{display:block" not in page_style:
        pass

    if changed:
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(tmpl, f, ensure_ascii=False, indent=2)
        print(f"  Updated: {fpath.name}")
    else:
        print(f"  Skipped: {fpath.name} (already up to date)")

print("\nDone! All templates upgraded.")
