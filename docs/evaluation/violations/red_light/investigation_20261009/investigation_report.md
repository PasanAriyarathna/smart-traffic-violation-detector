# Red-light investigation — `red light.mp4` (2026-10-09)

## Video

- Duration: **~14.256 s** (416 frames @ 29.181 fps)
- Artifacts: `signal_frames/` (1 Hz full + ROI crops, `signal_roi_contact_sheet.jpg`)

## Signal observations (visual / contact sheet — not model-inferred)

| Video time (s) | Observable evidence |
|----------------|---------------------|
| 0 | Red lamp on; countdown **10** |
| 1–9 | Countdown decreases **9…1** (~1 s per step) |
| 10 | Red on; countdown **blank** |
| 11 | Red still on; display shows **51** (green digits) |
| 12 | **Green arrow** on; countdown **50** |
| 13–14 | Signal face largely out of frame |

**Phase at t=0:** Strong evidence the clip starts **near the start of a red countdown** (10 at 0 s, linear decay). Not proven to be t=0 of a full 61 s cycle without off-video context.

**Amber:** Not clearly visible at 1 s sampling.

## Config comparison

| Timeline | Red end | Green start | Crossing @ 11.788 s (track 130) |
|----------|---------|-------------|----------------------------------|
| User cycle (`config_red_light_video_v2_user_signal_cycle.json`) | 10 s | 11 s | Classified **green** → **0** red-light rule fires |
| ROI contact sheet | ~12 s | ~12 s | Would be **red** → rule **can** fire (see proposed PENDING run) |

## Stop line / crossing (tracking probe)

- **One** geometric crossing (`approach_side=1`, stop line y=540):
  - **t ≈ 11.788 s**, **track_id 130**, class **motorcycle**
  - Centers: (255.2, 541.4) → (260.4, 535.5) — crosses configured line near stop-bar band (calibration grid 530–550)
- Stop line appears on **stop bar band**, not mid-intersection (see `config_calibration/grid_y_frame_0060.jpg`)

## Proposed intervals (your confirmation required)

File: `signal_state_intervals_proposed_evidence_20261009.csv`  
Config: `config_red_light_video_v2_evidence_proposed_PENDING.json`  
Run: `real_video_runs/evidence_proposed_PENDING_20261009/` — **exploratory only**

## Metrics

**NOT MEASURED** — no human TP/FP ground truth.
