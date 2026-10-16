# Overtaking — Prepared for Human-Verified Evaluation

## Clip inventory

- **54** clips under `datasets/raw_clips/illegal overtaking/`
- No clip is pre-selected as a verified illegal-overtaking example.

## Contact sheet (manual clip choice)

```powershell
$py = "$env:LOCALAPPDATA\venvs\smart-traffic-yolo\Scripts\python.exe"
& $py scripts/build_overtaking_clip_contact_sheet.py
```

Output: `clip_contact_sheet.jpg` + `clip_contact_sheet.txt` (filenames in sheet order).

Pick a clip where **same-direction** passing is visible; note filename for config naming.

## Polygon configuration

1. Read `OVERTAKING_POLYGON_GUIDE.md`.
2. Copy `config_overtaking_annotation_template_1440x1080.json` to  
   `config_overtaking_<your_clip>.json` (do not overwrite template).
3. Draw **travel**, **passing**, **prohibited_passing_zones**, and **progress_direction** from the actual frame — do not use a 50/50 vertical split unless it matches the road layout.
4. Validate before running detection:

```powershell
& $py scripts/validate_overtaking_config.py `
  --config "docs/evaluation/violations/overtaking/config_overtaking_<your_clip>.json" `
  --probe-video "datasets/raw_clips/illegal overtaking/<your_clip>.mp4"
```

## Detector run (only after valid config + chosen clip)

```powershell
& $py model/violation_detector.py `
  --source "datasets/raw_clips/illegal overtaking/<your_clip>.mp4" `
  --overtaking-config "docs/evaluation/violations/overtaking/config_overtaking_<your_clip>.json" `
  --output-dir "docs/evaluation/violations/overtaking/real_video_runs/<run_id>"
```

## Metrics

**NOT MEASURED** until predictions are exported and `ground_truth_label` (TP/FP/AMBIGUOUS) is filled per `../GROUND_TRUTH_LABELING.md`.

Passing another vehicle ≠ confirmed illegal overtaking without human legal/geometry review.
