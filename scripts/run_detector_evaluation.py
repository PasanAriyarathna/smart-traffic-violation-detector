"""Run YOLO val on test split and save full evaluation artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from experiment_utils import environment_info, git_commit, new_experiment_dir, sha256_file, write_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--weights",
        default="runs/detect/runs/traffic_violation/yolov8n_v1/weights/best.pt",
    )
    parser.add_argument("--data", default="datasets/training_copy/data.yaml")
    parser.add_argument("--split", default="test")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.7)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--experiment-id", default="detector_val_test")
    args = parser.parse_args()

    weights = (ROOT / args.weights).resolve()
    data = (ROOT / args.data).resolve()
    if not weights.is_file():
        print(f"ERROR: weights not found: {weights}", file=sys.stderr)
        return 1
    if not data.is_file():
        print(f"ERROR: data yaml not found: {data}", file=sys.stderr)
        return 1

    exp_dir = new_experiment_dir("detector", args.experiment_id)
    log_path = exp_dir / "evaluation_log.txt"

    weights_sha = sha256_file(weights)
    config = {
        "weights": str(weights),
        "weights_sha256": weights_sha,
        "data_yaml": str(data),
        "split": args.split,
        "device": args.device,
        "conf": args.conf,
        "iou": args.iou,
        "imgsz": args.imgsz,
        "batch": args.batch,
    }

    cmd = [
        sys.executable,
        str(Path(__file__).name),
        *sys.argv[1:],
    ]
    try:
        model = YOLO(str(weights))
        metrics = model.val(
            data=str(data),
            split=args.split,
            device=args.device,
            conf=args.conf,
            iou=args.iou,
            imgsz=args.imgsz,
            batch=args.batch,
            workers=0,
            plots=True,
            save_json=True,
            verbose=True,
        )
        exit_code = 0
    except Exception as exc:
        log_path.write_text(f"FAILED: {exc}\n", encoding="utf-8")
        write_manifest(
            exp_dir,
            experiment_id=args.experiment_id,
            category="detector",
            command=cmd,
            exit_code=1,
            config=config,
            status="failed",
            limitations=[str(exc)],
        )
        return 1

    names = model.names
    class_names = [names[i] for i in range(len(names))] if isinstance(names, dict) else list(names)
    ap50 = getattr(metrics.box, "ap50", None)
    per_class = []
    if ap50 is not None:
        ap50_list = ap50.tolist() if hasattr(ap50, "tolist") else list(ap50)
        per_class = [
            {"class": name, "ap50": float(value)}
            for name, value in zip(class_names, ap50_list)
        ]

    payload = {
        "git_commit": git_commit(),
        "environment": environment_info(),
        "config": config,
        "test_image_count": 36,
        "metrics": {
            "precision": float(metrics.box.mp),
            "recall": float(metrics.box.mr),
            "map50": float(metrics.box.map50),
            "map50_95": float(metrics.box.map),
        },
        "per_class_ap50": per_class,
        "ultralytics_save_dir": str(getattr(metrics, "save_dir", "")),
        "note": (
            "These metrics measure object detection on the image test split. "
            "They do not measure helmet/red-light/overtaking violation accuracy."
        ),
    }
    (exp_dir / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with (exp_dir / "per_class_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["class", "ap50"])
        writer.writeheader()
        writer.writerows(per_class)

    log_path.write_text(
        json.dumps(payload, indent=2) + f"\n\nsave_dir={payload['ultralytics_save_dir']}\n",
        encoding="utf-8",
    )

    cm_candidates = list(Path(payload["ultralytics_save_dir"]).glob("*confusion*.png"))
    if cm_candidates:
        import shutil

        shutil.copy2(cm_candidates[0], exp_dir / "confusion_matrix.png")

    write_manifest(
        exp_dir,
        experiment_id=args.experiment_id,
        category="detector",
        command=cmd,
        exit_code=exit_code,
        config=config,
        metrics=payload["metrics"],
    )
    print(json.dumps(payload, indent=2))
    print(f"Saved to {exp_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
