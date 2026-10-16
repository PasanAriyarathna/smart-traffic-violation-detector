"""Foot-point vs bbox center relative to configured stop line (investigation aid)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.rules.red_light import RedLightConfig


def main() -> None:
    verification = ROOT / "docs/evaluation/violations/red_light/investigation_20261009/crossing_verification_11_788/crossing_verification.json"
    config = RedLightConfig.from_file(
        ROOT / "docs/evaluation/violations/red_light/config_red_light_video_v2_geometry.json"
    )
    data = json.loads(verification.read_text(encoding="utf-8"))
    stop_y = config.stop_line[0][1] if config.stop_line else None
    rows = []
    for entry in data["timeline_track_rows"]:
        if not entry.get("track_present"):
            continue
        bb = entry.get("bbox_xyxy")
        if not bb:
            continue
        x1, y1, x2, y2 = bb
        cx, cy = entry["center_px"]
        foot = ((x1 + x2) / 2.0, y2)
        rows.append(
            {
                "frame_index": entry["frame_index"],
                "video_seconds": entry["video_seconds"],
                "center_y": cy,
                "foot_y": y2,
                "center_vs_stop_line": round(cy - stop_y, 2) if stop_y is not None else None,
                "foot_vs_stop_line": round(y2 - stop_y, 2) if stop_y is not None else None,
                "center_on_approach_side": bool(entry.get("on_approach_side")),
            }
        )
    out = verification.parent / "track130_stop_bar_geometry.json"
    out.write_text(json.dumps({"stop_line_y_px": stop_y, "samples": rows}, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
