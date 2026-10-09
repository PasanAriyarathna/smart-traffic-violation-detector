import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from model.rules.red_light import (
    RedLightConfig,
    RedLightRule,
    SignalInterval,
    candidate_record,
)


def config(states, cooldown=10.0):
    return RedLightConfig(
        frame_width=100,
        frame_height=100,
        traffic_light_regions=((0.8, 0.0, 1.0, 0.2),),
        stop_line=((0.0, 50.0), (100.0, 50.0)),
        approach_side=-1,
        signal_intervals=tuple(states),
        cooldown_seconds=cooldown,
    )


def vehicle(track_id, center_y, name="car"):
    return SimpleNamespace(
        track_id=track_id,
        name=name,
        confidence=0.8,
        xyxy=(45.0, center_y - 5.0, 55.0, center_y + 5.0),
    )


class RedLightRuleTests(unittest.TestCase):
    def test_incomplete_config_is_accepted_but_explicitly_disables_rule(self):
        raw = {
            "frame_width": 1268,
            "frame_height": 718,
            "traffic_light_regions": [],
            "stop_line": None,
            "approach_side": None,
            "signal_states": [],
            "unsupported_reason": "lane mapping not established",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "incomplete.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            parsed = RedLightConfig.from_file(path)
        self.assertFalse(parsed.is_supported)
        self.assertEqual(
            RedLightRule(parsed).update([vehicle(1, 40), vehicle(1, 60)], 1.0), []
        )

    def test_crossing_during_reviewed_red_interval_creates_candidate(self):
        rule = RedLightRule(config([SignalInterval(0.0, 5.0, "red")]))
        self.assertEqual(rule.update([vehicle(7, 40)], 0.0), [])
        candidates = rule.update([vehicle(7, 60)], 1.0)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].track_id, 7)
        self.assertEqual(candidates[0].signal_state, "red")
        record = candidate_record(candidates[0], "event-1", "evidence.jpg", "clip.mp4")
        self.assertEqual(record["review_status"], "NEEDS_REVIEW")
        self.assertEqual(record["tracking_id"], 7)
        self.assertEqual(record["evidence_image"], "evidence.jpg")
        self.assertEqual(record["signal_state"], "red")

    def test_unknown_or_uncovered_signal_state_never_creates_candidate(self):
        for states in (
            [],
            [SignalInterval(0.0, 5.0, "amber")],
            [SignalInterval(2.0, 5.0, "red")],
        ):
            with self.subTest(states=states):
                rule = RedLightRule(config(states))
                rule.update([vehicle(1, 40)], 0.0)
                self.assertEqual(rule.update([vehicle(1, 60)], 1.0), [])

    def test_green_interval_never_creates_candidate(self):
        rule = RedLightRule(config([SignalInterval(0.0, 5.0, "green")]))
        rule.update([vehicle(1, 40)], 0.0)
        self.assertEqual(rule.update([vehicle(1, 60)], 1.0), [])

    def test_no_crossing_or_missing_track_id_creates_no_candidate(self):
        rule = RedLightRule(config([SignalInterval(0.0, 5.0, "red")]))
        rule.update([vehicle(1, 40)], 0.0)
        self.assertEqual(rule.update([vehicle(1, 45)], 1.0), [])
        rule.update([vehicle(None, 40)], 2.0)
        self.assertEqual(rule.update([vehicle(None, 60)], 3.0), [])

    def test_same_track_crossing_is_deduplicated_during_cooldown(self):
        rule = RedLightRule(config([SignalInterval(0.0, 30.0, "red")]))
        rule.update([vehicle(3, 40)], 0.0)
        self.assertEqual(len(rule.update([vehicle(3, 60)], 1.0)), 1)
        rule.update([], 2.0)
        rule.update([vehicle(3, 40)], 3.0)
        self.assertEqual(rule.update([vehicle(3, 60)], 4.0), [])
        rule.update([], 12.0)
        rule.update([vehicle(3, 40)], 13.0)
        self.assertEqual(len(rule.update([vehicle(3, 60)], 14.0)), 1)

    def test_crossing_must_intersect_finite_stop_line_segment(self):
        rule = RedLightRule(config([SignalInterval(0.0, 5.0, "red")]))
        outside_segment = SimpleNamespace(
            track_id=9, name="car", confidence=0.8,
            xyxy=(145.0, 35.0, 155.0, 45.0),
        )
        rule.update([outside_segment], 0.0)
        outside_segment = SimpleNamespace(
            track_id=9, name="car", confidence=0.8,
            xyxy=(145.0, 55.0, 155.0, 65.0),
        )
        self.assertEqual(rule.update([outside_segment], 1.0), [])


if __name__ == "__main__":
    unittest.main()
