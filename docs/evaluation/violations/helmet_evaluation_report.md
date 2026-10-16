# Helmet Rule Evaluation Report

## Scope

Evaluation of **review candidates** (`helmet_not_observed_on_associated_rider`), not confirmed legal violations.

## Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| JSONL | `runs/violation_detector/not wearing helmets_20261009_124822/events.jsonl` | 48 events |
| Evidence JPGs | same run `evidence/` | 48/48 present |
| Annotation template | `docs/evaluation/violations/helmet_reviewed_annotations.csv` | 48 rows, all `Unreviewed` |
| FN log template | `docs/evaluation/violations/helmet_fn_log_template.csv` | Empty |
| Verification | `docs/evaluation/violations/helmet_artifact_verification.json` | status verified |

## Metrics (computed)

Source: `docs/evaluation/violations/helmet_metrics.json`

- **Precision:** NOT MEASURED (0 TP, 0 FP labeled)
- **Recall / F1:** NOT MEASURED (no independent FN video review)

## Validation (2026-10-09)

- Format/evidence check: `docs/evaluation/violations/helmet_annotation_validation.json` — **48** rows, **48** Unreviewed, precision **not measurable**.

## Manual action required

See `docs/evaluation/workflows/helmet_review_workflow.md`:

1. `python scripts/validate_helmet_annotations.py`
2. Review via `docs/evaluation/review_tools/helmet_review.html` or Excel
3. `python scripts/compute_helmet_metrics.py` (optional `--fn-video-count N`)
