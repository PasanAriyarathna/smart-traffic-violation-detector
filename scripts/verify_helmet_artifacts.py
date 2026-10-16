"""Verify helmet JSONL, CSV, and evidence image counts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSONL = ROOT / "runs/violation_detector/not wearing helmets_20261009_124822/events.jsonl"
CSV = ROOT / "docs/evaluation/rule_review/helmet_not_observed_on_associated_rider_review.csv"
OUT = ROOT / "docs/evaluation/violations/helmet_artifact_verification.json"


def main() -> None:
    events = [
        json.loads(line)
        for line in JSONL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    missing = [
        e["event_id"]
        for e in events
        if not Path(e["evidence_image"]).is_file()
    ]
    track_ids = {e.get("tracking_id") for e in events}
    csv_rows = list(csv.DictReader(CSV.open(encoding="utf-8"))) if CSV.is_file() else []
    payload = {
        "jsonl_path": str(JSONL),
        "jsonl_line_count": len(events),
        "unique_event_ids": len({e["event_id"] for e in events}),
        "unique_tracking_ids": len(track_ids),
        "missing_evidence_files": len(missing),
        "review_csv_rows": len(csv_rows),
        "evidence_dir_jpg_count": len(list((JSONL.parent / "evidence").glob("*.jpg"))),
        "status": "verified" if len(events) == 48 and not missing else "check_required",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
