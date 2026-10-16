"""Export detection metrics, per-class AP, and paper figures from YOLO val()."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from ultralytics import YOLO


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--weights",
        default="runs/detect/runs/traffic_violation/yolov8n_v1/weights/best.pt",
    )
    parser.add_argument("--data", default="datasets/training_copy/data.yaml")
    parser.add_argument("--split", default="test")
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--output-dir",
        default="docs/research_paper/ieee/generated",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    figures_dir = output_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    weights = Path(args.weights).resolve()
    data = Path(args.data).resolve()
    model = YOLO(str(weights))
    metrics = model.val(
        data=str(data),
        split=args.split,
        device=args.device,
        workers=0,
        plots=True,
        save_json=True,
        verbose=False,
    )

    names = model.names
    if isinstance(names, dict):
        class_names = [names[i] for i in range(len(names))]
    else:
        class_names = list(names)

    ap50 = getattr(metrics.box, "ap50", None)
    per_class: list[dict[str, float | str]] = []
    if ap50 is not None:
        ap50_list = ap50.tolist() if hasattr(ap50, "tolist") else list(ap50)
        for name, value in zip(class_names, ap50_list):
            per_class.append({"class": name, "ap50": float(value)})

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "weights": str(weights),
        "dataset_yaml": str(data),
        "split": args.split,
        "metrics": {
            "precision": float(metrics.box.mp),
            "recall": float(metrics.box.mr),
            "map50": float(metrics.box.map50),
            "map50_95": float(metrics.box.map),
        },
        "per_class_ap50": per_class,
        "save_dir": str(getattr(metrics, "save_dir", "")),
    }
    json_path = output_dir / "yolo_evaluation.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if per_class:
        labels = [row["class"] for row in per_class]
        values = [row["ap50"] for row in per_class]
        figure_path = figures_dir / "per_class_ap50.png"
        plt.figure(figsize=(10, 4.5))
        plt.bar(labels, values, color="#00629B")
        plt.xticks(rotation=45, ha="right")
        plt.ylim(0, 1.0)
        plt.ylabel("AP@0.5")
        plt.title(f"Per-class AP@0.5 ({args.split} split)")
        plt.tight_layout()
        plt.savefig(figure_path, dpi=200)
        plt.close()

    pipeline_path = figures_dir / "pipeline.png"
    plt.figure(figsize=(9, 2.2))
    plt.axis("off")
    steps = [
        "Dashcam video",
        "YOLOv8 + ByteTrack",
        "Rule candidates\n(NEEDS_REVIEW)",
        "Optional OCR\n(plate hash)",
        "Human verify",
        "Sepolia log\n(metadata)",
    ]
    x = np.linspace(0.05, 0.95, len(steps))
    for index, (xi, label) in enumerate(zip(x, steps)):
        plt.text(xi, 0.55, label, ha="center", va="center", fontsize=9, bbox=dict(boxstyle="round", fc="#E8F1F8"))
        if index < len(steps) - 1:
            plt.annotate("", xy=(x[index + 1] - 0.06, 0.55), xytext=(xi + 0.06, 0.55), arrowprops=dict(arrowstyle="->"))
    plt.savefig(pipeline_path, dpi=200, bbox_inches="tight")
    plt.close()

    print(json.dumps(payload, indent=2))
    print(f"Wrote {json_path}")
    print(f"Figures in {figures_dir}")


if __name__ == "__main__":
    main()
