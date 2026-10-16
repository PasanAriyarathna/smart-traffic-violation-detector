# Event-Level Ground Truth Labeling

## Prediction CSV columns (from `export_rule_event_predictions.py`)

- `event_id`, `video_filename`, `video_timestamp`, `candidate_type`
- `tracking_id`, `other_vehicle_tracking_id`, `detection_evidence_score`, `evidence_image`
- **`ground_truth_label`** — fill by human reviewer
- `reviewer_notes`

## Label values (must match `compute_rule_event_metrics.py`)

| Label | Meaning |
|-------|---------|
| **TP** | Valid review candidate under your protocol (not a confirmed legal violation) |
| **FP** | False alarm / wrong geometry / wrong vehicle |
| **AMBIGUOUS** | Insufficient evidence |
| *(empty)* | Excluded from precision |

## False negatives (recall)

FN are **not** rows in the prediction CSV. Record missed events in `red_light/red_light_fn_log_template.csv` (or overtaking equivalent) with video time and description:

```powershell
python scripts/validate_rule_ground_truth.py --predictions-csv path.csv
python scripts/compute_rule_event_metrics.py --predictions-csv path.csv --fn-log-csv path_fn.csv
```

Or pass `--fn-count N` after you count reviewed FN rows manually.

## Metrics

- **Precision** = TP / (TP + FP) only when both exist.
- **Recall** = TP / (TP + FN) only when FN comes from independent review.
- Candidate count ≠ accuracy.
