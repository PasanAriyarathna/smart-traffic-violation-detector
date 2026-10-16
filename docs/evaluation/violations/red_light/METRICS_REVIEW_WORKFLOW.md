# Red-Light Metrics Review Workflow

## Current export (for labeling)

**File:** `red_light_predictions_for_review.csv`  
**Source run:** `real_video_runs/evidence_proposed_PENDING_20261009/` (exploratory interval config — not confirmed)

| event_id | Time | Track | Notes |
|----------|------|-------|--------|
| b97bcb91-… | 11.788 s | 130 | See `investigation_20261009/crossing_verification_11_788/` |

## Labeling rules

- `ground_truth_label`: **TP** | **FP** | **AMBIGUOUS** only (uppercase).
- **Do not** label track 130 **TP** without resolving: physical stop bar, green-arrow movement applicability, and signal interval review.
- Default for unresolved case: **AMBIGUOUS**.
- **FN** (missed red-light crossings): separate file `red_light_fn_log_template.csv` — not in prediction CSV.

## Track 130 checklist (before TP/FP)

1. `PHYSICAL_AND_SIGNAL_ASSESSMENT.md`
2. Evidence JPG vs `signal_roi/t_011.788s_f0344.jpg`
3. `signal_state` column reflects **config**, not vision

## Compute metrics

```powershell
python scripts/validate_rule_ground_truth.py --predictions-csv docs/evaluation/violations/red_light/red_light_predictions_for_review.csv
python scripts/compute_rule_event_metrics.py `
  --predictions-csv docs/evaluation/violations/red_light/red_light_predictions_for_review.csv `
  --fn-log-csv docs/evaluation/violations/red_light/red_light_fn_log_template.csv `
  --output docs/evaluation/violations/red_light/red_light_event_metrics.json
```

Precision/recall/F1 require at least one **TP** or **FP** and independent **FN** count for recall.
