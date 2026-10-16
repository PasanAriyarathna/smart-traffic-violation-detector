"""Frame-by-frame stop-line and signal review for one track in a time window."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.rules.red_light import RedLightConfig, RedLightRule
from scripts.diagnose_rule_video_run import DEFAULT_WEIGHTS, VEHICLE_NAMES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--track-id", type=int, required=True)
    parser.add_argument("--t-start", type=float, default=10.5)
    parser.add_argument("--t-end", type=float, default=12.5)
    parser.add_argument("--event-t", type=float, help="Expected detector event time (seconds)")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--conf", type=float, default=0.25)
    args = parser.parse_args()

    from ultralytics import YOLO

    config = RedLightConfig.from_file(args.config)
    rule = RedLightRule(config)
    video = Path(args.source)
    out = Path(args.output_dir)
    frames_dir = out / "annotated_frames"
    roi_dir = out / "signal_roi"
    frames_dir.mkdir(parents=True, exist_ok=True)
    roi_dir.mkdir(parents=True, exist_ok=True)

    model = YOLO(str(DEFAULT_WEIGHTS))
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    region = config.traffic_light_regions[0]
    rx1, ry1, rx2, ry2 = region

    timeline: list[dict] = []
    crossing_events: list[dict] = []
    frame_index = 0
    saved_paths: list[str] = []

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = frame_index / fps
        if t > args.t_end + (2.0 / fps):
            break

        results = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=args.conf,
            verbose=False,
        )[0]

        target = None
        vehicles = []
        if results.boxes is not None:
            names = results.names
            for box in results.boxes:
                cls_id = int(box.cls[0])
                name = names.get(cls_id, str(cls_id))
                tid = int(box.id[0]) if box.id is not None else None
                xyxy = tuple(float(v) for v in box.xyxy[0].tolist())
                if name in VEHICLE_NAMES and tid is not None:
                    det = type("D", (), {"track_id": tid, "name": name, "xyxy": xyxy, "confidence": float(box.conf[0])})()
                    vehicles.append(det)
                    if tid == args.track_id:
                        target = det

        cands = rule.update(vehicles, t) if args.t_start <= t <= args.t_end + 1e-6 else []
        for c in cands:
            if c.track_id == args.track_id:
                crossing_events.append(
                    {
                        "video_seconds": round(t, 4),
                        "frame_index": frame_index,
                        "signal_state_config": c.signal_state,
                        "prev_center": list(c.previous_center),
                        "cur_center": list(c.current_center),
                    }
                )

        in_window = args.t_start <= t <= args.t_end
        entry: dict = {
            "frame_index": frame_index,
            "video_seconds": round(t, 4),
            "track_present": target is not None,
        }
        if target is not None:
            x1, y1, x2, y2 = target.xyxy
            cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            signed = rule._signed_side((cx, cy))
            entry.update(
                {
                    "center_px": [round(cx, 2), round(cy, 2)],
                    "bbox_xyxy": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                    "signed_side": round(signed, 2),
                    "approach_side": config.approach_side,
                    "on_approach_side": signed * config.approach_side > 0 if config.approach_side else None,
                    "detector_confidence": round(target.confidence, 4),
                }
            )
        timeline.append(entry)

        if in_window:
            vis = frame.copy()
            h, w = vis.shape[:2]
            if config.stop_line:
                (lx1, ly1), (lx2, ly2) = config.stop_line
                cv2.line(vis, (int(lx1), int(ly1)), (int(lx2), int(ly2)), (255, 255, 0), 2)
                cv2.putText(vis, "stop_line", (int(lx1), int(ly1) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            cv2.rectangle(
                vis,
                (int(rx1 * w), int(ry1 * h)),
                (int(rx2 * w), int(ry2 * h)),
                (0, 255, 255),
                2,
            )
            if results.boxes is not None:
                names = results.names
                for box in results.boxes:
                    cls_id = int(box.cls[0])
                    name = names.get(cls_id, str(cls_id))
                    if name not in VEHICLE_NAMES:
                        continue
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    tid = int(box.id[0]) if box.id is not None else -1
                    color = (0, 0, 255) if tid == args.track_id else (0, 255, 0)
                    cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(vis, f"id={tid}", (x1, max(0, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
                    if tid == args.track_id:
                        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                        cv2.circle(vis, (cx, cy), 4, (0, 0, 255), -1)
            label = f"t={t:.3f}s f={frame_index}"
            if target is not None:
                label += f" id{args.track_id} side={entry.get('signed_side')}"
            cv2.putText(vis, label, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
            stem = f"t_{t:07.3f}s_f{frame_index:04d}"
            fp = frames_dir / f"{stem}.jpg"
            cv2.imwrite(str(fp), vis)
            saved_paths.append(str(fp.relative_to(out)))
            roi = frame[int(ry1 * h) : int(ry2 * h), int(rx1 * w) : int(rx2 * w)]
            cv2.imwrite(str(roi_dir / f"{stem}.jpg"), roi)

        frame_index += 1

    cap.release()

    # contact sheet (every saved frame, 4 cols)
    thumbs = []
    for p in sorted(frames_dir.glob("*.jpg")):
        img = cv2.imread(str(p))
        if img is None:
            continue
        thumb = cv2.resize(img, (400, 225))
        thumbs.append(thumb)
    if thumbs:
        cols = 4
        rows = int(np.ceil(len(thumbs) / cols))
        sheet = np.zeros((rows * 230, cols * 410, 3), dtype=np.uint8)
        for i, thumb in enumerate(thumbs):
            r, c = divmod(i, cols)
            sheet[r * 230 : r * 230 + thumb.shape[0], c * 410 : c * 410 + thumb.shape[1]] = thumb
        cv2.imwrite(str(out / "crossing_window_contact_sheet.jpg"), sheet)

    event_frame = None
    if args.event_t is not None:
        event_frame = int(round(args.event_t * fps))

    payload = {
        "source_video": str(video.resolve()),
        "config": str(Path(args.config).resolve()),
        "fps": fps,
        "window_seconds": [args.t_start, args.t_end],
        "track_id": args.track_id,
        "expected_event_seconds": args.event_t,
        "expected_event_frame_index": event_frame,
        "rule_crossing_emissions_in_window": crossing_events,
        "timeline_track_rows": [e for e in timeline if e.get("track_present") or (args.t_start <= e["video_seconds"] <= args.t_end)],
        "saved_frame_count": len(saved_paths),
    }
    (out / "crossing_verification.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"crossings": crossing_events, "saved": len(saved_paths)}, indent=2))


if __name__ == "__main__":
    main()
