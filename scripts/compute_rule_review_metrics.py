"""Aggregate TP/FP/FN counts from filled rule review CSV files."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-dir", default="docs/evaluation/rule_review")
    parser.add_argument(
        "--output",
        default="docs/research_paper/ieee/generated/rule_review_metrics.json",
    )
    args = parser.parse_args()

    review_dir = Path(args.review_dir)
    if not review_dir.is_dir():
        raise SystemExit(f"Review directory not found: {review_dir}")

    summary: dict[str, dict[str, int | float | None]] = {}
    for csv_path in sorted(review_dir.glob("*_review.csv")):
        counts = {"TP": 0, "FP": 0, "FN": 0, "unlabeled": 0}
        with csv_path.open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                label = (row.get("reviewer_label") or "").strip().upper()
                if label in counts:
                    counts[label] += 1
                else:
                    counts["unlabeled"] += 1
        tp, fp = counts["TP"], counts["FP"]
        precision = tp / (tp + fp) if (tp + fp) else None
        summary[csv_path.stem] = {
            **counts,
            "precision_among_labeled_candidates": precision,
        }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
