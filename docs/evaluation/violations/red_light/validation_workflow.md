# Red-Light Rule — Video Validation Workflow

## Prerequisites

- Example config: `configs/examples/red_light_template.json`
- Adjust `frame_width`, `frame_height`, `stop_line`, `approach_side`, and **manually reviewed** `signal_states` after watching the video (`scripts/probe_video_geometry.py`).

## Run detector (actual CLI flags)

From repository root:

```powershell
$py = "$env:LOCALAPPDATA\venvs\smart-traffic-yolo\Scripts\python.exe"
& $py model/violation_detector.py `
  --source "PATH\to\video.mp4" `
  --red-light-config "configs\examples\red_light_template.json" `
  --output-dir "runs\violation_detector" `
  --max-frames 300
```

Optional flags: `--weights`, `--conf`, `--rule-conf`, `--tracker`, `--cooldown`, `--association-frames`, `--enable-plate-ocr`.

## Export predictions for review

```powershell
python scripts/export_rule_event_predictions.py `
  --jsonl "runs\violation_detector\YOUR_RUN\events.jsonl" `
  --rule-type "vehicle_crossed_configured_stop_line"
```

Fill `ground_truth_label` with **TP** / **FP** / **AMBIGUOUS** after reviewing evidence and video.

## Metrics

```powershell
python scripts/compute_rule_event_metrics.py `
  --predictions-csv "runs\violation_detector\YOUR_RUN\events_predictions.csv" `
  --output "docs/evaluation/violations/red_light/rule_event_metrics.json" `
  --fn-count N
```

Precision/recall are reported only when sufficient labeled rows exist.

## Status

Real-video validation: **pending** (no committed per-video config or labeled predictions CSV).
