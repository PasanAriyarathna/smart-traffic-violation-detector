"""Export YOLO validation metrics to JSON for research reporting."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate YOLO weights and write metrics JSON.")
    parser.add_argument(
        "--weights",
        default="runs/detect/runs/traffic_violation/yolov8n_v1/weights/best.pt",
    )
    parser.add_argument("--data", default="datasets/training_copy/data.yaml")
    parser.add_argument("--split", default="test", choices=("train", "val", "test"))
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--output",
        default="docs/research_paper/evaluation_results.json",
        help="JSON output path",
    )
    args = parser.parse_args()

    weights = Path(args.weights).resolve()
    data = Path(args.data).resolve()
    if not weights.is_file():
        raise SystemExit(f"Weights not found: {weights}")
    if not data.is_file():
        raise SystemExit(f"Dataset YAML not found: {data}")

    model = YOLO(str(weights))
    metrics = model.val(
        data=str(data),
        split=args.split,
        device=args.device,
        workers=0,
        plots=False,
        verbose=False,
    )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "weights": str(weights),
        "dataset_yaml": str(data),
        "split": args.split,
        "device": args.device,
        "metrics": {
            "precision": float(metrics.box.mp),
            "recall": float(metrics.box.mr),
            "map50": float(metrics.box.map50),
            "map50_95": float(metrics.box.map),
        },
        "notes": [
            "Metrics come from Ultralytics validation on the configured split.",
            "Small held-out sets produce high variance; report per-class metrics separately when publishing.",
        ],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
