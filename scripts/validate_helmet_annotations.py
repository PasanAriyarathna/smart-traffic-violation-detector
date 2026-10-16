"""Validate helmet_reviewed_annotations.csv format and evidence paths."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_COLUMNS = {
    "candidate_id",
    "video_id",
    "reviewer_label",
    "evidence_image",
}
VALID_LABELS = {"tp", "fp", "ambiguous", "unreviewed", ""}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        default="docs/evaluation/violations/helmet_reviewed_annotations.csv",
    )
    parser.add_argument(
        "--output",
        default="docs/evaluation/violations/helmet_annotation_validation.json",
    )
    args = parser.parse_args()

    csv_path = ROOT / args.csv
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    if not rows:
        raise SystemExit("CSV has no data rows")

    missing_cols = REQUIRED_COLUMNS - set(rows[0].keys())
    errors: list[str] = []
    warnings: list[str] = []
    label_counts: dict[str, int] = {}

    seen_ids: set[str] = set()
    for index, row in enumerate(rows, start=2):
        cid = (row.get("candidate_id") or "").strip()
        if not cid:
            errors.append(f"Line {index}: missing candidate_id")
        elif cid in seen_ids:
            errors.append(f"Line {index}: duplicate candidate_id {cid}")
        else:
            seen_ids.add(cid)

        label = (row.get("reviewer_label") or "").strip().lower()
        label_counts[label or "empty"] = label_counts.get(label or "empty", 0) + 1
        if label and label not in VALID_LABELS:
            warnings.append(f"Line {index}: non-standard label '{row.get('reviewer_label')}'")

        evidence = (row.get("evidence_image") or "").strip()
        if evidence:
            path = Path(evidence)
            if not path.is_file():
                rel = ROOT / evidence.replace("/", "\\") if not path.is_absolute() else path
                if not rel.is_file():
                    errors.append(f"Line {index}: evidence missing: {evidence}")
        else:
            errors.append(f"Line {index}: empty evidence_image")

    reviewed_tp_fp = sum(
        1
        for row in rows
        if (row.get("reviewer_label") or "").strip().lower() in ("tp", "fp")
    )

    payload = {
        "csv_path": str(csv_path.resolve()),
        "row_count": len(rows),
        "columns_ok": not missing_cols,
        "missing_columns": sorted(missing_cols),
        "label_counts": label_counts,
        "reviewed_tp_or_fp_count": reviewed_tp_fp,
        "precision_measurable": reviewed_tp_fp > 0,
        "errors": errors,
        "warnings": warnings,
        "status": "FAIL" if errors or missing_cols else ("WARN" if warnings else "OK"),
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
