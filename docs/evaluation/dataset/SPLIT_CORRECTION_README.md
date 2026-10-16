# Dataset Split Leakage and Corrected Manifest

## Audits (original data unchanged)

| File | Purpose |
|------|---------|
| `split_independence_audit.json` | Stem-key overlap (filename heuristic) |
| `split_leakage_audit.json` | SHA-256, dHash near-duplicates, stem groups across splits |
| `corrected_split_manifest_v1.json` | Recommended split per file (group by stem) |

## Findings (2026-10-09 run, 361 images)

- **Exact SHA-256 duplicates across splits:** 0
- **Stem groups appearing in more than one split:** many (Roboflow augmentations of same `frame_XXXX`)
- **Recommended moves if manifest applied:** 108 files would change split (see manifest)

## Applying the manifest (manual)

Do **not** overwrite `datasets/training_copy/`. Copy to a new folder, e.g. `datasets/training_copy_v1/`, and move files according to `recommended_split` in the manifest. Re-run detector evaluation on the new test split before updating paper numbers.

## Command

```powershell
python scripts/audit_dataset_leakage.py
```

No automatic retraining is performed by this script.
