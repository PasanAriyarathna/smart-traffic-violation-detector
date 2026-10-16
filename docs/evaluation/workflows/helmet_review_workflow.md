# Helmet Candidate Review Workflow

## Files

| Role | Path |
|------|------|
| Annotation CSV | `docs/evaluation/violations/helmet_reviewed_annotations.csv` |
| Guidelines | `docs/evaluation/violations/helmet_annotation_guidelines.md` |
| FN log (recall) | `docs/evaluation/violations/helmet_fn_log_template.csv` |
| Browser helper | `docs/evaluation/review_tools/helmet_review.html` |

## Labels (case-insensitive in metrics script)

- **TP** — plausible review case under the written protocol  
- **FP** — false alarm  
- **Ambiguous** — insufficient evidence  
- **Unreviewed** — default; excluded from precision  

## Steps

1. Validate format and evidence paths:
   ```powershell
   python scripts/validate_helmet_annotations.py
   ```
2. Open the review UI in a browser (file picker required for local images):
   ```powershell
   start "" "D:\Campus\semester 6\Intelligent system\smart-traffic-violation-detector\docs\evaluation\review_tools\helmet_review.html"
   ```
   Click **Choose file** and select `docs\evaluation\violations\helmet_reviewed_annotations.csv`.  
   Review each row (evidence loads via `file:///` paths). Set **TP**, **FP**, or **Ambiguous**.  
   Click **Download updated CSV** and replace `helmet_reviewed_annotations.csv` (or save as new file and point metrics script to it).
3. Re-run validation after edits.
4. Compute metrics (only TP/FP rows count toward precision):
   ```powershell
   python scripts/compute_helmet_metrics.py
   ```
5. Optional recall after full-video FN review:
   ```powershell
   python scripts/compute_helmet_metrics.py --fn-video-count N
   ```

## Current status

Run validation JSON for live counts: `docs/evaluation/violations/helmet_annotation_validation.json`

Metrics are **NOT MEASURED** until at least one row is labeled TP or FP.
