"""Validate human signal CSV and merge into a new red-light JSON config."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.rules.red_light import RedLightConfig

from scripts.red_light_signal_utils import parse_interval_csv, validate_intervals


def video_duration_from_file(video_path: Path) -> float:
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    if fps <= 0 or count <= 0:
        raise SystemExit("Could not read video duration")
    return float(count) / float(fps)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-config",
        default="docs/evaluation/violations/red_light/config_red_light_video_v2_geometry.json",
    )
    parser.add_argument(
        "--review-csv",
        default="docs/evaluation/violations/red_light/signal_state_intervals.csv",
        help="CSV with row_type=interval rows (see signal_state_intervals_template.csv)",
    )
    parser.add_argument(
        "--output",
        default="docs/evaluation/violations/red_light/config_red_light_video_v2_human_signals.json",
    )
    parser.add_argument(
        "--video",
        help="Optional video path to bound interval end times (recommended)",
    )
    parser.add_argument(
        "--video-duration-seconds",
        type=float,
        help="Override video duration in seconds",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate CSV without writing merged config",
    )
    parser.add_argument(
        "--require-full-coverage",
        action="store_true",
        help="Require intervals to cover 0..video_duration with no gaps",
    )
    args = parser.parse_args()

    csv_path = ROOT / args.review_csv
    if not csv_path.is_file():
        raise SystemExit(f"Review CSV not found: {csv_path}")

    duration = args.video_duration_seconds
    if duration is None and args.video:
        video_path = Path(args.video)
        if not video_path.is_file():
            video_path = ROOT / args.video
        duration = video_duration_from_file(video_path)

    try:
        intervals = parse_interval_csv(csv_path)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    errors = validate_intervals(
        intervals,
        video_duration_seconds=duration,
        require_full_coverage=args.require_full_coverage,
    )
    if errors:
        raise SystemExit("Validation failed:\n- " + "\n- ".join(errors))

    if args.validate_only:
        print(f"OK: {len(intervals)} interval(s) validated.")
        if duration is not None:
            print(f"Video duration bound: {duration:.3f}s")
        return

    base_path = ROOT / args.base_config
    base = json.loads(base_path.read_text(encoding="utf-8"))
    base["signal_states"] = [
        {
            "start_seconds": item.start_seconds,
            "end_seconds": item.end_seconds,
            "state": item.state,
        }
        for item in sorted(intervals, key=lambda x: x.start_seconds)
    ]
    base.pop("_evidence_notes", None)

    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(base, indent=2), encoding="utf-8")

    RedLightConfig.from_file(out)
    print(f"Wrote and schema-validated {out} ({len(intervals)} interval(s))")


if __name__ == "__main__":
    main()
