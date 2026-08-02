# Smart Traffic Violation Detection System

**Module:** IT41043 — Intelligent Systems
**Institution:** Faculty of Information Technology, Horizon Campus
**Academic Year:** 2026 | Third Year, Second Semester
**Milestone:** Milestone 2 — Methodology and Data Description

## 1. Project Overview

This project aims to build an intelligent computer vision system capable of automatically
detecting common traffic violations from dashcam footage. The system identifies and
flags the following violation types:

- Red light violations
- Illegal parking
- Riding/driving without a helmet
- Illegal overtaking
- Illegal U-turns

In addition to violation detection, the system localizes **vehicle number plates**, laying
the groundwork for a future violation-logging pipeline (see `blockchain/` for the planned
tamper-proof logging component).

## 2. Dataset Description

### 2.1 Source and Collection

- **Source:** Dashcam video clips sourced from public Facebook groups sharing road
  footage from Sri Lankan roads.
- **Volume:** 103 raw video clips collected (average duration ~32.5 seconds, ranging
  from ~4 seconds to ~4 minutes).
- **Collection method:** Clips were manually downloaded and stored, then processed using
  a custom Python frame-extraction script (`preprocessing/frame_extractor.py`).

### 2.2 Frame Extraction & Class Distribution

- Frames were extracted using an **evenly-spaced sampling strategy** — each video
  contributes a fixed number of frames (30) spread proportionally across its full
  duration, rather than a fixed frame-skip interval. This avoids over-representing
  longer clips and under-representing short ones.
- **Total frames extracted:** 1,890 (from 63 successfully processed videos; 40 clips
  failed extraction due to file access/corruption issues and were excluded).
- **Annotated so far:** 318 images, manually labeled using [Roboflow](https://roboflow.com).
- **Classes (7):**
  | Class | Description |
  |---|---|
  | `red_light_violation` | Vehicle crossing an intersection during a red signal |
  | `traffic_light_red` | Traffic light in the red state (context for the above) |
  | `illegal_parking` | Vehicles parked in restricted zones |
  | `no_helmet` | Motorcyclists/riders without a helmet |
  | `illegal_overtaking` | Vehicles overtaking across a solid/no-overtaking line |
  | `illegal_u_turn` | Vehicles performing a U-turn in a restricted zone |
  | `number_plate` | Vehicle registration plates (for identification) |

- Class imbalance is expected given the natural frequency of violations in real traffic
  footage; this will be addressed through **data augmentation** (see below) and will be
  monitored during model training with per-class precision/recall.

### 2.3 Annotation Process

- Annotation was performed manually (bounding boxes) using Roboflow's annotation tool by
  the project pair, following an agreed labeling convention:
  - A box is drawn only around the object directly responsible for or evidencing the
    violation (e.g. the overtaking vehicle, not the lane markings; the traffic light
    itself as separate context, not merged into the vehicle's violation box).
  - Frames with no clear, verifiable violation are left unannotated rather than
    force-labeled.
- **Inter-annotator agreement:** As both members of the pair annotate portions of the
  dataset, a sample of overlapping frames will be cross-checked and agreement reported
  (e.g. Cohen's Kappa) in the final report.

### 2.4 Ethical Considerations

- All footage originates from **public roads**, captured via dashcams — a context with a
  reduced expectation of privacy compared to private spaces.
- Vehicle number plates are intentionally **not blurred**, as plate detection is itself a
  target class for this system.
- Bystander/pedestrian faces not directly relevant to a violation are candidates for
  blurring in any future public release or production deployment of this dataset/model;
  this was deprioritized for Milestone 2 given time constraints but is noted as a
  planned improvement.
- No personally identifying metadata (names, addresses) is stored alongside the images.

### 2.5 Preprocessing

- **Frame extraction:** `preprocessing/frame_extractor.py` — extracts a fixed number of
  evenly-spaced frames per video (see Section 2.2).
- **Resizing:** All annotated images are resized to 640×640 (fit, not stretch, to
  preserve aspect ratio) for YOLOv8 compatibility.
- **Augmentation:** Horizontal flip, rotation (±5°), and brightness adjustment (±15%)
  applied to expand the annotated set from 318 to 768 images, improving robustness to
  lighting and orientation variation typical of dashcam footage.
- **Train/Validation/Test split:** 70% / 20% / 10%.

## 3. Repository Structure

```
smart-traffic-violation-detector/
├── datasets/
│   ├── raw_clips/          # Original dashcam video clips (not pushed to GitHub — see below)
│   └── annotated/          # Roboflow-exported YOLOv8-format dataset
│       ├── train/
│       ├── valid/
│       ├── test/
│       └── data.yaml
├── preprocessing/
│   └── frame_extractor.py  # Extracts evenly-spaced frames from raw video clips
├── model/
│   └── train_yolov8.py     # (Planned) YOLOv8 training script — Milestone 3/4
├── blockchain/
│   └── violation_logger.sol # (Planned) Smart contract for violation logging — Milestone 3/4
├── .gitignore
└── README.md
```

> **Note on raw video files:** The original video clips (~1.1GB total) are not stored in
> this repository due to GitHub file-size practicality. They are retained locally and
> in cloud storage; only the extracted/annotated frame dataset is version-controlled
> here.

## 4. Current Status (Milestone 2)

- [x] Raw dashcam clips collected (103 videos)
- [x] Frame extraction pipeline implemented and run (1,890 frames from 63 videos)
- [x] Manual annotation in progress (318 of 1,890 frames labeled across 7 classes)
- [x] Dataset augmented and split (Train/Valid/Test: 70/20/10)
- [ ] Remaining frames to be annotated (ongoing, prioritizing variety over near-duplicate
      frames)
- [ ] Model training (Milestone 3/4)
- [ ] Blockchain violation-logging integration (Milestone 3/4)

## 5. How to Run the Preprocessing Script

```bash
python preprocessing/frame_extractor.py --input datasets/raw_clips --output datasets/frames --frames_per_video 30
```

## 6. Requirements

See `requirements.txt` (to be finalized ahead of Milestone 4). Core dependencies used so
far:

```
opencv-python
```

## 7. Team

- Group pair as registered for Milestone 1 (IT41043).

- A.S.N. Malshan Seeman - ITBIN-2313-0103
- H.A.P.P. Ariyarathna - ITBIN-2313-0009


## 8. Module Information

- **Module Leader:** Mr. Isuru Madusanka Samarappulige
- **Faculty:** Information Technology, Horizon Campus
