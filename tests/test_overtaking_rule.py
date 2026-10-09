import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from model.rules.overtaking import OvertakingConfig, OvertakingRule, candidate_record


def make_config(**overrides):
    values = {
        "frame_width": 100,
        "frame_height": 100,
        "lanes": {
            "travel": [[0.0, 0.0], [0.55, 0.0], [0.55, 1.0], [0.0, 1.0]],
            "passing": [[0.55, 0.0], [1.0, 0.0], [1.0, 1.0], [0.55, 1.0]],
        },
        "progress_direction": [0.0, 1.0],
        "prohibited_passing_zones": [
            [[0.55, 0.0], [1.0, 0.0], [1.0, 1.0], [0.55, 1.0]]
        ],
        "prohibition_basis": "Manually reviewed no-passing section for this camera.",
        "minimum_observations": 5,
        "minimum_duration_seconds": 0.5,
        "minimum_order_gap": 0.05,
        "minimum_forward_progress": 0.1,
        "maximum_track_gap_seconds": 0.25,
        "maximum_maneuver_seconds": 3.0,
    }
    values.update(overrides)
    return OvertakingConfig.from_file_dict(values)


def detection(track_id, x, y, name="car", confidence=0.9):
    return SimpleNamespace(
        track_id=track_id,
        name=name,
        confidence=confidence,
        xyxy=(x * 100 - 2, y * 100 - 4, x * 100 + 2, y * 100),
    )


def feed_sequence(rule, actor_id=10, first_actor_id=None, count=5):
    sequence = [
        (0.0, 0.35, 0.20, 0.35),
        (0.2, 0.35, 0.30, 0.40),
        (0.4, 0.75, 0.50, 0.45),
        (0.6, 0.75, 0.60, 0.50),
        (0.8, 0.35, 0.70, 0.55),
    ][:count]
    candidates = []
    for index, (time, actor_x, actor_y, target_y) in enumerate(sequence):
        current_actor_id = first_actor_id if index == 0 and first_actor_id is not None else actor_id
        vehicles = [
            detection(current_actor_id, actor_x, actor_y),
            detection(20, 0.35, target_y, name="truck", confidence=0.8),
        ]
        candidates.extend(rule.update(vehicles, time))
    return candidates


class OvertakingRuleTests(unittest.TestCase):
    def test_complete_same_direction_pass_through_configured_zone(self):
        rule = OvertakingRule(make_config())
        candidates = feed_sequence(rule)
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual((candidate.passing_track_id, candidate.passed_track_id), (10, 20))
        self.assertEqual(candidate.observed_frames, 5)
        record = candidate_record(candidate, "event-1", "evidence.jpg", "clip.mp4")
        self.assertEqual(record["review_status"], "NEEDS_REVIEW")
        self.assertEqual(record["legal_status"], "not_determined")
        self.assertEqual(record["tracking_id"], 10)

    def test_too_few_observations_do_not_create_candidate(self):
        rule = OvertakingRule(make_config())
        self.assertEqual(feed_sequence(rule, count=4), [])

    def test_order_reversal_without_entering_passing_lane_is_not_overtaking(self):
        rule = OvertakingRule(make_config())
        candidates = []
        for time, actor_y, target_y in (
            (0.0, 0.20, 0.35),
            (0.2, 0.30, 0.40),
            (0.4, 0.50, 0.45),
            (0.6, 0.60, 0.50),
            (0.8, 0.70, 0.55),
        ):
            candidates.extend(
                rule.update(
                    [detection(10, 0.35, actor_y), detection(20, 0.35, target_y, name="truck")],
                    time,
                )
            )
        self.assertEqual(candidates, [])

    def test_missing_geometry_or_prohibition_configuration_disables_rule(self):
        incomplete = {
            "frame_width": 100,
            "frame_height": 100,
            "lanes": {},
            "progress_direction": None,
            "prohibited_passing_zones": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "incomplete.json"
            path.write_text(json.dumps(incomplete), encoding="utf-8")
            config = OvertakingConfig.from_file(path)
        self.assertFalse(config.is_supported)
        rule = OvertakingRule(config)
        self.assertEqual(feed_sequence(rule), [])

    def test_tracking_id_change_does_not_stitch_a_maneuver(self):
        rule = OvertakingRule(make_config())
        candidates = feed_sequence(rule, actor_id=11, first_actor_id=10)
        self.assertEqual(candidates, [])

    def test_duplicate_pair_event_is_suppressed(self):
        rule = OvertakingRule(make_config())
        candidates = feed_sequence(rule)
        self.assertEqual(len(candidates), 1)
        # Same track pair remains ahead on the following frame; no duplicate event.
        following = [detection(10, 0.35, 0.75), detection(20, 0.35, 0.60, name="truck")]
        self.assertEqual(rule.update(following, 1.0), [])

    def test_pass_outside_configured_prohibition_zone_is_not_illegal_candidate(self):
        config = make_config(
            prohibited_passing_zones=[
                [[0.85, 0.0], [1.0, 0.0], [1.0, 1.0], [0.85, 1.0]]
            ]
        )
        rule = OvertakingRule(config)
        self.assertEqual(feed_sequence(rule), [])


if __name__ == "__main__":
    unittest.main()
