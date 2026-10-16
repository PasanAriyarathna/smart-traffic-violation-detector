# Red-Light Zero Candidates — Root Cause Analysis

**Video:** `datasets/raw_clips/red light events/red light.mp4` (1268×718, 416 frames ≈ 14.3 s)  
**Original run config:** `config_red_light_video_v1.json` (120 frames processed)

## Verified: detector and tracking are working

| Metric | 120-frame run | Full 416-frame diagnosis |
|--------|---------------|---------------------------|
| Frames with zero vehicles | 0 | 0 |
| Sum of tracked vehicle obs. | 288 | (see `diagnosis_20261009_full416/diagnosis.json`) |

## Root cause 1 — signal intervals (confirmed)

`config_red_light_video_v1.json` marks **0.0–120.0 s as `unknown`**. The processed clip is only **~4.1 s** (120 frames) or **~14.3 s** (full video).  
During the entire diagnostic replay, `state_at(t)` was **`unknown` for every frame** → `state_during(...) == "red"` never holds → **no candidates even if geometry fires**.

The configured **red** interval starts at **120 s**, which **does not overlap** the video timeline.

**Proof:** `config_red_light_diagnostic_signal_red_0_20s.json` (diagnostic only, not human-verified timing) with red over 0–20 s on full video:

- Geometric stop-line crossings: **1**
- Crossings during reviewed red: **1**
- Rule candidates emitted: **1**

Original v1 config on full video: geometric crossings **1**, candidates **0**.

## Root cause 2 — stop line / ROI misalignment (visual + diagnostic frames)

Diagnostic frames under `diagnosis_20261009/frames/` show:

- Red **stop_line** sits mid-intersection, not on visible white stop bars.
- Yellow **traffic_light_regions** box is empty (sky); actual signals are outside the ROI.

So even after fixing signal intervals, **human calibration** of stop line and approach_side is required. One geometric crossing was detected with the placeholder line — that event may not match a real violation.

## Manual inputs required

1. Watch `red light.mp4` and record **signal_states** with video timestamps (seconds from start).
2. Adjust **stop_line** pixel endpoints to the finite segment vehicles cross when entering the junction.
3. Set **approach_side** (−1 or 1) from which side of the line the approach occurs.
4. Optionally refine **traffic_light_regions** for documentation (not used for color inference today).

## Rerun command (after editing config)

```powershell
python model/violation_detector.py `
  --source "datasets/raw_clips/red light events/red light.mp4" `
  --red-light-config "docs/evaluation/violations/red_light/config_red_light_video_v1.json" `
  --output-dir "docs/evaluation/violations/red_light/real_video_runs"
```

Do not treat `config_red_light_diagnostic_signal_red_0_20s.json` as validation ground truth.
