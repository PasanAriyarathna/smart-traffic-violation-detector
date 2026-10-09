# Smart Traffic Violation Detector

Research project exploring computer vision for traffic-scene analysis and
violation detection. The repository currently contains a video-frame
preprocessing utility and project scaffolding; it does not yet provide a
complete, validated detection or violation-decision pipeline.

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
- `model/train_yolvo6.py` is empty; model training is not implemented there.
- There are no inference or object-tracking scripts in the repository.
- `blockchain/violation_logger.sol` is empty; blockchain logging is not
  implemented.
- Dataset source-video provenance has not been established. Do not interpret
  current dataset metrics as reliable video-independent research evaluation.

## Technology

- Python
- OpenCV (`cv2`) for video reading and image writing
- YOLO/Ultralytics and PyTorch are intended for future model work but are not
  declared in a dependency manifest in this repository.
- Solidity is a planned integration area; the current contract file is empty.

## Repository layout

```text
blockchain/                 Solidity project placeholder
datasets/                   Local datasets (excluded from new Git additions)
model/                       Model scripts
preprocessing/               Video frame extraction utility
runs/                        Generated experiment outputs (ignored)
README.md                    Project documentation
```

Raw clips, extracted frames, annotated datasets, training copies, model weights,
and experiment outputs are local research artifacts and should not be added to
GitHub by default. Keep a separate, backed-up copy of any data that is not
tracked in Git.

## Environment setup

Use an isolated Python virtual environment. The frame extractor requires
Python and OpenCV's Python package (`opencv-python`). There is currently no
`requirements.txt`, `pyproject.toml`, or other dependency lock/manifest; record
and pin tested dependency versions before publishing reproducible experiments.
Install Ultralytics and a compatible PyTorch build only when implementing and
validating the model workflow. No install or training command is provided
because the repository does not currently define that workflow.

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

Not implemented. The local `yolov8n.pt` artifact is ignored by Git and is not
provided by this repository. No inference or tracking command is currently
available.

## Dataset, weights, and evaluation

The annotated dataset and model weights are not distributed through this
repository. Obtain the authorized dataset and the intended model weights
separately, and verify their integrity and licenses. Dataset annotations and
split definitions should be retained with appropriate backups.

No validated evaluation metrics are currently reported. Before making research
claims, verify labels and dataset configuration, establish source-video
provenance, prevent videos or near-duplicate frames from crossing splits, and
report metrics such as per-class precision, recall, and mAP on a documented
held-out evaluation set.

## Limitations and next work

- Implement and validate detection, inference, and tracking workflows.
- Resolve dataset provenance and establish video-independent train/validation/
  test splits before evaluating generalization.
- Define a pinned dependency manifest and document exact model/data versions.
- Report reproducible per-class metrics and limitations before claiming
  operational violation detection.
- Implement and test any planned blockchain integration before describing it
  as a functioning feature.
