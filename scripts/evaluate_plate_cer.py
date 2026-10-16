"""Compute mean CER from a CSV of image paths and ground-truth plate text.

CSV columns: image_path,ground_truth_plate
Requires easyocr (see requirements-ocr.txt).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2

from model.plate_ocr import PlateOCRReader, character_error_rate


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate plate OCR CER on labeled crops or full frames.")
    parser.add_argument("--csv", required=True, help="CSV with image_path,ground_truth_plate")
    parser.add_argument("--output", default="docs/research_paper/ocr_cer_results.json")
    args = parser.parse_args()

    reader = PlateOCRReader(gpu=False)
    if not reader.available:
        raise SystemExit(reader.unavailable_reason or "OCR unavailable")

    scores: list[float] = []
    rows_out: list[dict[str, str | float]] = []
    with Path(args.csv).open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            image_path = Path(row["image_path"])
            reference = row["ground_truth_plate"]
            image = cv2.imread(str(image_path))
            if image is None:
                continue
            result = reader.read_crop(image)
            hypothesis = result.normalized_text if result else ""
            cer = character_error_rate(reference, hypothesis)
            scores.append(cer)
            rows_out.append(
                {
                    "image_path": str(image_path),
                    "ground_truth": reference,
                    "hypothesis": hypothesis,
                    "cer": round(cer, 4),
                }
            )

    if not scores:
        raise SystemExit("No valid rows evaluated.")

    mean_cer = sum(scores) / len(scores)
    payload = {
        "samples": len(scores),
        "mean_cer": round(mean_cer, 4),
        "rows": rows_out,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(__import__("json").dumps(payload, indent=2), encoding="utf-8")
    print(f"Mean CER: {mean_cer:.4f} over {len(scores)} samples -> {output}")


if __name__ == "__main__":
    main()
