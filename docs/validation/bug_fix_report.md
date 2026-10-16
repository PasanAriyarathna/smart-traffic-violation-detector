# Bug Fix Report

**Date:** 2026-10-09  
**Branch:** `feature/update-annotated-dataset`

## Issues found and fixed

| Issue | Severity | Fix |
|-------|----------|-----|
| Windows `PermissionError` deleting temp SQLite after API tests | Test infra | `tests/test_api_integration.py`: class-scoped temp DB, `TestClient` context manager, `ignore_cleanup_errors=True` |
| SQLite `events` table missing on first API use | Backend | `backend/app/main.py`: `_connect()` calls `_init_db()` (prior pass) |
| Review export documented wrong `candidate_type` names | Documentation / tooling | `scripts/export_rule_review_sheet.py`: `CANONICAL_CANDIDATE_TYPES` aligned with `model/rules/*.py` |
| No API route to reject a candidate | Missing feature | `POST /events/{event_id}/reject` in `backend/app/main.py` + integration assertion |
| No example overtaking JSON in repo | Config gap | `configs/examples/overtaking_template.json` |
| `build_verified_summary.py` referenced undefined `dirs` | Script bug | Use `latest_detector_experiment()` tuple (prior pass) |

## Not bugs (documented limitations)

- Overtaking rule disabled until full geometry JSON is supplied per video.
- Red-light rule requires manual signal intervals; YOLO `traffic_light` class is not signal-state recognition.
- `verify` sets status `VERIFIED` for workflow/chain gating — not a legal violation confirmation.
- Sepolia logging returns 503 without `.env` credentials (by design).

## Files changed (this audit pass)

- `backend/app/main.py`
- `tests/test_api_integration.py`
- `tests/test_overtaking_rule.py`
- `tests/test_red_light_rule.py`
- `scripts/export_rule_review_sheet.py`
- `configs/examples/overtaking_template.json`
- `scripts/build_evaluation_summary.py`
- `docs/validation/*.md` (reports)

## Verification

```text
python -m pytest tests/ -q
cd blockchain && npm test
```

See `docs/validation/final_validation_report.md` for recorded counts.
