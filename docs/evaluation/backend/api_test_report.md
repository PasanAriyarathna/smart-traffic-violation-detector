# Backend API Integration Test Report

## Command

```text
python -m pytest tests/test_api_integration.py -q
```

## Result: VERIFIED (3 passed, 0 failed; includes reject path in import test)

Date: 2026-10-09

## Coverage

| Test | Behavior |
|------|----------|
| `test_health` | `GET /health` → 200, status ok |
| `test_import_and_verify` | POST import from helmet JSONL, list events, POST verify, POST log-chain → 503 (chain not configured) |
| `test_import_missing_jsonl` | POST invalid path → 404 |

## Environment

- Temporary SQLite via `STVD_DB_PATH`
- `backend/app/main.py` initializes schema on connect

## Machine-readable

`docs/evaluation/backend/api_test_results.json`

## Not tested in this suite

- Production database persistence across process restart
- Frontend dashboard browser integration
- Live Sepolia transaction submission
