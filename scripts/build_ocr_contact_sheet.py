"""OCR review contact sheet + HTML index (predictions preserved; GT human-filled)."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    csv_path = ROOT / "docs/evaluation/ocr/ocr_review_annotations.csv"
    out_dir = ROOT / "docs/evaluation/ocr/review_package_20261009"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))

    thumbs = []
    manifest = []
    for row in rows:
        path = Path(row["image_path"])
        img = cv2.imread(str(path)) if path.is_file() else None
        if img is None:
            continue
        h, w = img.shape[:2]
        scale = min(320 / max(w, 1), 120 / max(h, 1))
        tw, th = max(40, int(w * scale)), max(40, int(h * scale))
        thumb = cv2.resize(img, (tw, th))
        pred = (row.get("predicted_ocr_text") or "").strip() or "(empty)"
        label = f"{row['image_id']} pred={pred[:12]}"
        cv2.putText(thumb, label, (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        thumbs.append(thumb)
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path.name
        manifest.append(
            {
                "image_id": row["image_id"],
                "relative_path": str(rel).replace("\\", "/"),
                "predicted_ocr_text": row.get("predicted_ocr_text") or "",
                "ground_truth_plate_text": row.get("ground_truth_plate_text") or "",
                "include_in_cer": row.get("include_in_cer") or "no",
            }
        )

    cols = 5
    rows_n = math.ceil(len(thumbs) / cols) if thumbs else 1
    cell_h, cell_w = 140, 330
    sheet = np.full((rows_n * cell_h, cols * cell_w, 3), 255, dtype=np.uint8)
    for i, thumb in enumerate(thumbs):
        r, c = divmod(i, cols)
        y0, x0 = r * cell_h, c * cell_w
        th, tw = thumb.shape[:2]
        th = min(th, cell_h)
        tw = min(tw, cell_w)
        sheet[y0 : y0 + th, x0 : x0 + tw] = thumb[:th, :tw]
    cv2.imwrite(str(out_dir / "ocr_contact_sheet.jpg"), sheet)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    html_rows = "\n".join(
        f"<tr><td><img src='../../../{m['relative_path']}' width='200'/></td>"
        f"<td>{m['image_id']}</td><td>{m['predicted_ocr_text'] or '—'}</td>"
        f"<td><em>fill in CSV</em></td><td>readable / unreadable</td></tr>"
        for m in manifest
    )
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"/><title>OCR review</title></head>
<body><h1>OCR plate review (30 crops)</h1>
<p>Edit <code>ocr_review_annotations.csv</code>: <strong>ground_truth_plate_text</strong> from image only;
<code>include_in_cer=yes</code> when verified. Do not copy predictions into GT.</p>
<table border="1">{html_rows}</table></body></html>"""
    (out_dir / "ocr_review_index.html").write_text(html, encoding="utf-8")
    print(f"Wrote {out_dir} ({len(manifest)} crops)")


if __name__ == "__main__":
    main()
