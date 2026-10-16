"""Extract per-second frames + traffic-light ROI crops for manual signal review."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--config-json", required=True, help="Red-light JSON with traffic_light_regions")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    args = parser.parse_args()

    import json
    import sys

    root = Path(__file__).resolve().parents[1]
    raw = json.loads(Path(args.config_json).read_text(encoding="utf-8"))
    region = raw["traffic_light_regions"][0]

    cap = cv2.VideoCapture(str(args.source))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    out_dir = Path(args.output_dir)
    frames_dir = out_dir / "full_frames"
    roi_dir = out_dir / "signal_roi"
    frames_dir.mkdir(parents=True, exist_ok=True)
    roi_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    fi = 0
    next_t = 0.0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = fi / fps
        if t + 1e-6 >= next_t:
            x1, y1, x2, y2 = region
            h, w = frame.shape[:2]
            rx1, ry1, rx2, ry2 = int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)
            roi = frame[ry1:ry2, rx1:rx2].copy()
            cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (0, 255, 255), 2)
            cv2.putText(
                frame,
                f"t={t:.2f}s f={fi}",
                (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
            )
            stem = f"t_{t:05.2f}s_f{fi:04d}"
            full_path = frames_dir / f"{stem}.jpg"
            roi_path = roi_dir / f"{stem}.jpg"
            cv2.imwrite(str(full_path), frame)
            cv2.imwrite(str(roi_path), roi)
            manifest.append({"video_seconds": round(t, 3), "frame_index": fi, "full": str(full_path.name), "roi": str(roi_path.name)})
            next_t += args.interval_seconds
        fi += 1
    cap.release()

    # contact sheet from ROI thumbs
    thumbs = []
    for entry in manifest:
        img = cv2.imread(str(roi_dir / entry["roi"]))
        if img is None:
            continue
        thumb = cv2.resize(img, (240, 120))
        cv2.putText(thumb, f"{entry['video_seconds']:.1f}s", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        thumbs.append(thumb)
    cols = 5
    rows = math.ceil(len(thumbs) / cols) if thumbs else 1
    sheet = np.zeros((rows * 130, cols * 250, 3), dtype=np.uint8)
    for i, thumb in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet[r * 130 : r * 130 + thumb.shape[0], c * 250 : c * 250 + thumb.shape[1]] = thumb
    sheet_path = out_dir / "signal_roi_contact_sheet.jpg"
    cv2.imwrite(str(sheet_path), sheet)
    (out_dir / "manifest.json").write_text(__import__("json").dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {len(manifest)} samples to {out_dir}")


if __name__ == "__main__":
    main()
