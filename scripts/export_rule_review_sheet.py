"""Convert detector JSONL output into manual FP/FN review spreadsheets."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


# Canonical candidate_type strings emitted by model/rules/*.py (export uses all types found in JSONL).
CANONICAL_CANDIDATE_TYPES = (
    "helmet_not_observed_on_associated_rider",
    "vehicle_crossed_configured_stop_line_during_reviewed_red_interval",
    "possible_overtaking_in_configured_prohibited_zone",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", required=True, help="events.jsonl from violation_detector.py")
    parser.add_argument(
        "--output-dir",
        default="docs/evaluation/rule_review",
    )
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl)
    if not jsonl_path.is_file():
        raise SystemExit(f"JSONL not found: {jsonl_path}")

    by_type: dict[str, list[dict]] = defaultdict(list)
    with jsonl_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            candidate_type = event.get("candidate_type", "unknown")
            by_type[candidate_type].append(event)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for candidate_type, events in by_type.items():
        safe_name = candidate_type.replace(" ", "_")
        csv_path = output_dir / f"{safe_name}_review.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "event_id",
                    "video_filename",
                    "video_timestamp",
                    "candidate_type",
                    "detection_evidence_score",
                    "association_score",
                    "evidence_image",
                    "reviewer_label",
                    "reviewer_notes",
                ],
            )
            writer.writeheader()
            for event in events:
                writer.writerow(
                    {
                        "event_id": event.get("event_id"),
                        "video_filename": event.get("video_filename"),
                        "video_timestamp": event.get("video_timestamp") or event.get("video_timestamp_seconds"),
                        "candidate_type": candidate_type,
                        "detection_evidence_score": event.get("detection_evidence_score"),
                        "association_score": event.get("association_score"),
                        "evidence_image": event.get("evidence_image"),
                        "reviewer_label": "",
                        "reviewer_notes": "TP=correct candidate, FP=false alarm, FN=missed violation (external)",
                    }
                )
        print(f"Wrote {csv_path} ({len(events)} rows)")

    summary_path = output_dir / "README.txt"
    summary_path.write_text(
        "Fill reviewer_label with TP, FP, or FN after watching evidence_image paths.\n"
        "Then run: python scripts/compute_rule_review_metrics.py --review-dir docs/evaluation/rule_review\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
