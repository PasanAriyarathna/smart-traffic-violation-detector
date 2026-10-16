# Final Validation Report

**Date:** 2026-10-09  
**Branch:** `feature/update-annotated-dataset` @ `fd8bc5e`

## Automated tests (executed)

| Suite | Command | Result |
|-------|---------|--------|
| Python | `python -m pytest tests/ -q` | **26 passed**, 0 failed, **3 subtests** passed |
| Hardhat | `cd blockchain && npm test` | **2 passed**, 0 failed |

Log: `docs/validation/pytest_full_log.txt`

## Build / Docker / Frontend

| Check | Status |
|-------|--------|
| Separate SPA frontend | **Not present** — HTML dashboard in FastAPI |
| Dockerfile / Compose | **Not present** |
| CI workflows | **Not present** |

## Measured AI metrics (object detection only)

Source: `docs/evaluation/detector/detector_val_test_20261009T120646Z/metrics.json`

| Metric | Value |
|--------|------:|
| Test images | 36 |
| Precision | 0.526 |
| Recall | 0.422 |
| mAP@0.5 | 0.407 |
| mAP@0.5:0.95 | 0.186 |

Helmet rule precision, OCR CER, tracking HOTA/MOTA, red-light/overtaking **video** accuracy: **NOT MEASURED**.

## Evidence-based conclusions

1. Detection pipeline and held-out test metrics are recorded and reproducible.
2. Helmet: 48 candidates verified on disk; human labels pending.
3. Red-light / overtaking: rule logic unit-tested; real-video validation not completed.
4. Backend: import, verify, reject, and chain-not-configured (503) tested.
5. Blockchain: local Hardhat tests only; Sepolia not deployed here.
6. Dataset split overlap documented — qualify generalization claims.

## Cross-check script

`docs/validation/artifact_crosscheck.md` (from `scripts/validate_research_artifacts.py`)

## Machine-readable summary

`docs/validation/evaluation_summary.json`
