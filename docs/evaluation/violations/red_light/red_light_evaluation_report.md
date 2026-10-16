# Red-Light Rule Evaluation Report

## Synthetic unit tests: VERIFIED

`tests/test_red_light_rule.py`

## Real-video run (2026-10-09)

| Field | Value |
|-------|--------|
| Video | `datasets/raw_clips/red light events/red light.mp4` |
| Config | `config_red_light_video_v1.json` (placeholder geometry/signals) |
| Frames | 120 |
| Candidates | **0** |
| Summary | `real_video_run_summary.json` |
| Log | `real_video_runs/detector_run_log.txt` |

**Event-level precision/recall:** NOT MEASURED (no human ground-truth labels; zero exported candidates).

## Next steps

1. Manually review video and edit `config_red_light_video_v1.json` (stop line + signal intervals).
2. Re-run per `validation_workflow.md` (full video or longer `--max-frames`).
3. Label `event_ground_truth_template.csv` / exported predictions.
4. `python scripts/compute_rule_event_metrics.py --predictions-csv ...`
