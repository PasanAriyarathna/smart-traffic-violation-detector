"""Compute event-level precision/recall from human-labeled prediction CSV."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from scripts.validate_rule_ground_truth import validate_predictions_csv


def count_fn_from_log(path: Path) -> tuple[int, list[str]]:
    """Count FN rows in missed-event log (video_timestamp + description required)."""
    errors: list[str] = []
    count = 0
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return 0, ["FN log has no header"]
        for line_no, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue
            ts = (row.get("video_timestamp") or row.get("video_timestamp_seconds") or "").strip()
            desc = (row.get("description") or row.get("reviewer_notes") or "").strip()
            if not ts or not desc:
                errors.append(f"FN log line {line_no}: need video_timestamp and description")
            else:
                count += 1
    return count, errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions-csv", required=True)
    parser.add_argument(
        "--output",
        default="docs/evaluation/violations/rule_event_metrics.json",
    )
    parser.add_argument(
        "--fn-count",
        type=int,
        default=None,
        help="Independently reviewed missed events (for recall)",
    )
    parser.add_argument(
        "--fn-log-csv",
        help="CSV of missed violations (alternative to --fn-count)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip CSV validation (not recommended)",
    )
    args = parser.parse_args()

    path = Path(args.predictions_csv)
    if not path.is_file():
        raise SystemExit(f"Not found: {path}")

    if not args.skip_validation:
        val_errors = validate_predictions_csv(path)
        if val_errors:
            raise SystemExit("Prediction CSV validation failed:\n- " + "\n- ".join(val_errors))

    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    tp = fp = ambiguous = unlabeled = 0
    for row in rows:
        label = (row.get("ground_truth_label") or "").strip().upper()
        if label == "TP":
            tp += 1
        elif label == "FP":
            fp += 1
        elif label == "AMBIGUOUS":
            ambiguous += 1
        else:
            unlabeled += 1

    fn = args.fn_count
    fn_errors: list[str] = []
    if args.fn_log_csv:
        fn_from_log, fn_errors = count_fn_from_log(Path(args.fn_log_csv))
        if fn is None:
            fn = fn_from_log
        elif fn != fn_from_log:
            fn_errors.append(
                f"--fn-count ({fn}) disagrees with FN log row count ({fn_from_log})"
            )
    if fn_errors:
        raise SystemExit("FN log validation failed:\n- " + "\n- ".join(fn_errors))

    reviewed = tp + fp
    precision = tp / reviewed if reviewed else None
    recall = tp / (tp + fn) if fn is not None and (tp + fn) > 0 else None
    f1 = None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)

    if not rows:
        status = "NOT_MEASURED"
        status_reason = "No prediction rows."
    elif reviewed == 0:
        status = "NOT_MEASURED"
        status_reason = "No TP/FP labels; unlabeled or AMBIGUOUS only."
    elif fn is None:
        status = "PARTIAL"
        status_reason = "Precision available; recall NOT_MEASURED (no independent FN count)."
    else:
        status = "VERIFIED"
        status_reason = "Precision and recall use human-verified TP/FP and independent FN."

    payload = {
        "predictions_csv": str(path.resolve()),
        "total_predictions": len(rows),
        "tp": tp,
        "fp": fp,
        "ambiguous": ambiguous,
        "unlabeled": unlabeled,
        "evaluation_sample_count_for_precision": reviewed,
        "precision": precision,
        "fn_independent": fn,
        "recall": recall,
        "f1": f1,
        "status": status,
        "status_reason": status_reason,
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
