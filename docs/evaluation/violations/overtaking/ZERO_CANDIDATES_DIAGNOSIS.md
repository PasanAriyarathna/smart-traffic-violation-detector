# Overtaking Zero Candidates — Root Cause Analysis

**Video:** first clip in `datasets/raw_clips/illegal overtaking/` (1440×1080)  
**Config:** `config_overtaking_video_v1.json` (template 55% vertical lane split)

## Verified: detector and tracking are working

| Metric | 120-frame diagnosis |
|--------|---------------------|
| Frames with zero vehicles | 0 |
| Tracked vehicle observations | 313 |
| Unique vehicle track IDs | **3** |

## Root cause 1 — template lane geometry vs camera (confirmed visually)

Diagnostic frames (`diagnosis_20261009/frames/`) show:

- **Travel** = left half, **passing** = right half of the frame.
- Traffic uses the **left** lane (same direction); oncoming traffic occupies the **right** half.
- This is a **following / same-lane** scene, not a completed pass into a prohibited zone.

The rule requires a **temporal** sequence: both vehicles in travel → passing vehicle enters **passing** lane → progress order reverses → prohibited zone hit.  
Short clip + **3 tracks** + no sustained two-vehicle pass sequence → **0 candidates** (expected).

## Root cause 2 — progress direction and road perspective

Default `progress_direction: [0, 1]` assumes forward motion increases normalized **y**. Road perspective and slow dashcam speed (~11 km/h in overlay) may not produce enough **minimum_forward_progress** across paired tracks in 4 s.

## Root cause 3 — not missing detections

Observations in travel lane: **253**; in passing lane: **60** (mostly oncoming lane assignment, not overtaking maneuver). **0** outside lanes (template always assigns a half-plane).

## Manual inputs required

1. Redraw **travel** / **passing** polygons along actual lane markings for this camera.
2. Set **progress_direction** along road travel (may need `[0, -1]` or a skewed vector after calibration).
3. Define **prohibited_passing_zones** where local rules forbid passing (not the entire right half if that is oncoming traffic).
4. Use a clip segment where a pass actually occurs, or label **FN** in a separate ground-truth log.

## Extended frame run (600 frames ≈ 20 s)

| Metric | Value |
|--------|------:|
| Unique vehicle track IDs | 32 |
| Travel-lane observations | 1064 |
| Passing-lane observations | 382 |
| Rule candidates | **0** |

Longer sampling increases tracks but **does not** produce overtaking candidates with the template lane split — confirms missing maneuver + miscalibrated geometry, not absent detections.

Synthetic unit tests (11) remain valid; they do not contradict this real-video outcome.
