"""Validate OCR review CSV before CER evaluation."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "image_id",
    "image_path",
    "ground_truth_plate_text",
    "include_in_cer",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        default="docs/evaluation/ocr/ocr_review_annotations.csv",
    )
    parser.add_argument(
        "--output",
        default="docs/evaluation/ocr/ocr_annotation_validation.json",
    )
    args = parser.parse_args()

    csv_path = ROOT / args.csv
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    missing_cols = REQUIRED - set(rows[0].keys()) if rows else REQUIRED
    errors: list[str] = []
    cer_eligible = 0
    with_gt = 0

    for index, row in enumerate(rows, start=2):
        path = (row.get("image_path") or "").strip()
        if path and not Path(path).is_file():
            errors.append(f"Line {index}: image not found")
        gt = (row.get("ground_truth_plate_text") or "").strip()
        if gt:
            with_gt += 1
        include = (row.get("include_in_cer") or "").strip().lower()
        if include == "yes":
            if not gt:
                errors.append(f"Line {index}: include_in_cer=yes but ground_truth empty")
            cer_eligible += 1 if gt else 0

    payload = {
        "csv_path": str(csv_path.resolve()),
        "row_count": len(rows),
        "missing_columns": sorted(missing_cols),
        "rows_with_ground_truth": with_gt,
        "cer_evaluation_sample_count": cer_eligible,
        "cer_measurable": cer_eligible > 0,
        "errors": errors,
        "status": "FAIL" if errors or missing_cols else "OK",
    }
    out = ROOT / args.output
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if errors or missing_cols:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
