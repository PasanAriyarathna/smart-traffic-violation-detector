# Overtaking Camera Calibration Guide

**Video sample:** 1440×1080 dashcam (see `diagnosis_20261009/frames/`)

## Required polygons (normalized 0–1 coordinates)

| Field | Meaning |
|-------|---------|
| `lanes.travel` | Polygon covering the lane(s) where the camera vehicle travels **before** a pass |
| `lanes.passing` | Polygon covering the lane used **during** a pass (may overlap travel at boundaries) |
| `prohibited_passing_zones` | One or more polygons where passing is prohibited by **local rules you document** in `prohibition_basis` |
| `progress_direction` | Unit vector `[dx, dy]` in normalized image coords pointing **forward** along travel |

## How to supply points

1. Open `diagnosis_20261009/frames/frame_0060.jpg` (or the target clip).
2. For each corner of the lane/trapezoid, record `(x/W, y/H)` where `W=1440`, `H=1080`.
3. Minimum 3 points per polygon; list in order around the region.
4. Save as `config_overtaking_<clipname>.json` (do not overwrite template).

## Why 50/50 split failed

Diagnostic frames show **same-direction traffic in the left portion** and **oncoming traffic in the right half**. A vertical 55% split treats oncoming lane as “passing” without a maneuver — no behind→ahead sequence in travel lane.

## Clip selection

Browse `datasets/raw_clips/illegal overtaking/*.mp4`. Pick a segment where one vehicle clearly passes another **in the same direction**. Note filename and start/end seconds for ground truth.

## Ground truth

Use `event_ground_truth_template.csv` with columns matching `export_rule_event_predictions.py` output plus `ground_truth_label` = TP | FP | AMBIGUOUS.
