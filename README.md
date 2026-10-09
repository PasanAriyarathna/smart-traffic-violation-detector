# Smart Traffic Violation Detector

Research project exploring computer vision for traffic-scene analysis and
violation detection. It includes video-frame preprocessing, YOLOv8 inference
and tracking, and conservative review-candidate rules. The rules are not
validated as reliable traffic-law decisions.

## Research objectives

- Prepare traffic-video frames for annotation and later object-detection work.
- Investigate detection and tracking as components of a future violation
  analysis pipeline.
- Evaluate any future model with documented, reproducible dataset splits and
  suitable detection metrics.

These are research objectives, not claims that violations are currently
detected reliably.

## Current implementation status

- `preprocessing/frame_extractor.py` samples frames across each input video
  and writes them into per-video output folders.
- `model/violation_detector.py` runs the existing YOLOv8 detection model with
  Ultralytics tracking and ByteTrack on a video, then writes an annotated video
  and structured local review records.
- The helmet rule only produces `NEEDS_REVIEW` candidates from spatially
  associated person/motorcycle detections when no helmet is detected in an
  approximate head region. It does not confirm a helmet violation.
- An opt-in fixed-camera red-light rule is implemented in
  `model/rules/red_light.py`. It only produces `NEEDS_REVIEW` candidates when a
  tracked vehicle crosses a configured stop line during a manually reviewed
  red-signal interval. The model's generic `traffic_light` class does not
  identify red, amber, or green, so this rule is unsupported without that
  external signal-state review and camera configuration.
- An opt-in fixed-camera overtaking rule is implemented in
  `model/rules/overtaking.py`. It requires tracked trajectories through
  configured travel/passing lanes and a manually documented prohibited zone.
  It produces only `NEEDS_REVIEW` candidates; it does not decide legal status.
- Lane-crossing violations are not implemented; detected road markings alone
  are insufficient without calibrated road geometry and vehicle trajectories.
- `model/train_yolvo6.py` is an empty placeholder. Training is not implemented
  by this repository; the existing checkpoint is used for inference.
- `blockchain/violation_logger.sol` is an empty placeholder. Blockchain
  logging is optional and not implemented.
- Dataset source-video provenance has not been established. Do not interpret
  current dataset metrics as reliable video-independent research evaluation.

## Technology

- Python
- OpenCV (`cv2`) for video reading and image writing
- Ultralytics YOLO and PyTorch for model inference and tracking
- The currently inspected local environment uses Python 3.13.1, Ultralytics
  8.4.174, CPU-only PyTorch 2.14.1, and OpenCV 5.0.0.93. These versions are
  not pinned in a dependency manifest.
- Solidity is a planned integration area; the current contract file is empty.

## Repository layout

```text
blockchain/                 Solidity project placeholder
datasets/                   Local datasets (excluded from new Git additions)
model/                       Inference pipeline and review rules
tests/                       Focused rule tests
preprocessing/               Video frame extraction utility
runs/                        Generated experiment outputs (ignored)
requirements.txt             Runtime Python dependencies
README.md                    Project documentation
```

Raw clips, extracted frames, training copies, model weights, and experiment
outputs are ignored for new Git additions. Annotated dataset files are already
tracked in the current repository history; `.gitignore` does not stop Git from
tracking files already in history. Keep separate, backed-up copies of research
data and review tracked dataset artifacts before future publication.

## Environment setup

Use an isolated Python virtual environment. The inspected environment used
Python 3.13.1, Ultralytics 8.4.174, CPU PyTorch 2.14.1, NumPy 2.5.3,
OpenCV 5.0.0, and pytest 9.1.1. These are the observed local versions, not a
tested compatibility matrix.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
```

For GPU inference, install a PyTorch build that matches the target CUDA setup
using the official PyTorch instructions, then install the remaining project
requirements. The inspected environment used CPU inference. Run tests with
`python -m pytest -q`.

## Frame extraction

From the repository root, run:

```powershell
python preprocessing/frame_extractor.py --input <video-folder> --output <frames-folder>
```

The utility accepts `.mp4`, `.avi`, `.mov`, and `.mkv` files, samples up to 30
frames per video by default, and accepts `--num-frames N` to change the sample
count. It creates one output subfolder per input video. Choose an output folder
outside Git-tracked source paths and ensure the destination is appropriate
before running it.

## Inference and tracking

From the repository root, run:

```powershell
$py = "$env:LOCALAPPDATA\venvs\smart-traffic-yolo\Scripts\python.exe"
& $py model\violation_detector.py --source "path\to\traffic_video.mp4"
```

The default model is `runs/detect/runs/traffic_violation/yolov8n_v1/weights/best.pt`.
Pass `--weights` to select another checkpoint. Each run creates a new timestamped
folder under `runs/violation_detector/` containing `annotated.mp4`,
`events.jsonl`, and an `evidence/` folder. Existing output paths are not
overwritten. Options such as `--conf`, `--rule-conf`, `--tracker`, `--cooldown`,
`--association-frames`, `--association-window`, `--association-margin`,
`--association-min-score`, `--output-video`, `--evidence-dir`, and `--records`
can be used to configure a run. `--max-frames` is available for short smoke
tests. Add `--red-light-config path\to\fixed_camera_config.json` or
`--overtaking-config path\to\fixed_camera_overtaking.json` to enable those
optional rules. Candidate visualization uses amber boxes and compact class,
confidence, and tracking-ID labels; label placement attempts to reduce overlap.

The detector requires the existing checkpoint at the documented default path,
or a local checkpoint supplied with `--weights`. Model weights are not a
runtime package dependency. The training placeholder does not provide a
training CLI; no repository-supported training command is currently
available. `datasets/training_copy/data.yaml` is the configured local dataset
YAML, but its dataset and checkpoint must exist locally before training.

Records are review candidates, not confirmed violations. A candidate must be
observed across nearby frames and is deduplicated per person track until the
configured quiet period passes. The `detection_evidence_score` is the lower
confidence of the associated person and motorcycle detections; it measures
detector confidence only, not the probability that a violation occurred.
`association_score` is an uncalibrated spatial heuristic, not a probability.
Ambiguous pairings are skipped and missed detections can still lead to false
review candidates. Detected number-plate regions are blurred in exported
frames; missed plate detections may remain visible. No plate text is read or
recorded.

### Red-light rule configuration

This rule is for a fixed camera and does not automatically recognize signal
colors. Configure the exact source-frame dimensions, each traffic-light region
as normalized `[x1, y1, x2, y2]` coordinates in the range `0..1`, and a stop
line as two `[x, y]` pixel coordinates in that source frame. `approach_side`
must be `-1` or `1`: it is the sign of
`(x2-x1)*(vehicle_y-y1) - (y2-y1)*(vehicle_x-x1)` on the approach side, where
`(x1,y1)` and `(x2,y2)` are the configured stop-line endpoints. The tracked
vehicle center must cross the finite line segment from that side to the other.

`signal_states` must contain manually reviewed time intervals, each with
`start_seconds`, `end_seconds`, and `state` (`red`, `amber`, `green`, or
`unknown`). Intervals use `[start, end)` semantics; gaps are treated as
`unknown`. A crossing is eligible only when one reviewed interval covers the
whole sampled crossing and says `red`. The traffic-light region is drawn for
visual reference; it is not a color classifier or evidence by itself. Review
the raw video to annotate signal intervals, and verify the stop-line position,
approach side, and vehicle trajectory before interpreting any candidate.

Example configuration (replace coordinates and times after reviewing the
specific video; it is not a ready-made mapping for other cameras):

```json
{
  "frame_width": 1920,
  "frame_height": 1080,
  "traffic_light_regions": [[0.82, 0.02, 0.98, 0.24]],
  "stop_line": [[280, 690], [1640, 690]],
  "approach_side": -1,
  "cooldown_seconds": 10,
  "signal_states": [
    {"start_seconds": 12.0, "end_seconds": 18.5, "state": "red"},
    {"start_seconds": 18.5, "end_seconds": 21.0, "state": "amber"},
    {"start_seconds": 21.0, "end_seconds": 36.0, "state": "green"}
  ]
}
```

Use it with `--red-light-config`. The configuration must match the video frame
dimensions. Missing signal intervals leave the rule unsupported for candidate
generation; an uncertain/gap/amber/green state produces no red-light candidate.
When geometry or a movement-specific signal ROI cannot be established, leave
`stop_line` and `approach_side` as `null`, leave `traffic_light_regions` and
`signal_states` empty, and optionally record an `unsupported_reason`. The
program accepts this incomplete configuration, warns that red-light candidate
generation is disabled, and produces no red-light candidates.
The output record remains `NEEDS_REVIEW`, contains the tracked vehicle ID,
timestamp, configured crossing evidence, and blurred evidence image. These
geometric and manually entered states have not been validated for real-world
accuracy.

### Overtaking rule configuration

The detector supplies vehicle classes, boxes, and tracker IDs. Those detections
alone cannot establish overtaking or illegality. This rule uses normalized
`[x, y]` coordinates (`0..1`) for manually drawn fixed-camera polygons and a
`progress_direction` vector `[dx, dy]` whose direction points along increasing
vehicle progress in the image. Configure `lanes.travel` and `lanes.passing` for
the two same-direction lanes, plus `prohibited_passing_zones` for the image
areas where a passing maneuver is prohibited under a rule basis you have
verified. Include a specific `prohibition_basis` description; the software
does not supply or validate local traffic law.

The rule requires the same tracked vehicle to start behind another vehicle in
the travel lane, enter the passing lane, move ahead while the other vehicle
remains in the travel lane, and return to the travel lane. Both tracks must
show forward progress, sufficient observations, and a configured prohibited
zone must contain a point on the passing vehicle's path during the maneuver.
Pair history is tied to the original tracking IDs; the software does not join
tracks across an ID change. Each ordered track pair is recorded at most once in
a run. A candidate is only a possible maneuver for review and has
`legal_status: not_determined`.

Use `--overtaking-config path\to\fixed_camera_overtaking.json`. The required
top-level fields are `frame_width`, `frame_height`, `lanes`,
`progress_direction`, `prohibited_passing_zones`, and `prohibition_basis`.
Optional thresholds include `minimum_observations`,
`minimum_duration_seconds`, `minimum_order_gap`, `minimum_forward_progress`,
`maximum_track_gap_seconds`, and `maximum_maneuver_seconds`. Frame dimensions
must exactly match the input video.
If lane geometry, direction, a prohibited zone, or the rule basis is
unavailable, leave it unset; the config is accepted as unsupported and no
overtaking candidates are generated.

Do not derive lane polygons or prohibited zones from a generic model class.
Choose the actual road boundaries and direction by reviewing the fixed-camera
view and applicable local rule. The progress vector is an image-space
approximation, not a calibrated ground-plane transform. Perspective, occlusion,
detector misses, ByteTrack ID switches, traffic congestion, and ambiguous lane
changes can all cause missed or incorrect maneuver candidates. Review each
event against the original video.

Focused rule tests can be run with:

```powershell
$py = "$env:LOCALAPPDATA\venvs\smart-traffic-yolo\Scripts\python.exe"
& $py -m unittest tests.test_overtaking_rule -v
```

## Dataset, weights, and evaluation

The local training copy contains 253 train, 72 validation, and 36 test images
with corresponding labels, and `data.yaml` declares 13 classes. Dataset files
and model weights are excluded from GitHub; keep authorized copies and backups
outside version control. Verify their integrity and licenses before use.

The saved training run contains per-epoch validation metrics, but no independent
test report was verified during implementation. Source-video provenance for the
annotated images remains unresolved, so it is not established that the current
splits are video-independent. Before making generalization claims, verify
labels and split assignments and report per-class precision, recall, and mAP on
a documented held-out evaluation set.

## Limitations and next work

- Validate the inference and tracking pipeline on varied, authorized videos.
- Validate spatial association and temporal filtering across camera angles,
  occlusions, and crowded scenes; improve helmet status assessment with
  suitable annotated data and independent review.
- Validate configured red-light crossing candidates against manually reviewed
  signal states and vehicle trajectories on suitable fixed-camera videos.
- Validate the configured overtaking trajectory heuristic against manually
  labeled videos before making traffic-law or accuracy claims.
- Add lane-rule logic only after road geometry, camera perspective, and vehicle
  trajectories can be estimated and validated.
- Resolve dataset provenance and establish video-independent train/validation/
  test splits before evaluating generalization.
- Pin dependencies and record model/data versions for reproducible runs.
- Report reproducible per-class metrics and limitations before claiming
  operational violation detection.
- Implement and test any planned blockchain integration before describing it
  as a functioning feature.
