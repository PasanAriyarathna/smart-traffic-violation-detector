# OCR Evaluation Report

## Status: NOT MEASURED

- **30** template rows; **0** ground-truth strings; **0** CER samples (`ocr_metrics.json`).
- Validation: `docs/evaluation/ocr/ocr_annotation_validation.json`
- Workflow: `docs/evaluation/workflows/ocr_review_workflow.md`

## Artifacts

- Source crops CSV: `docs/evaluation/plates_labeled.csv` (30 rows, empty `ground_truth_plate`)
- Review template: `docs/evaluation/ocr/ocr_review_annotations.csv` (30 rows, `include_in_cer=no`)

## Pipeline tests

- CER helper unit tests pass via `tests/test_plate_ocr.py`.
- EasyOCR executed 2026-10-09 (`ocr_predictions_status.json`): 30 crops, **0** non-empty predictions; still **0** ground-truth strings → CER **NOT MEASURED**.

## Next steps

1. Fill `ground_truth_plate_text` for readable crops only.
2. Set `include_in_cer=yes` where appropriate.
3. Install `requirements-ocr.txt` and run `scripts/evaluate_plate_cer.py` after labels exist.

Privacy: do not publish raw plate strings in public appendices.
