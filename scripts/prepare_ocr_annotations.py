"""Create OCR review template from plate crop CSV without inventing ground truth."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "evaluation" / "plates_labeled.csv"
OUTPUT = ROOT / "docs" / "evaluation" / "ocr" / "ocr_review_annotations.csv"


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Missing source CSV: {SOURCE}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "image_id",
        "image_path",
        "predicted_ocr_text",
        "ground_truth_plate_text",
        "readable_status",
        "image_quality",
        "lighting_condition",
        "blur_occlusion",
        "reviewer_decision",
        "exclusion_reason",
        "include_in_cer",
    ]
    out_rows = []
    with SOURCE.open(encoding="utf-8") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            out_rows.append(
                {
                    "image_id": f"plate_{index:03d}",
                    "image_path": row.get("image_path", ""),
                    "predicted_ocr_text": "",
                    "ground_truth_plate_text": "",
                    "readable_status": "unreviewed",
                    "image_quality": "",
                    "lighting_condition": "",
                    "blur_occlusion": "",
                    "reviewer_decision": "",
                    "exclusion_reason": "",
                    "include_in_cer": "no",
                }
            )
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"Wrote {len(out_rows)} template rows to {OUTPUT}")


if __name__ == "__main__":
    main()
