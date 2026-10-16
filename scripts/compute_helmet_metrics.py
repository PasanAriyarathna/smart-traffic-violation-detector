"""Compute helmet review metrics from helmet_reviewed_annotations.csv."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        default="docs/evaluation/violations/helmet_reviewed_annotations.csv",
    )
    parser.add_argument(
        "--output",
        default="docs/evaluation/violations/helmet_metrics.json",
    )
    parser.add_argument(
        "--fn-video-count",
        type=int,
        default=None,
        help="Optional independently reviewed missed-case count for recall",
    )
    args = parser.parse_args()

    csv_path = ROOT / args.csv
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    total = len(rows)
    labels = [(row.get("reviewer_label") or "").strip().lower() for row in rows]

    tp = sum(1 for label in labels if label == "tp")
    fp = sum(1 for label in labels if label == "fp")
    ambiguous = sum(1 for label in labels if label == "ambiguous")
    unreviewed = sum(1 for label in labels if label in ("", "unreviewed"))
    other = total - tp - fp - ambiguous - unreviewed

    reviewed = tp + fp
    precision = tp / reviewed if reviewed else None
    fn = args.fn_video_count
    recall = tp / (tp + fn) if fn is not None and (tp + fn) > 0 else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and (precision + recall) > 0
        else None
    )

    payload = {
        "formulas": {
            "precision": "TP / (TP + FP) on reviewed candidate rows labeled TP or FP",
            "recall": "TP / (TP + FN) where FN comes from independent full-video review, not CSV rows",
            "f1": "2 * precision * recall / (precision + recall)",
        },
        "total_candidates": total,
        "tp": tp,
        "fp": fp,
        "ambiguous": ambiguous,
        "unreviewed": unreviewed + other,
        "reviewed_for_precision": reviewed,
        "precision": precision,
        "fn_independent_video_review": fn,
        "recall": recall,
        "f1": f1,
        "limitations": [
            "Recall is NOT MEASURED until fn_independent_video_review is supplied.",
            "Unreviewed and Ambiguous rows are excluded from precision.",
            "Metrics are candidate-level, not legal violation convictions.",
        ],
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
