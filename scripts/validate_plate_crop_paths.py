"""Verify OCR review CSV image paths exist."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "docs/evaluation/ocr/ocr_review_annotations.csv"
OUT = ROOT / "docs/evaluation/ocr/ocr_crop_path_validation.json"


def main() -> None:
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    missing = []
    for row in rows:
        path = Path(row["image_path"])
        if not path.is_file():
            missing.append(row["image_id"])
    payload = {
        "row_count": len(rows),
        "missing_image_ids": missing,
        "status": "OK" if not missing else "FAIL",
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
