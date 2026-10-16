# Frame-by-frame verification — track 130 @ ~11.788 s

## Evidence alignment (detector event)

| Field | Value |
|-------|--------|
| Event JSONL time | **11.788 s** |
| Recomputed frame | **344** @ 29.181 fps → **11.7885 s** |
| Saved detector evidence | `real_video_runs/evidence_proposed_PENDING_20261009/.../b97bcb91-4bbd-4891-89d6-dd870fa04e7f.jpg` |
| Verification frame | `annotated_frames/t_011.788s_f0344.jpg` |

**Verdict:** Event timestamp matches **frame 344** (same frame the detector annotates when the rule fires).

## Geometric crossing (track 130, `approach_side=1`, stop line y=540)

Reference point: **bbox center** (same as `RedLightRule`).

| Frame | t (s) | center (x, y) | signed_side | on approach side? |
|-------|-------|---------------|-------------|-------------------|
| 343 | 11.754 | (255.2, **541.4**) | +1472 | yes |
| 344 | 11.788 | (260.4, **535.5**) | −4783 | no (past line) |

**Rule `_crosses_segment`:** fires on frame **344** (prev @ 343 → current @ 344). Center moves from **y > 540** to **y < 540** along approach side 1.

**Caveats (human review):**

- Track **130** is **missing** on many frames in 10.5–11.6 s; reappears @ 11.686, gap @ 11.72, then 343–347. Crossing uses **one-step** prev→current only.
- Low confidence on frames 341–343 (0.32–0.35); 344 = 0.62.
- Motorcycle is **left edge of frame**; center may not match wheel path over the physical stop bar.

**Geometric crossing assessment:** **Plausible one-frame rule crossing** at **11.788 s**, not independently verified as a wheel crossing the painted bar.

## Signal state at crossing (visual — not config JSON)

ROI crops: `signal_roi/t_*.jpg`

| t (s) | Circular red | Green arrow | Countdown |
|-------|--------------|-------------|-----------|
| ~11.0 | Red lit (see 1 Hz sheet) | — | — |
| 11.617–11.686 | Transition region | — | confirm in ROI files |
| **11.754** | **Not seen lit** | **Green arrow ON** | **50** (green digits) |
| **11.788** (crossing) | **Not seen lit** | **Green arrow ON** | **50** |

**Assessment:** At the **exact crossing frame**, the overhead signal in ROI shows a **green directional arrow** and **50** countdown — **not** a lit **red ball**. A green arrow does **not** by itself prove this movement is legally permitted for track 130’s path, but it **does** mean we **cannot** treat the crossing as visually on **red** at that instant.

The PENDING config labels `signal_state=red` because interval CSV says red until 12 s — that is **config**, not vision.

## Candidate disposition (per review criteria)

| Criterion | Result |
|-----------|--------|
| Geometric crossing | **Partially supported** (rule math on track 130 @ 344) |
| Visually red at exact time | **Not established** (green arrow @ 11.754–11.788) |
| Retain as confirmed red-light violation | **No** |
| Existing JSONL in `evidence_proposed_PENDING_*` | **Exploratory only** — needs human relabel or interval correction **before** any metric |

**No signal interval files were changed in this step.**

## Artifacts

- 58 annotated frames: `annotated_frames/` (10.5–12.5 s, every video frame)
- Signal ROI per frame: `signal_roi/`
- Contact sheet: `crossing_window_contact_sheet.jpg`
- Machine log: `crossing_verification.json`

## Next validation steps (commands)

Re-run window after you adjust intervals (new filename only):

```powershell
$py = "$env:LOCALAPPDATA\venvs\smart-traffic-yolo\Scripts\python.exe"
cd "D:\Campus\semester 6\Intelligent system\smart-traffic-violation-detector"

# 1) Re-verify geometry (no config write)
& $py scripts/verify_red_light_crossing_window.py `
  --source "datasets/raw_clips/red light events/red light.mp4" `
  --config "docs/evaluation/violations/red_light/config_red_light_video_v2_geometry.json" `
  --track-id 130 --t-start 10.5 --t-end 12.5 --event-t 11.788 `
  --output-dir "docs/evaluation/violations/red_light/investigation_20261009/crossing_verification_11_788_geometry_only"

# 2) After YOU confirm intervals in CSV → merge new config → new run dir
& $py scripts/apply_red_light_signal_review.py --validate-only `
  --review-csv "docs/evaluation/violations/red_light/signal_state_intervals.csv" `
  --video "datasets/raw_clips/red light events/red light.mp4" --require-full-coverage
```

Manual: open `crossing_window_contact_sheet.jpg`, `t_011.754s_f0343.jpg`, `t_011.788s_f0344.jpg`, and compare to `b97bcb91-...jpg`.
