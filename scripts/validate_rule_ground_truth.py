"""Validate prediction / ground-truth CSV before computing event metrics."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

VALID_LABELS = frozenset({"TP", "FP", "AMBIGUOUS", ""})
REQUIRED_COLUMNS = frozenset(
    {
        "event_id",
        "video_filename",
        "video_timestamp",
        "candidate_type",
        "ground_truth_label",
    }
)


def validate_predictions_csv(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return ["CSV has no header row"]
        missing = REQUIRED_COLUMNS - {h.strip() for h in reader.fieldnames if h}
        if missing:
            errors.append(f"Missing required columns: {sorted(missing)}")
            return errors
        seen_ids: dict[str, int] = {}
        for line_no, row in enumerate(reader, start=2):
            label = (row.get("ground_truth_label") or "").strip().upper()
            if label not in VALID_LABELS:
                errors.append(f"Line {line_no}: invalid ground_truth_label {label!r}")
            eid = (row.get("event_id") or "").strip()
            if eid:
                seen_ids[eid] = seen_ids.get(eid, 0) + 1
        dupes = [eid for eid, count in seen_ids.items() if count > 1]
        if dupes:
            errors.append(f"Duplicate event_id values: {dupes[:5]}" + ("..." if len(dupes) > 5 else ""))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions-csv", required=True)
    args = parser.parse_args()
    path = Path(args.predictions_csv)
    if not path.is_file():
        raise SystemExit(f"Not found: {path}")
    errors = validate_predictions_csv(path)
    if errors:
        raise SystemExit("Validation failed:\n- " + "\n- ".join(errors))
    print(f"OK: {path}")


if __name__ == "__main__":
    main()
