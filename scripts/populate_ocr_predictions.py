"""Fill predicted_ocr_text column only (never ground truth)."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2

from model.plate_ocr import PlateOCRReader, normalize_plate_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        default="docs/evaluation/ocr/ocr_review_annotations.csv",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--enhanced-crops-dir",
        default=None,
        help=(
            "Optional directory of enhanced crops (same filenames). "
            "Reads enhanced images for OCR but does not change image_path in the CSV."
        ),
    )
    args = parser.parse_args()

    csv_path = ROOT / args.csv
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    fieldnames = rows[0].keys() if rows else []

    reader = PlateOCRReader(gpu=False)
    if not reader.available:
        raise SystemExit(reader.unavailable_reason or "EasyOCR unavailable")

    enhanced_root = (ROOT / args.enhanced_crops_dir).resolve() if args.enhanced_crops_dir else None
    if enhanced_root is not None and not enhanced_root.is_dir():
        raise SystemExit(f"Enhanced crops dir not found: {enhanced_root}")

    filled = 0
    for row in rows:
        if row.get("predicted_ocr_text") and not args.overwrite:
            continue
        path = Path(row["image_path"])
        read_path = path
        if enhanced_root is not None:
            candidate = enhanced_root / path.name
            if candidate.is_file():
                read_path = candidate
        if not read_path.is_file():
            continue
        image = cv2.imread(str(read_path))
        if image is None:
            continue
        result = reader.read_crop(image)
        row["predicted_ocr_text"] = normalize_plate_text(result.normalized_text if result else "")
        filled += 1

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    suffix = f" (OCR from enhanced dir {enhanced_root})" if enhanced_root else ""
    print(f"Updated predicted_ocr_text for {filled} rows in {csv_path}{suffix}")


if __name__ == "__main__":
    main()
