"""Analyze and enhance plate crops; write plate_crops_enhanced + CSV + contact sheet."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT))

from model.plate_crop_enhance import analyze_crop, enhance_plate_crop


def _contact_sheet(
    pairs: list[tuple[np.ndarray, np.ndarray, str]],
    out_path: Path,
    *,
    thumb_h: int = 80,
) -> None:
    """Side-by-side original (left) | enhanced (right) per row."""
    if not pairs:
        return
    rows: list[np.ndarray] = []
    label_h = 22
    for orig, enh, name in pairs:
        def _thumb(img: np.ndarray) -> np.ndarray:
            h, w = img.shape[:2]
            scale = thumb_h / max(h, 1)
            tw = max(20, int(w * scale))
            th = max(20, int(h * scale))
            t = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)
            bar = np.full((label_h, tw, 3), 255, dtype=np.uint8)
            cv2.putText(
                bar,
                name[:42],
                (2, 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (0, 0, 0),
                1,
            )
            return np.vstack([bar, t])

        left = _thumb(orig)
        right = _thumb(enh)
        max_h = max(left.shape[0], right.shape[0])
        pad = lambda im, target: (  # noqa: E731
            np.pad(im, ((0, target - im.shape[0]), (0, 0), (0, 0)), constant_values=255)
            if im.shape[0] < target
            else im
        )
        left, right = pad(left, max_h), pad(right, max_h)
        gap = np.full((max_h, 8, 3), 200, dtype=np.uint8)
        rows.append(np.hstack([left, gap, right]))
    max_w = max(r.shape[1] for r in rows)
    padded = []
    for r in rows:
        if r.shape[1] < max_w:
            r = np.pad(r, ((0, 0), (0, max_w - r.shape[1]), (0, 0)), constant_values=255)
        padded.append(r)
    sheet = np.vstack(padded)
    cv2.imwrite(str(out_path), sheet)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        default="docs/evaluation/plate_crops",
        help="Original plate crops (read-only)",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/evaluation/plate_crops_enhanced",
    )
    parser.add_argument(
        "--report-csv",
        default="docs/evaluation/plate_crops_enhanced/enhancement_report.csv",
    )
    parser.add_argument(
        "--analysis-json",
        default="docs/evaluation/plate_crops_enhanced/enhancement_analysis.json",
    )
    parser.add_argument(
        "--contact-sheet",
        default="docs/evaluation/plate_crops_enhanced/enhancement_contact_sheet.jpg",
    )
    args = parser.parse_args()

    in_dir = ROOT / args.input_dir
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    report_rows: list[dict[str, str]] = []
    analysis_summary: list[dict] = []
    contact_pairs: list[tuple[np.ndarray, np.ndarray, str]] = []

    paths = sorted(in_dir.glob("*.jpg"))
    if not paths:
        raise SystemExit(f"No JPG crops in {in_dir}")

    for path in paths:
        orig = cv2.imread(str(path))
        if orig is None:
            report_rows.append(
                {
                    "filename": path.name,
                    "status": "read_failed",
                    "orig_width": "",
                    "orig_height": "",
                    "enh_width": "",
                    "enh_height": "",
                    "enhancement_methods": "",
                    "detected_issues": "",
                }
            )
            continue
        pre = analyze_crop(orig)
        result = enhance_plate_crop(orig)
        out_path = out_dir / path.name
        cv2.imwrite(str(out_path), result.image_bgr)
        eh, ew = result.image_bgr.shape[:2]
        report_rows.append(
            {
                "filename": path.name,
                "status": "ok",
                "orig_width": str(pre.width),
                "orig_height": str(pre.height),
                "enh_width": str(ew),
                "enh_height": str(eh),
                "enhancement_methods": ";".join(result.methods),
                "detected_issues": ";".join(pre.issues) if pre.issues else "none",
                "scale_factor": f"{result.scale_factor:.3f}",
            }
        )
        analysis_summary.append(
            {
                "filename": path.name,
                "orig": [pre.width, pre.height],
                "enhanced": [ew, eh],
                "laplacian_variance": pre.laplacian_variance,
                "gray_std": pre.gray_std,
                "issues": list(pre.issues),
                "methods": list(result.methods),
            }
        )
        contact_pairs.append((orig, result.image_bgr, path.name))

    report_path = ROOT / args.report_csv
    report_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "filename",
        "status",
        "orig_width",
        "orig_height",
        "enh_width",
        "enh_height",
        "scale_factor",
        "enhancement_methods",
        "detected_issues",
    ]
    with report_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    analysis_path = ROOT / args.analysis_json
    analysis_path.write_text(
        json.dumps({"crop_count": len(paths), "crops": analysis_summary}, indent=2),
        encoding="utf-8",
    )

    _contact_sheet(contact_pairs, ROOT / args.contact_sheet)

    ok = sum(1 for r in report_rows if r.get("status") == "ok")
    print(f"Enhanced {ok}/{len(paths)} crops -> {out_dir}")
    print(f"Report: {report_path}")
    print(f"Contact sheet: {ROOT / args.contact_sheet}")


if __name__ == "__main__":
    main()
