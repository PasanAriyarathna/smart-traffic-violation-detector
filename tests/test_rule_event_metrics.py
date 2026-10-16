import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.compute_rule_event_metrics import count_fn_from_log
from scripts.validate_rule_ground_truth import validate_predictions_csv


class RuleEventMetricsTests(unittest.TestCase):
    def _write_predictions(self, path: Path, rows: list[dict]) -> None:
        fields = [
            "event_id",
            "video_filename",
            "video_timestamp",
            "candidate_type",
            "tracking_id",
            "ground_truth_label",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    def test_validate_rejects_bad_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.csv"
            self._write_predictions(
                path,
                [
                    {
                        "event_id": "1",
                        "video_filename": "v.mp4",
                        "video_timestamp": "0:00:01",
                        "candidate_type": "test",
                        "tracking_id": "1",
                        "ground_truth_label": "MAYBE",
                    }
                ],
            )
            errors = validate_predictions_csv(path)
            self.assertTrue(any("invalid ground_truth_label" in e for e in errors))

    def test_fn_log_counts_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fn.csv"
            path.write_text(
                "video_filename,video_timestamp,description\n"
                "v.mp4,0:00:05,crossed on red\n",
                encoding="utf-8",
            )
            count, errors = count_fn_from_log(path)
            self.assertEqual(errors, [])
            self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
