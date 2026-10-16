import csv
import json
import tempfile
import unittest
from pathlib import Path

from model.rules.red_light import RedLightConfig
from scripts.red_light_signal_utils import (
    SignalIntervalRow,
    parse_interval_csv,
    validate_intervals,
)


class SignalIntervalValidationTests(unittest.TestCase):
    def test_valid_non_overlapping_intervals(self):
        rows = [
            SignalIntervalRow(0.0, 5.0, "red"),
            SignalIntervalRow(5.0, 14.0, "green"),
        ]
        self.assertEqual(validate_intervals(rows, video_duration_seconds=14.25), [])

    def test_unknown_state_allowed(self):
        rows = [SignalIntervalRow(0.0, 14.0, "unknown")]
        self.assertEqual(validate_intervals(rows, video_duration_seconds=14.0), [])

    def test_overlap_rejected(self):
        rows = [
            SignalIntervalRow(0.0, 8.0, "red"),
            SignalIntervalRow(7.0, 14.0, "green"),
        ]
        self.assertTrue(any("Overlapping" in err for err in validate_intervals(rows)))

    def test_invalid_state_rejected(self):
        rows = [SignalIntervalRow(0.0, 5.0, "purple")]
        self.assertTrue(any("invalid state" in err for err in validate_intervals(rows)))

    def test_exceeds_video_duration(self):
        rows = [SignalIntervalRow(0.0, 20.0, "red")]
        self.assertTrue(
            any("exceeds video duration" in err for err in validate_intervals(rows, video_duration_seconds=14.0))
        )

    def test_parse_csv_skips_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "intervals.csv"
            path.write_text(
                "row_type,interval_start_seconds,interval_end_seconds,reviewer_confirmed_state\n"
                "observation,0,,,\n"
                "interval,0,10,red\n",
                encoding="utf-8",
            )
            parsed = parse_interval_csv(path)
            self.assertEqual(len(parsed), 1)
            self.assertEqual(parsed[0].state, "red")

    def test_parse_csv_incomplete_interval_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text(
                "row_type,interval_start_seconds,interval_end_seconds,reviewer_confirmed_state\n"
                "interval,0,,red\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                parse_interval_csv(path)

    def test_merged_config_loads_in_red_light_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = {
                "frame_width": 100,
                "frame_height": 100,
                "traffic_light_regions": [[0.8, 0.0, 1.0, 0.2]],
                "stop_line": [[10.0, 50.0], [90.0, 50.0]],
                "approach_side": 1,
                "signal_states": [{"start_seconds": 0, "end_seconds": 5, "state": "unknown"}],
            }
            cfg_path = Path(tmp) / "cfg.json"
            cfg_path.write_text(json.dumps(base), encoding="utf-8")
            base["signal_states"] = [{"start_seconds": 0, "end_seconds": 5, "state": "red"}]
            merged = Path(tmp) / "merged.json"
            merged.write_text(json.dumps(base), encoding="utf-8")
            parsed = RedLightConfig.from_file(merged)
            self.assertEqual(parsed.state_at(1.0), "red")
            self.assertEqual(parsed.state_at(6.0), "unknown")


    def test_v2_geometry_config_loads(self):
        root = Path(__file__).resolve().parents[1]
        cfg = root / "docs/evaluation/violations/red_light/config_red_light_video_v2_geometry.json"
        if not cfg.is_file():
            self.skipTest("v2 geometry config missing")
        parsed = RedLightConfig.from_file(cfg)
        self.assertEqual(parsed.state_at(1.0), "unknown")


if __name__ == "__main__":
    unittest.main()
