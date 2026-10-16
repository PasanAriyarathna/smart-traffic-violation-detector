# Repository Audit

**Date:** 2026-10-09 (full audit pass)  
**Branch:** `feature/update-annotated-dataset`  
**Commit:** `fd8bc5e0da0788a34ba4ecd8874f1c612ea9188c`

## Architecture map

```text
preprocessing/frame_extractor.py     → frame sampling for annotation
model/train_yolvo6.py                → YOLOv8 train/val (Ultralytics)
model/evaluate_yolo.py               → standalone eval helper
model/violation_detector.py          → video: detect + ByteTrack + rules + JSONL
model/rules/red_light.py             → opt-in red-interval + stop-line candidates
model/rules/overtaking.py            → opt-in trajectory + zone candidates
model/plate_ocr.py                   → optional EasyOCR + CER helpers
backend/app/main.py                  → FastAPI + SQLite + HTML dashboard
services/chain_client.py             → Sepolia logging (env-gated)
blockchain/contracts/ViolationLogger.sol + Hardhat tests
scripts/*                            → evaluation, exports, audits
tests/*                              → rules, OCR, API integration
docs/evaluation/*                    → experiment artifacts
docs/validation/*                    → audits and validation reports
```

## Git working tree (preserved)

- Modified tracked: `README.md`, `model/violation_detector.py`, `model/train_yolvo6.py`
- Deleted tracked: `blockchain/violation_logger.sol` (superseded by Hardhat layout)
- Large untracked tree: `backend/`, `blockchain/`, `docs/`, `scripts/`, `services/`, `tests/test_api_integration.py`, etc.

## Component verification

| Component | Evidence | Status |
|-----------|----------|--------|
| YOLO weights | `runs/detect/runs/traffic_violation/yolov8n_v1/weights/best.pt` | Present |
| Detector test eval | `docs/evaluation/detector/detector_val_test_20261009T120646Z/` | **Run verified** |
| ByteTrack in pipeline | `violation_detector.py` tracker args | Integrated (qualitative) |
| Helmet rule | JSONL 48 events + evidence JPGs | **Artifacts verified** |
| Red-light rule | Unit tests | **Logic verified**; video config incomplete |
| Overtaking rule | 11 unit tests + template JSON | **Logic verified**; no real-video run |
| OCR | 30 crops, empty GT | Pipeline optional; **CER not measured** |
| FastAPI | pytest integration | **Working** |
| Blockchain | npm test 2/2 | **Local logic verified** |
| Frontend SPA | — | **Not in repo** (server-rendered HTML only) |
| Docker / CI | — | **Missing** |

## Security notes

- `.env.example` documents chain vars; no secrets committed in audit.
- Chain logging stores hashes, not raw plates (see contract + `chain_client`).
- No authentication on review API (prototype scope).

## Documentation cross-check

- README states conservative `NEEDS_REVIEW` semantics — **consistent** with code.
- Older IEEE JSON metrics may **differ** from 2026-10-09 detector re-run — use timestamped experiment dir.
- Export script now documents canonical `candidate_type` strings matching rule modules.

## Related reports

- `implementation_gap_analysis.md`
- `bug_fix_report.md`
- `overtaking_validation_report.md`
- `final_validation_report.md`
