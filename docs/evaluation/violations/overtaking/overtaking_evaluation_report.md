# Overtaking Rule Evaluation Report

## Synthetic unit tests: VERIFIED (11 cases)

`tests/test_overtaking_rule.py`

## Real-video run (2026-10-09)

| Field | Value |
|-------|--------|
| Video | First clip in `datasets/raw_clips/illegal overtaking/` |
| Config | `config_overtaking_video_v1.json` (template lanes) |
| Frames | 120 |
| Candidates | **0** |
| Summary | `real_video_run_summary.json` |

**Event-level precision/recall:** NOT MEASURED.

## Next steps

Calibrate `config_overtaking_video_v1.json` for the chosen camera, re-run detector, export predictions, complete human ground truth.

See `validation_workflow.md` and `docs/validation/overtaking_validation_report.md`.
