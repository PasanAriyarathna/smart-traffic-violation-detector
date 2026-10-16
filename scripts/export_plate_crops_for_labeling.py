"""Export number_plate crops and a CSV template for manual ground-truth transcription."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
import yaml

CLASS_NAMES = [
    "broken_line",
    "bus",
    "car",
    "crosswalk",
    "double_solid_line",
    "helmet",
    "motorcycle",
    "number_plate",
    "person",
    "solid_line",
    "three_wheeler",
    "traffic_light",
    "truck",
]
PLATE_CLASS_ID = CLASS_NAMES.index("number_plate")


def yolo_box_to_pixels(
    cx: float, cy: float, w: float, h: float, img_w: int, img_h: int
) -> tuple[int, int, int, int]:
    x1 = int(round((cx - w / 2) * img_w))
    y1 = int(round((cy - h / 2) * img_h))
    x2 = int(round((cx + w / 2) * img_w))
    y2 = int(round((cy + h / 2) * img_h))
    x1 = max(0, min(img_w - 1, x1))
    y1 = max(0, min(img_h - 1, y1))
    x2 = max(0, min(img_w, x2))
    y2 = max(0, min(img_h, y2))
    return x1, y1, x2, y2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="datasets/training_copy/data.yaml")
    parser.add_argument("--split", default="test", choices=("train", "val", "test"))
    parser.add_argument(
        "--output-dir",
        default="docs/evaluation/plate_crops",
    )
    parser.add_argument(
        "--csv",
        default="docs/evaluation/plates_labeled.csv",
    )
    args = parser.parse_args()

    data_yaml = Path(args.data)
    raw = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    split_key = {"train": "train", "val": "valid", "test": "test"}[args.split]
    images_rel = raw[split_key if split_key in raw else args.split]
    images_dir = (data_yaml.parent / images_rel).resolve()
    labels_dir = images_dir.parent.parent / args.split / "labels"
    if not labels_dir.is_dir():
        labels_dir = images_dir.parent / "labels"

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    for image_path in sorted(images_dir.glob("*.*")):
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        label_path = labels_dir / f"{image_path.stem}.txt"
        if not label_path.is_file():
            continue
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        img_h, img_w = image.shape[:2]
        plate_index = 0
        for line in label_path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) != 5:
                continue
            class_id = int(float(parts[0]))
            if class_id != PLATE_CLASS_ID:
                continue
            cx, cy, w, h = map(float, parts[1:])
            x1, y1, x2, y2 = yolo_box_to_pixels(cx, cy, w, h, img_w, img_h)
            if x2 <= x1 or y2 <= y1:
                continue
            crop = image[y1:y2, x1:x2]
            crop_name = f"{image_path.stem}_plate{plate_index}.jpg"
            crop_path = out_dir / crop_name
            cv2.imwrite(str(crop_path), crop)
            rows.append(
                {
                    "image_path": str(crop_path.resolve()),
                    "source_image": image_path.name,
                    "ground_truth_plate": "",
                    "annotator": "",
                    "notes": "Fill ground_truth_plate manually for CER evaluation",
                }
            )
            plate_index += 1

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["image_path", "source_image", "ground_truth_plate", "annotator", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} plate crops to {out_dir}")
    print(f"CSV template: {csv_path}")
    if not rows:
        print("No number_plate boxes found in labels for this split.")


if __name__ == "__main__":
    main()
