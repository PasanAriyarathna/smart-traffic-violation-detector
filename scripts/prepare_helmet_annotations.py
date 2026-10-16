"""Build helmet annotation template from JSONL without inventing human labels."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = (
    ROOT
    / "runs"
    / "violation_detector"
    / "not wearing helmets_20261009_124822"
    / "events.jsonl"
)
OUTPUT = ROOT / "docs" / "evaluation" / "violations" / "helmet_reviewed_annotations.csv"


def main() -> None:
    jsonl_path = DEFAULT_JSONL
    if not jsonl_path.is_file():
        raise SystemExit(f"JSONL not found: {jsonl_path}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "candidate_id",
        "video_id",
        "timestamp",
        "frame_id",
        "track_id",
        "associated_motorcycle_tracking_id",
        "predicted_violation",
        "reviewer_label",
        "confidence_in_review",
        "association_correct",
        "helmet_visible",
        "rider_visible",
        "evidence_quality",
        "ambiguity_reason",
        "reviewer_notes",
        "reviewer_id_or_code",
        "annotation_timestamp",
        "evidence_image",
    ]

    rows = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        evidence = event.get("evidence_image", "")
        rows.append(
            {
                "candidate_id": event.get("event_id"),
                "video_id": event.get("video_filename"),
                "timestamp": event.get("video_timestamp") or event.get("video_timestamp_seconds"),
                "frame_id": "",
                "track_id": event.get("tracking_id"),
                "associated_motorcycle_tracking_id": event.get("associated_motorcycle_tracking_id"),
                "predicted_violation": event.get("candidate_type"),
                "reviewer_label": "Unreviewed",
                "confidence_in_review": "",
                "association_correct": "",
                "helmet_visible": "",
                "rider_visible": "",
                "evidence_quality": "",
                "ambiguity_reason": "",
                "reviewer_notes": "",
                "reviewer_id_or_code": "",
                "annotation_timestamp": "",
                "evidence_image": evidence,
            }
        )

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT}")
    print("All reviewer_label values set to Unreviewed — no autonomous human labels applied.")


if __name__ == "__main__":
    main()
