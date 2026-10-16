# Red-Light — Prepared for Human-Verified Evaluation

## Working geometry config

**File:** `config_red_light_video_v2_geometry.json` (v1 and diagnostic configs preserved)

| Field | Value | Evidence |
|-------|--------|----------|
| Stop line | y=540, x 120→1180 | `config_calibration/grid_y_frame_0060.jpg` (stop bar band ~530–550) |
| Traffic-light ROI | [0.35,0.06]–[0.68,0.32] | Overhead gantry (approximate) |
| approach_side | **1** | Diagnosis: 1 geometric crossing (vs 0 with −1) |
| signal_states | **unknown** 0–14.5 s | No invented red/amber/green intervals |

## Signal timing (manual — required)

| File | Purpose |
|------|---------|
| `signal_state_review_template.csv` | Scratch notes + video bounds (~0–14.22 s) |
| `signal_state_observations.csv` | Optional frame observations (not merged) |
| `signal_state_intervals_template.csv` | Copy to **`signal_state_intervals.csv`** and fill **interval** rows |

Observations at t≈0 s and t≈2 s are **not** a complete timeline. Evaluation stays **partial** until `signal_state_intervals.csv` has non-overlapping intervals covering the clip (use `unknown` where the signal cannot be seen).

### Validate reviewed intervals (no write)

```powershell
$py = "$env:LOCALAPPDATA\venvs\smart-traffic-yolo\Scripts\python.exe"
cd "D:\Campus\semester 6\Intelligent system\smart-traffic-violation-detector"
& $py scripts/apply_red_light_signal_review.py `
  --review-csv "docs/evaluation/violations/red_light/signal_state_intervals.csv" `
  --video "datasets/raw_clips/red light events/red light.mp4" `
  --validate-only `
  --require-full-coverage
```

### Generate human-reviewed config (after validation passes)

```powershell
& $py scripts/apply_red_light_signal_review.py `
  --base-config "docs/evaluation/violations/red_light/config_red_light_video_v2_geometry.json" `
  --review-csv "docs/evaluation/violations/red_light/signal_state_intervals.csv" `
  --output "docs/evaluation/violations/red_light/config_red_light_video_v2_human_signals.json" `
  --video "datasets/raw_clips/red light events/red light.mp4" `
  --require-full-coverage
```

## Signal investigation (2026-10-09, PotPlayer + ROI contact sheet)

- **Artifacts:** `investigation_20261009/signal_frames/signal_roi_contact_sheet.jpg`, `signal_state_observations.csv`, `investigation_report.md`
- **Finding:** Red countdown **10→1** from 0–9 s; red still lit at **10–11 s**; green arrow ~**12 s**. This **does not match** red ending at **10 s** in `config_red_light_video_v2_user_signal_cycle.json`.
- **Proposed intervals (needs your OK):** `signal_state_intervals_proposed_evidence_20261009.csv` → exploratory run `evidence_proposed_PENDING_20261009/` (1 red-light **candidate** @ 11.788 s, track 130).

## User-provided signal cycle run (2026-10-09)

**Assumption:** Cycle durations supplied for this task (red 10 s, amber 1 s, green 50 s, total 61 s), applied in order and **clipped to video length** (~14.256 s @ 29.18 fps, 416 frames). Intervals are **not** inferred from pixel-level signal recognition in the model.

| Interval | Seconds in config |
|----------|-------------------|
| Red | 0–10 |
| Amber | 10–11 |
| Green | 11–14.256 (truncated; would be 11–61 on a longer clip) |

**Files:** `signal_state_intervals.csv` → `config_red_light_video_v2_user_signal_cycle.json`

```powershell
& $py scripts/apply_red_light_signal_review.py `
  --base-config "docs/evaluation/violations/red_light/config_red_light_video_v2_geometry.json" `
  --review-csv "docs/evaluation/violations/red_light/signal_state_intervals.csv" `
  --output "docs/evaluation/violations/red_light/config_red_light_video_v2_user_signal_cycle.json" `
  --video "datasets/raw_clips/red light events/red light.mp4" `
  --require-full-coverage

& $py model/violation_detector.py `
  --source "datasets/raw_clips/red light events/red light.mp4" `
  --red-light-config "docs/evaluation/violations/red_light/config_red_light_video_v2_user_signal_cycle.json" `
  --output-dir "docs/evaluation/violations/red_light/real_video_runs/user_signal_cycle_20261009"
```

| Run | Red-light candidates | Other |
|-----|---------------------|--------|
| `user_signal_cycle_20261009` / `red light_20261009_185138` | **0** | 1 helmet @ 13.056 s (unrelated rule) |

Prior diagnosis: one geometric stop-line crossing near **~13 s** — under this timeline that falls in the **green** interval, so the red-light rule correctly emits **no** candidates. Summary: `real_video_runs/user_signal_cycle_20261009/run_summary.json`.

## Earlier pipeline run (geometry only, unknown signal)

| Run | Red-light candidates | Other |
|-----|---------------------|--------|
| `human_eval_geometry_v2_20261009` | **0** | 1 helmet (unrelated) |

**Diagnosis (v2, full video):** 1 geometric stop-line crossing; **0** during `unknown` signal → **0** rule candidates.

## Overlays

`diagnosis_v2_final_416/frames/` — stop line at y=540, boxes, traffic-light ROI.

## Export predictions and metrics

```powershell
& $py scripts/export_rule_event_predictions.py `
  --jsonl "docs/evaluation/violations/red_light/real_video_runs/human_eval_geometry_v2_20261009/red light_20261009_183018/events.jsonl" `
  --rule-type "stop_line" `
  --output "docs/evaluation/violations/red_light/human_eval_v2_red_light_predictions.csv"

& $py scripts/validate_rule_ground_truth.py --predictions-csv "docs/evaluation/violations/red_light/human_eval_v2_red_light_predictions.csv"
& $py scripts/compute_rule_event_metrics.py `
  --predictions-csv "docs/evaluation/violations/red_light/human_eval_v2_red_light_predictions.csv" `
  --output "docs/evaluation/violations/red_light/red_light_event_metrics.json"
```

Candidate checklist: `CANDIDATE_REVIEW_CHECKLIST.md`. FN log: `red_light_fn_log_template.csv`.

## Ground truth

- Metrics: **NOT MEASURED** until `ground_truth_label` is TP/FP for reviewed rows

## Technical vs legal

Rule output = **NEEDS_REVIEW** candidate when geometry + **reviewed red** interval align. Not a confirmed violation.
