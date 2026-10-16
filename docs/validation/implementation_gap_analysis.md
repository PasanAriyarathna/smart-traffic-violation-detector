# Implementation Gap Analysis

**Date:** 2026-10-09

## Fully implemented and tested

| Feature | Evidence |
|---------|----------|
| YOLOv8 inference + ByteTrack on video | `violation_detector.py`, weights on disk |
| Helmet **candidates** | 48-event run + evidence files |
| Red-light rule (synthetic) | `tests/test_red_light_rule.py` |
| Overtaking rule (synthetic) | `tests/test_overtaking_rule.py` (11 cases) |
| Plate OCR helpers | `tests/test_plate_ocr.py` |
| FastAPI import / verify / reject | `tests/test_api_integration.py` |
| ViolationLogger (local) | Hardhat 2 tests |
| Detector test-split metrics | `detector_val_test_20261009T120646Z` |

## Partially implemented

| Feature | Gap |
|---------|-----|
| Red-light on real video | v2 geometry + multiple runs on `red light.mp4`; track-130 case **NEEDS_REVIEW**; P/R/F1 **NOT MEASURED**; no directional-signal logic |
| Overtaking on real video | `overtaking_template.json` only; no labeled validation |
| OCR end-to-end | EasyOCR optional; no human plate labels |
| Human review metrics | CSV templates exist; labels empty |
| Chain logging | Client code present; Sepolia env not configured |
| Research paper | Markdown/DOCX use verified detector numbers; rule/OCR sections NOT MEASURED |
| End-to-end pipeline | Partial smoke run; chain stage blocked without RPC |

## Missing or blocked

| Feature | Blocker |
|---------|---------|
| YOLOv5 + MySQL baseline | No baseline code/weights |
| Quantitative tracking (HOTA/MOTA) | No GT track annotations |
| Corrected leak-free split + retrain | Manual regrouping + GPU time |
| Production frontend (login, roles) | Not scoped in repo |
| Docker / CI | Not present |
| Public testnet deployment | Credentials / approval |

## Overtaking-specific (priority)

**Status:** Rule module + pipeline hook + unit tests + example config — **complete for logic**.  
**Missing:** Per-camera JSON for project videos, human review of candidates, real-world precision/recall.

See `overtaking_validation_report.md`.
