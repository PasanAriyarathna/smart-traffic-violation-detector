"""Diagnose zero rule candidates: detections, tracking, geometry, signal coverage."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.rules.overtaking import OvertakingConfig, OvertakingRule, _point_in_polygon
from model.rules.red_light import RedLightConfig, RedLightRule

DEFAULT_WEIGHTS = ROOT / "runs/detect/runs/traffic_violation/yolov8n_v1/weights/best.pt"
VEHICLE_NAMES = {"car", "bus", "truck", "three_wheeler", "motorcycle"}


class SimpleDetection:
    __slots__ = ("track_id", "name", "confidence", "xyxy")

    def __init__(self, track_id, name, confidence, xyxy):
        self.track_id = track_id
        self.name = name
        self.confidence = confidence
        self.xyxy = xyxy


def draw_red_config(frame: np.ndarray, config: RedLightConfig) -> None:
    h, w = frame.shape[:2]
    if config.stop_line:
        (x1, y1), (x2, y2) = config.stop_line
        cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
        cv2.putText(frame, "stop_line", (int(x1), int(y1) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    for region in config.traffic_light_regions:
        x1, y1, x2, y2 = region
        cv2.rectangle(
            frame,
            (int(x1 * w), int(y1 * h)),
            (int(x2 * w), int(y2 * h)),
            (0, 255, 255),
            2,
        )


def draw_overtaking_config(frame: np.ndarray, config: OvertakingConfig) -> None:
    h, w = frame.shape[:2]
    for polygon, color, label in (
        (config.travel_lane, (255, 200, 0), "travel"),
        (config.passing_lane, (0, 220, 255), "passing"),
    ):
        if polygon:
            pts = np.array([(int(x * w), int(y * h)) for x, y in polygon], dtype=np.int32)
            cv2.polylines(frame, [pts], True, color, 2)
            cv2.putText(frame, label, tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    for index, polygon in enumerate(config.prohibited_zones):
        pts = np.array([(int(x * w), int(y * h)) for x, y in polygon], dtype=np.int32)
        cv2.polylines(frame, [pts], True, (0, 0, 255), 2)
        cv2.putText(frame, f"prohibited_{index}", tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)


def run_tracking(source: Path, max_frames: int, conf: float):
    from ultralytics import YOLO

    model = YOLO(str(DEFAULT_WEIGHTS))
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise SystemExit(f"Cannot open {source}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_stats = []
    all_detections_by_frame: list[tuple[float, list[SimpleDetection]]] = []
    frame_index = 0

    while frame_index < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        results = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=conf,
            verbose=False,
        )[0]
        names = results.names
        detections: list[SimpleDetection] = []
        if results.boxes is not None and len(results.boxes):
            for box in results.boxes:
                cls_id = int(box.cls[0])
                name = names.get(cls_id, str(cls_id))
                tid = int(box.id[0]) if box.id is not None else None
                xyxy = tuple(float(v) for v in box.xyxy[0].tolist())
                detections.append(SimpleDetection(tid, name, float(box.conf[0]), xyxy))
        vehicles = [d for d in detections if d.name in VEHICLE_NAMES and d.track_id is not None]
        t = frame_index / fps
        frame_stats.append(
            {
                "frame_index": frame_index,
                "video_seconds": round(t, 3),
                "total_detections": len(detections),
                "vehicle_tracked": len(vehicles),
                "vehicle_classes": sorted({d.name for d in vehicles}),
            }
        )
        all_detections_by_frame.append((t, vehicles))
        frame_index += 1
    cap.release()
    return width, height, fps, frame_stats, all_detections_by_frame


def diagnose_red(config_path: Path, detections_by_frame: list, fps: float) -> dict:
    config = RedLightConfig.from_file(config_path)
    rule = RedLightRule(config)
    crossings_any = 0
    crossings_red = 0
    candidates_total = 0
    states_seen: dict[str, int] = defaultdict(int)

    class CrossingProbe(RedLightRule):
        def update(self, vehicles, timestamp_seconds):
            nonlocal crossings_any, crossings_red
            state = config.state_at(timestamp_seconds)
            states_seen[state] += 1
            if not config.is_supported:
                return []
            for vehicle in vehicles:
                track_id = vehicle.track_id
                if track_id is None:
                    continue
                x1, y1, x2, y2 = vehicle.xyxy
                center = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
                previous = self.previous.get(track_id)
                if previous and self._crosses_segment(previous[0], center):
                    crossings_any += 1
                    st = config.state_during(previous[2], timestamp_seconds)
                    if st == "red":
                        crossings_red += 1
            return super().update(vehicles, timestamp_seconds)

    probe = CrossingProbe(config)
    for t, vehicles in detections_by_frame:
        cands = probe.update(vehicles, t)
        candidates_total += len(cands)

    max_t = detections_by_frame[-1][0] if detections_by_frame else 0.0
    covered_red = [
        {
            "start": iv.start_seconds,
            "end": iv.end_seconds,
            "state": iv.state,
            "overlaps_run_window": iv.start_seconds < max_t and iv.end_seconds > 0,
        }
        for iv in config.signal_intervals
    ]
    return {
        "config_supported": config.is_supported,
        "unsupported_reasons": list(config.unsupported_reasons),
        "run_duration_seconds_approx": round(max_t, 3),
        "signal_intervals": covered_red,
        "signal_states_observed_during_run": dict(states_seen),
        "stop_line_crossings_geometry_only": crossings_any,
        "crossings_during_reviewed_red_interval": crossings_red,
        "rule_candidates_emitted": candidates_total,
    }


def diagnose_overtaking(config_path: Path, detections_by_frame: list) -> dict:
    config = OvertakingConfig.from_file(config_path)
    rule = OvertakingRule(config)
    lane_counts = {"travel": 0, "passing": 0, "outside": 0}
    unique_tracks: set[int] = set()

    def lane_label(det: SimpleDetection) -> str:
        x1, _, x2, y2 = det.xyxy
        point = ((x1 + x2) / (2.0 * config.frame_width), y2 / config.frame_height)
        if config.travel_lane and _point_in_polygon(point, config.travel_lane):
            return "travel"
        if config.passing_lane and _point_in_polygon(point, config.passing_lane):
            return "passing"
        return "outside"

    for _, vehicles in detections_by_frame:
        for v in vehicles:
            unique_tracks.add(v.track_id)
            lane_counts[lane_label(v)] += 1

    candidates_total = 0
    for t, vehicles in detections_by_frame:
        candidates_total += len(rule.update(vehicles, t))

    return {
        "config_supported": config.is_supported,
        "unsupported_reasons": list(config.unsupported_reasons),
        "vehicle_observations_in_travel_lane": lane_counts["travel"],
        "vehicle_observations_in_passing_lane": lane_counts["passing"],
        "vehicle_observations_outside_configured_lanes": lane_counts["outside"],
        "unique_vehicle_track_ids": len(unique_tracks),
        "rule_candidates_emitted": candidates_total,
    }


def save_diagnostic_frames(
    source: Path,
    out_dir: Path,
    config_kind: str,
    config_path: Path,
    frame_indices: list[int],
    conf: float,
) -> None:
    from ultralytics import YOLO

    out_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(DEFAULT_WEIGHTS))
    cap = cv2.VideoCapture(str(source))
    if config_kind == "red_light":
        config = RedLightConfig.from_file(config_path)
    else:
        config = OvertakingConfig.from_file(config_path)

    index = 0
    saved = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if index in frame_indices:
            results = model.track(frame, persist=True, tracker="bytetrack.yaml", conf=conf, verbose=False)[0]
            vis = frame.copy()
            if results.boxes is not None:
                names = results.names
                for box in results.boxes:
                    cls_id = int(box.cls[0])
                    name = names.get(cls_id, str(cls_id))
                    if name not in VEHICLE_NAMES:
                        continue
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    tid = int(box.id[0]) if box.id is not None else -1
                    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        vis,
                        f"id={tid} {name}",
                        (x1, max(0, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (0, 255, 0),
                        1,
                    )
            if config_kind == "red_light":
                draw_red_config(vis, config)
            else:
                draw_overtaking_config(vis, config)
            path = out_dir / f"frame_{index:04d}.jpg"
            cv2.imwrite(str(path), vis)
            saved.append(str(path))
        index += 1
        if index > max(frame_indices):
            break
    cap.release()
    return saved  # type: ignore[return-value]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--kind", choices=("red_light", "overtaking"), required=True)
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    source = Path(args.source)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Re-read video for frame saves
    cap = cv2.VideoCapture(str(source))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.release()

    width, height, fps, frame_stats, det_frames = run_tracking(
        source, args.max_frames, args.conf
    )
    if args.kind == "red_light":
        rule_diag = diagnose_red(Path(args.config), det_frames, fps)
    else:
        rule_diag = diagnose_overtaking(Path(args.config), det_frames)

    sample_indices = sorted({0, args.max_frames // 4, args.max_frames // 2, (3 * args.max_frames) // 4, args.max_frames - 1})
    frames_saved = save_diagnostic_frames(
        source, out / "frames", args.kind, Path(args.config), sample_indices, args.conf
    )

    total_vehicle_obs = sum(s["vehicle_tracked"] for s in frame_stats)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_video": str(source.resolve()),
        "config": str(Path(args.config).resolve()),
        "kind": args.kind,
        "max_frames": args.max_frames,
        "video_geometry": {"width": width, "height": height, "fps": round(fps, 3)},
        "detector": {"weights": str(DEFAULT_WEIGHTS), "conf": args.conf, "tracker": "bytetrack.yaml"},
        "aggregate_detections": {
            "frames_processed": len(frame_stats),
            "sum_vehicle_tracked_per_frame": total_vehicle_obs,
            "frames_with_zero_vehicles": sum(1 for s in frame_stats if s["vehicle_tracked"] == 0),
        },
        "rule_diagnosis": rule_diag,
        "diagnostic_frames": frames_saved,
        "sample_frame_stats": frame_stats[:: max(1, len(frame_stats) // 10)][:12],
    }
    (out / "diagnosis.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
