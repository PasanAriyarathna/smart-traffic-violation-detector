"""Compute OCR CER and exact-match from ocr_review_annotations.csv (human GT only)."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from model.plate_ocr import PlateOCRReader, character_error_rate, normalize_plate_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        default="docs/evaluation/ocr/ocr_review_annotations.csv",
    )
    parser.add_argument(
        "--output",
        default="docs/evaluation/ocr/ocr_metrics.json",
    )
    parser.add_argument(
        "--run-ocr",
        action="store_true",
        help="Run EasyOCR on crops when predicted_ocr_text is empty",
    )
    args = parser.parse_args()

    csv_path = ROOT / args.csv
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    reader = PlateOCRReader(gpu=False) if args.run_ocr else None
    if args.run_ocr and (reader is None or not reader.available):
        raise SystemExit(
            reader.unavailable_reason if reader else "OCR reader unavailable — install requirements-ocr.txt"
        )

    evaluated: list[dict] = []
    import cv2

    for row in rows:
        if (row.get("include_in_cer") or "").strip().lower() != "yes":
            continue
        reference = normalize_plate_text(row.get("ground_truth_plate_text") or "")
        if not reference:
            continue
        hypothesis = normalize_plate_text(row.get("predicted_ocr_text") or "")
        if not hypothesis and args.run_ocr and reader:
            image = cv2.imread(row["image_path"])
            if image is not None:
                result = reader.read_crop(image)
                hypothesis = normalize_plate_text(result.normalized_text if result else "")
        if not hypothesis and not args.run_ocr:
            continue
        cer = character_error_rate(reference, hypothesis)
        evaluated.append(
            {
                "image_id": row.get("image_id"),
                "cer": round(cer, 4),
                "exact_match": int(reference == hypothesis),
            }
        )

    if not evaluated:
        payload = {
            "evaluation_sample_count": 0,
            "mean_cer": None,
            "exact_match_accuracy": None,
            "status": "NOT_MEASURED",
            "note": "No rows with include_in_cer=yes and valid ground_truth (and hypothesis if not --run-ocr).",
        }
    else:
        mean_cer = sum(item["cer"] for item in evaluated) / len(evaluated)
        exact = sum(item["exact_match"] for item in evaluated) / len(evaluated)
        payload = {
            "evaluation_sample_count": len(evaluated),
            "mean_cer": round(mean_cer, 4),
            "exact_match_accuracy": round(exact, 4),
            "status": "VERIFIED",
            "rows": evaluated,
        }

    out = ROOT / args.output
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
