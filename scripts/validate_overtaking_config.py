"""Validate overtaking JSON config against schema and support requirements."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.rules.overtaking import OvertakingConfig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--probe-video",
        help="Optional clip to compare frame dimensions with config",
    )
    args = parser.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        raise SystemExit(f"Not found: {cfg_path}")

    config = OvertakingConfig.from_file(cfg_path)
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    print(f"Loaded {cfg_path}")
    print(f"  frame: {config.frame_width}x{config.frame_height}")
    print(f"  travel_lane: {'set' if config.travel_lane else 'MISSING'}")
    print(f"  passing_lane: {'set' if config.passing_lane else 'MISSING'}")
    print(f"  progress_direction: {config.progress_direction}")
    print(f"  prohibited_zones: {len(config.prohibited_zones)}")

    if args.probe_video:
        import cv2

        vpath = Path(args.probe_video)
        if not vpath.is_file():
            vpath = ROOT / args.probe_video
        cap = cv2.VideoCapture(str(vpath))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if (w, h) != (config.frame_width, config.frame_height):
            raise SystemExit(
                f"Dimension mismatch: video {w}x{h} vs config "
                f"{config.frame_width}x{config.frame_height}"
            )
        print(f"  video dimensions match: {w}x{h}")

    if not config.is_supported:
        print("Status: NOT READY — unsupported_reasons:")
        for reason in config.unsupported_reasons:
            print(f"  - {reason}")
        raise SystemExit(1)

    print("Status: OK — configuration is supported for detection runs.")


if __name__ == "__main__":
    main()
