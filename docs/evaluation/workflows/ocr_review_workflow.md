# OCR Ground-Truth Review Workflow

## Files

| Role | Path |
|------|------|
| Review CSV | `docs/evaluation/ocr/ocr_review_annotations.csv` |
| Plate crops | `docs/evaluation/plate_crops/` |

## Columns

- `ground_truth_plate_text` — human-entered text from the image (never copy from OCR output).
- `readable_status` — `readable` / `unreadable` / `unreviewed`
- `include_in_cer` — `yes` only when GT is verified and crop is readable
- `predicted_ocr_text` — optional; filled manually or via `--run-ocr`

## Steps

1. Validate CSV:
   ```powershell
   python scripts/validate_ocr_annotations.py
   ```
2. Enter ground truth for each readable crop; set `include_in_cer=yes` where appropriate.
3. Generate **predictions only** (never ground truth):
   ```powershell
   pip install -r requirements-ocr.txt
   python scripts/populate_ocr_predictions.py
   ```
   Status file: `docs/evaluation/ocr/ocr_predictions_status.json` (2026-10-09 run: 30 crops processed, 0 non-empty OCR reads).
4. Enter `ground_truth_plate_text` in Excel/CSV; set `include_in_cer=yes` for readable plates.
5. Metrics:
   ```powershell
   python scripts/compute_ocr_review_metrics.py
   ```
   Or re-run OCR at metric time: `python scripts/compute_ocr_review_metrics.py --run-ocr`

Output: `docs/evaluation/ocr/ocr_metrics.json` (sample count, mean CER, exact-match accuracy).

## Privacy

Do not commit raw plate strings to public repos; use hashes in production logs.
