"""One-off probe: stop-line crossings + traffic-light ROI samples (investigation aid)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.rules.red_light import RedLightConfig, RedLightRule
from scripts.diagnose_rule_video_run import run_tracking


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-frames", type=int, default=416)
    args = parser.parse_args()

    video = Path(args.source)
    cfg = RedLightConfig.from_file(args.config)
    rule = RedLightRule(cfg)
    w, h, fps, _stats, dets = run_tracking(video, args.max_frames, 0.25)

    crossings = []
    for t, vehicles in dets:
        for v in vehicles:
            tid = v.track_id
            x1, y1, x2, y2 = v.xyxy
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            prev = rule.previous.get(tid)
            if prev and prev[1] == v.name and rule._crosses_segment(prev[0], center):
                crossings.append(
                    {
                        "video_seconds": round(t, 3),
                        "track_id": tid,
                        "vehicle_class": v.name,
                        "interval_start_t": round(prev[2], 3),
                        "prev_center_px": [round(prev[0][0], 1), round(prev[0][1], 1)],
                        "cur_center_px": [round(center[0], 1), round(center[1], 1)],
                        "state_during_user_cycle": cfg.state_during(prev[2], t),
                    }
                )
            rule.previous[tid] = (center, v.name, t)

    cap = cv2.VideoCapture(str(video))
    region = cfg.traffic_light_regions[0]
    samples = []
    fi = 0
    step = max(1, int(round(fps)))
    while fi < args.max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        t = fi / fps
        if fi % step == 0:
            x1, y1, x2, y2 = region
            height, width = frame.shape[:2]
            roi = frame[int(y1 * height) : int(y2 * height), int(x1 * width) : int(x2 * width)]
            if roi.size:
                b, g, r = cv2.split(roi)
                samples.append(
                    {
                        "frame_index": fi,
                        "video_seconds": round(t, 3),
                        "mean_r": round(float(r.mean()), 1),
                        "mean_g": round(float(g.mean()), 1),
                        "mean_b": round(float(b.mean()), 1),
                        "red_dominant_heuristic": bool(
                            float(r.mean()) > float(g.mean()) + 12 and float(r.mean()) > float(b.mean()) + 12
                        ),
                    }
                )
        fi += 1
    cap.release()

    payload = {
        "source_video": str(video.resolve()),
        "config": str(Path(args.config).resolve()),
        "fps": fps,
        "stop_line_crossings": crossings,
        "traffic_light_roi_samples_1hz": samples,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"crossings": crossings, "roi_samples": len(samples)}, indent=2))


if __name__ == "__main__":
    main()
