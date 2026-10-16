"""Build a contact sheet of first frames from overtaking raw clips for manual selection."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import cv2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--clips-dir",
        default="datasets/raw_clips/illegal overtaking",
    )
    parser.add_argument(
        "--output",
        default="docs/evaluation/violations/overtaking/clip_contact_sheet.jpg",
    )
    parser.add_argument("--max-clips", type=int, default=18)
    parser.add_argument("--thumb-width", type=int, default=320)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    clips_dir = root / args.clips_dir
    if not clips_dir.is_dir():
        raise SystemExit(f"Clips directory not found: {clips_dir}")

    clips = sorted(clips_dir.glob("*.mp4"))[: args.max_clips]
    if not clips:
        raise SystemExit(f"No .mp4 files in {clips_dir}")

    thumbs: list[tuple[str, any]] = []
    for clip in clips:
        cap = cv2.VideoCapture(str(clip))
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            continue
        h, w = frame.shape[:2]
        scale = args.thumb_width / w
        thumb = cv2.resize(frame, (args.thumb_width, max(1, int(h * scale))))
        label = clip.name[:36]
        cv2.putText(
            thumb,
            label,
            (4, 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )
        thumbs.append((clip.name, thumb))

    cols = 3
    rows = math.ceil(len(thumbs) / cols)
    row_heights = []
    for r in range(rows):
        row_thumbs = [thumbs[i][1] for i in range(r * cols, min((r + 1) * cols, len(thumbs)))]
        row_heights.append(max(t.shape[0] for t in row_thumbs))
    sheet_h = sum(row_heights) + 8 * (rows + 1)
    sheet_w = cols * args.thumb_width + 8 * (cols + 1)
    sheet = 255 * __import__("numpy").ones((sheet_h, sheet_w, 3), dtype="uint8")

    y = 8
    for r in range(rows):
        x = 8
        rh = row_heights[r]
        for c in range(cols):
            idx = r * cols + c
            if idx >= len(thumbs):
                break
            thumb = thumbs[idx][1]
            th, tw = thumb.shape[:2]
            sheet[y : y + th, x : x + tw] = thumb
            x += args.thumb_width + 8
        y += rh + 8

    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), sheet)
    manifest = out.with_suffix(".txt")
    manifest.write_text("\n".join(name for name, _ in thumbs), encoding="utf-8")
    print(f"Wrote {out} ({len(thumbs)} clips)")
    print(f"Clip list: {manifest}")


if __name__ == "__main__":
    main()
