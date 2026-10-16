"""Export event-level predictions from events.jsonl for manual ground-truth comparison."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", required=True)
    parser.add_argument(
        "--output",
        help="CSV path (default: same dir as jsonl with _predictions.csv suffix)",
    )
    parser.add_argument(
        "--rule-type",
        help="Optional filter on candidate_type substring",
    )
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl)
    if not jsonl_path.is_file():
        raise SystemExit(f"Not found: {jsonl_path}")

    output = Path(args.output) if args.output else jsonl_path.with_name(jsonl_path.stem + "_predictions.csv")
    fieldnames = [
        "event_id",
        "video_filename",
        "video_timestamp",
        "candidate_type",
        "tracking_id",
        "other_vehicle_tracking_id",
        "signal_state",
        "detection_evidence_score",
        "evidence_image",
        "ground_truth_label",
        "reviewer_notes",
    ]

    rows = []
    with jsonl_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            event = json.loads(line)
            ctype = event.get("candidate_type", "")
            if args.rule_type and args.rule_type not in ctype:
                continue
            crossing = event.get("stop_line_crossing") or {}
            crossing_note = ""
            if crossing:
                prev = crossing.get("previous_center_px")
                cur = crossing.get("current_center_px")
                if prev and cur:
                    crossing_note = f"centers {prev} -> {cur}"
            rows.append(
                {
                    "event_id": event.get("event_id"),
                    "video_filename": event.get("video_filename"),
                    "video_timestamp": event.get("video_timestamp") or event.get("video_timestamp_seconds"),
                    "candidate_type": ctype,
                    "tracking_id": event.get("tracking_id"),
                    "other_vehicle_tracking_id": event.get("other_vehicle_tracking_id", ""),
                    "signal_state": event.get("signal_state", ""),
                    "detection_evidence_score": event.get("detection_evidence_score", ""),
                    "evidence_image": event.get("evidence_image", ""),
                    "ground_truth_label": "",
                    "reviewer_notes": crossing_note or "TP/FP/AMBIGUOUS; FN in red_light_fn_log_template.csv",
                }
            )

    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} prediction rows to {output}")


if __name__ == "__main__":
    main()
