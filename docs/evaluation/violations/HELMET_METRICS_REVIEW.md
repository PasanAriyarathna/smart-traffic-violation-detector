# Helmet metrics — human review required

**Candidates:** 48 (`helmet_reviewed_annotations.csv`)  
**Current labels:** all `reviewer_label=Unreviewed` — **not ground truth**

## Review tools

| Tool | Path |
|------|------|
| Interactive CSV | `docs/evaluation/review_tools/helmet_review.html` |
| Contact sheet | `helmet_review_package_20261009/helmet_contact_sheet.jpg` |
| Workflow | `docs/evaluation/workflows/helmet_review_workflow.md` |

## Label values

- **TP** / **FP** / **AMBIGUOUS** / **Unreviewed** (Unreviewed excluded from metrics)

## Compute (after labels)

```powershell
python scripts/validate_helmet_annotations.py
python scripts/compute_rule_event_metrics.py --predictions-csv docs/evaluation/violations/helmet_event_predictions.csv
```

**Status:** NOT MEASURED until human TP/FP labels exist.
