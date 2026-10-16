# Physical crossing & signal/movement assessment — track 130

**Status:** Event remains **NEEDS_REVIEW** / **unconfirmed** red-light violation.

## 1. Physical stop bar vs cyan line vs bbox center

**Configured line:** y = **540 px** (cyan overlay in `annotated_frames/`).

**Track 130 geometry** (`track130_stop_bar_geometry.json`, bbox from same tracker run):

| t (s) | Frame | center_y | foot_y (bbox bottom) | center − 540 | foot − 540 |
|-------|-------|----------|----------------------|--------------|------------|
| 11.686 | 341 | 544.7 | 597.8 | +4.7 | +57.8 |
| 11.754 | 343 | 541.4 | 594.8 | +1.4 | +54.8 |
| **11.788** | **344** | **535.5** | **588.7** | **−4.5** | **+48.7** |
| 11.823 | 345 | 535.8 | 588.3 | −4.2 | +48.3 |

**Interpretation (image + geometry):**

- The **rule** uses **bbox center**; center crosses y=540 between frames 343→344 (+1.4 → −4.5 px).
- **BBox foot (bottom)** stays **~49–58 px below** the cyan line (larger y) on all sampled frames — i.e. the detector box’s lowest point does **not** cross the configured line in this window.
- Full frames (`t_011.686s_f0341.jpg`, `t_011.754s_f0343.jpg`): the **white painted stop bar** is **ahead** of the motorcycle; the cyan line is **near** the bar but the bike’s **rear** is still short of the intersection proper. **Physical wheel crossing of the painted bar is not established** from these frames; only a **center-point vs virtual line** crossing is.

**Physical crossing assessment:** **Uncertain / not confirmed** for the painted stop bar; **one-frame center vs configured line** only.

## 2. Red ball → green arrow (11.0–11.8 s, ROI crops)

No amber phase observed in saved ROI frames. Bracketing:

| t (s) | Frame | Visible in ROI |
|-------|-------|----------------|
| 11.000 | 321 | **Red ball ON**; countdown **51** (green digits) |
| 11.206 | 327 | **Red ball ON**; countdown **51** |
| 11.343 | 331 | **Green arrow ON** (straight); countdown **51**; red ball **off** |
| 11.412–11.754 | 333–343 | **Green arrow ON**; countdown **50** |
| 11.788 | 344 | **Green arrow ON**; countdown **50** |

**Transition window (visual):** red ball → green arrow between **~11.21 s and ~11.34 s** (between frames 327 and 331). **Amber:** not visible — **not recorded**.

This **contradicts** `config_red_light_video_v2_evidence_proposed_PENDING.json` (red until 12 s) and the nominal **0–10 s red** user cycle for this segment of video.

## 3. Green arrow vs motorcycle movement

- Motorcycle (id 130) is on the **left** edge, moving **forward into the scene** (toward the intersection / bus ahead).
- Overhead **green arrow** points **straight/up** in ROI.
- **Cannot determine from video alone:** lane assignment, whether this arrow applies to the motorcycle’s lane vs a different approach, filter lanes, or simultaneous red for other movements.

**Movement / signal coupling:** **Requires human review** (PotPlayer + lane context + local rules).

## 4. Code findings (`model/rules/red_light.py`)

- Module docstring: signal from **manual intervals**; does **not** infer from `traffic_light` detector class.
- `signal_states` values: `red` | `amber` | `green` | `unknown` only — **no** aspect type (ball vs arrow).
- `RedLightRule.update`: candidate iff `state_during(...) == "red"` (string match on reviewed interval) **and** geometry crossing.
- `traffic_light_regions`: used for **draw/ROI only** in detector overlay — **not** read by the rule.
- **Conclusion:** The implementation does **not** distinguish red circular vs green directional arrow. It cannot evaluate directional signals reliably.

## 5. Event disposition

| Item | Result |
|------|--------|
| JSONL candidate (PENDING run) | Keep **NEEDS_REVIEW**; **not** confirmed violation |
| Verified red-light violation | **No** |
| Metrics / ground truth | **Not created** |

Design follow-up: `../DIRECTIONAL_SIGNAL_DESIGN_PROPOSAL.md` (documentation only; no rule change in this step).

## 6. Manual decisions still required

1. Does the motorcycle **physically** cross the **painted** stop bar (video), vs center/line artifact?
2. Confirm **signal transition** time between `signal_roi/t_011.206s_f0327.jpg` and `t_011.343s_f0331.jpg`.
3. Does **straight green arrow** govern **this** motorcycle’s movement?
4. If updating intervals, use **new** CSV/config filenames; do not overwrite PENDING artifacts until approved.

## 7. Key files

- Frames: `crossing_verification_11_788/annotated_frames/t_011.754s_f0343.jpg`, `t_011.788s_f0344.jpg`
- ROI transition: `signal_roi/t_011.206s_f0327.jpg`, `t_011.343s_f0331.jpg`
- Detector evidence: `real_video_runs/evidence_proposed_PENDING_20261009/.../b97bcb91-4bbd-4891-89d6-dd870fa04e7f.jpg`
- Geometry log: `track130_stop_bar_geometry.json`
