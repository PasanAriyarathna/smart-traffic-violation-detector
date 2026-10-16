# Overtaking Rule — Video Validation Workflow

See also: `docs/validation/overtaking_validation_report.md`

## Prerequisites

- Template: `configs/examples/overtaking_template.json`
- Document `prohibition_basis` and lane polygons for the fixed camera.

## Run detector

```powershell
$py = "$env:LOCALAPPDATA\venvs\smart-traffic-yolo\Scripts\python.exe"
& $py model/violation_detector.py `
  --source "PATH\to\video.mp4" `
  --overtaking-config "configs\examples\overtaking_template.json" `
  --output-dir "runs\violation_detector" `
  --max-frames 300
```

Config frame size must match video dimensions or the rule is skipped with a warning.

## Export and label

```powershell
python scripts/export_rule_event_predictions.py `
  --jsonl "runs\violation_detector\YOUR_RUN\events.jsonl" `
  --rule-type "possible_overtaking"
```

Candidate type emitted: `possible_overtaking_in_configured_prohibited_zone` (`legal_status`: not determined).

## Metrics

```powershell
python scripts/compute_rule_event_metrics.py `
  --predictions-csv "runs\violation_detector\YOUR_RUN\events_predictions.csv" `
  --output "docs/evaluation/violations/overtaking/rule_event_metrics.json"
```

## Unit-test evidence

Synthetic logic: `python -m pytest tests/test_overtaking_rule.py -q` (11 tests).

Real-video event precision: **NOT MEASURED** until ground-truth labels are filled.
