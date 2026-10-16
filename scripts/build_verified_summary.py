"""Aggregate verified experiment outputs into summary JSON/CSV."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_DIR = ROOT / "docs/evaluation/summary"


def latest_detector_experiment() -> tuple[dict, Path] | None:
    dirs = sorted((ROOT / "docs/evaluation/detector").glob("detector_val_test_*"))
    if not dirs:
        return None
    metrics_path = dirs[-1] / "metrics.json"
    if not metrics_path.is_file():
        return None
    return json.loads(metrics_path.read_text(encoding="utf-8")), metrics_path


def main() -> None:
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    detector_pair = latest_detector_experiment()
    detector = detector_pair[0] if detector_pair else None
    detector_source = str(detector_pair[1]) if detector_pair else ""
    if detector:
        m = detector["metrics"]
        rows.append(
            {
                "experiment": "detector_val_test",
                "metric": "precision",
                "value": m["precision"],
                "status": "VERIFIED",
                "source": detector_source,
            }
        )
        rows.append(
            {
                "experiment": "detector_val_test",
                "metric": "map50",
                "value": m["map50"],
                "status": "VERIFIED",
                "source": detector_source,
            }
        )

    helmet_metrics = ROOT / "docs/evaluation/violations/helmet_metrics.json"
    if helmet_metrics.is_file():
        hm = json.loads(helmet_metrics.read_text(encoding="utf-8"))
        rows.append(
            {
                "experiment": "helmet_review",
                "metric": "precision",
                "value": hm.get("precision"),
                "status": "NOT_MEASURED" if hm.get("precision") is None else "VERIFIED",
                "source": str(helmet_metrics),
            }
        )

    payload = {"results": rows, "detector_full": detector}
    (SUMMARY_DIR / "verified_results.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    with (SUMMARY_DIR / "verified_results.csv").open("w", encoding="utf-8", newline="") as handle:
        if rows:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
