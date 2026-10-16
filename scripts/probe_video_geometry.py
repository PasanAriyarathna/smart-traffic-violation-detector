"""Print frame size and FPS for fixed-camera rule JSON configuration."""

from __future__ import annotations

import argparse
import math

import cv2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    cap = cv2.VideoCapture(args.source)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video: {args.source}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if not math.isfinite(fps) or fps <= 0:
        fps = 25.0
    cap.release()
    print(f"frame_width={width}")
    print(f"frame_height={height}")
    print(f"fps={fps:.3f}")


if __name__ == "__main__":
    main()
