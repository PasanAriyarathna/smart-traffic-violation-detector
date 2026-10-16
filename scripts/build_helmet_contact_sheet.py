"""Helmet candidate contact sheet for human TP/FP/AMBIGUOUS labeling."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    csv_path = ROOT / "docs/evaluation/violations/helmet_reviewed_annotations.csv"
    out_dir = ROOT / "docs/evaluation/violations/helmet_review_package_20261009"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))

    thumbs = []
    manifest = []
    for row in rows:
        path = Path(row.get("evidence_image") or "")
        if not path.is_file():
            continue
        img = cv2.imread(str(path))
        if img is None:
            continue
        thumb = cv2.resize(img, (280, 160))
        cid = (row.get("candidate_id") or "")[:8]
        cv2.putText(thumb, cid, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        thumbs.append(thumb)
        manifest.append(
            {
                "candidate_id": row.get("candidate_id"),
                "timestamp": row.get("timestamp"),
                "track_id": row.get("track_id"),
                "reviewer_label": row.get("reviewer_label"),
                "evidence_image": str(path),
            }
        )

    cols = 4
    rows_n = math.ceil(len(thumbs) / cols) if thumbs else 1
    sheet = np.full((rows_n * 170, cols * 290, 3), 240, dtype=np.uint8)
    for i, thumb in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet[r * 170 : r * 170 + thumb.shape[0], c * 290 : c * 290 + thumb.shape[1]] = thumb
    cv2.imwrite(str(out_dir / "helmet_contact_sheet.jpg"), sheet)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {out_dir} ({len(manifest)} / {len(rows)} candidates with readable evidence)")


if __name__ == "__main__":
    main()
