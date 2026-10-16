"""Diagnostic: count non-empty EasyOCR reads on original vs enhanced crops (no GT, no CER claims)."""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2

from model.plate_ocr import PlateOCRReader, normalize_plate_text

CSV = ROOT / "docs/evaluation/ocr/ocr_review_annotations.csv"
ENHANCED = ROOT / "docs/evaluation/plate_crops_enhanced"
OUT = ROOT / "docs/evaluation/ocr/ocr_enhanced_vs_original_diagnosis.json"


def _count_reads(reader: PlateOCRReader, rows: list[dict], *, use_enhanced: bool) -> dict:
    nonempty = 0
    samples: list[dict] = []
    for row in rows:
        path = Path(row["image_path"])
        if use_enhanced:
            path = ENHANCED / path.name
        if not path.is_file():
            continue
        img = cv2.imread(str(path))
        if img is None:
            continue
        result = reader.read_crop(img)
        text = normalize_plate_text(result.normalized_text if result else "")
        if text:
            nonempty += 1
            if len(samples) < 5:
                samples.append({"image_id": row["image_id"], "filename": path.name, "text_len": len(text)})
    return {"nonempty_predictions": nonempty, "sample_nonempty": samples}


def main() -> None:
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    reader = PlateOCRReader(gpu=False)
    if not reader.available:
        raise SystemExit(reader.unavailable_reason or "EasyOCR unavailable")

    payload = {
        "note": "Counts only; not OCR accuracy. Ground truth unchanged.",
        "total_rows": len(rows),
        "original_crops": _count_reads(reader, rows, use_enhanced=False),
        "enhanced_crops": _count_reads(reader, rows, use_enhanced=True),
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
