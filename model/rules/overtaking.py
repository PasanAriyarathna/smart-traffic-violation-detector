"""Conservative fixed-camera overtaking maneuver review candidates.

This rule uses tracked box trajectories and manually configured image geometry.
It does not determine traffic law or establish a confirmed violation.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any


Point = tuple[float, float]
Polygon = tuple[Point, ...]
VEHICLE_CLASSES = {"car", "bus", "truck", "motorcycle", "three_wheeler"}


@dataclass(frozen=True)
class TrackObservation:
    timestamp_seconds: float
    point: Point
    progress: float
    lane: str | None
    confidence: float


@dataclass(frozen=True)
class OvertakingCandidate:
    passing_track_id: int
    passed_track_id: int
    vehicle_class: str
    timestamp_seconds: float
    passing_confidence: float
    passed_confidence: float
    start_gap: float
    end_gap: float
    observed_frames: int
    maneuver_duration_seconds: float
    prohibition_basis: str
    prohibited_zone_index: int


def _parse_polygon(value: Any, field_name: str) -> Polygon | None:
    if value is None:
        return None
    points = tuple(tuple(float(coord) for coord in point) for point in value)
    if len(points) < 3 or any(len(point) != 2 for point in points):
        raise ValueError(f"{field_name} must be a polygon with at least three [x, y] points")
    if any(not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0) for x, y in points):
        raise ValueError(f"{field_name} polygon coordinates must be normalized to 0..1")
    return points


def _point_in_polygon(point: Point, polygon: Polygon) -> bool:
    x, y = point
    inside = False
    previous_x, previous_y = polygon[-1]
    for current_x, current_y in polygon:
        if (current_y > y) != (previous_y > y):
            crossing_x = (previous_x - current_x) * (y - current_y) / (previous_y - current_y) + current_x
            if x < crossing_x:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


@dataclass(frozen=True)
class OvertakingConfig:
    frame_width: int
    frame_height: int
    travel_lane: Polygon | None
    passing_lane: Polygon | None
    progress_direction: Point | None
    prohibited_zones: tuple[Polygon, ...]
    prohibition_basis: str | None
    minimum_observations: int = 6
    minimum_duration_seconds: float = 0.5
    minimum_order_gap: float = 0.025
    minimum_forward_progress: float = 0.04
    maximum_track_gap_seconds: float = 0.25
    maximum_maneuver_seconds: float = 5.0
    unsupported_reason: str | None = None

    @classmethod
    def from_file(cls, path: str | Path) -> "OvertakingConfig":
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read overtaking config {path}: {exc}") from exc
        return cls.from_file_dict(raw)

    @classmethod
    def from_file_dict(cls, raw: dict[str, Any]) -> "OvertakingConfig":
        try:
            width, height = int(raw["frame_width"]), int(raw["frame_height"])
            lanes = raw.get("lanes", {})
            travel_lane = _parse_polygon(lanes.get("travel"), "lanes.travel")
            passing_lane = _parse_polygon(lanes.get("passing"), "lanes.passing")
            raw_direction = raw.get("progress_direction")
            direction = tuple(float(value) for value in raw_direction) if raw_direction is not None else None
            raw_zones = raw.get("prohibited_passing_zones", [])
            zones = tuple(
                polygon
                for index, value in enumerate(raw_zones)
                if (polygon := _parse_polygon(value, f"prohibited_passing_zones[{index}]")) is not None
            )
            basis = raw.get("prohibition_basis")
            settings = {
                "minimum_observations": int(raw.get("minimum_observations", 6)),
                "minimum_duration_seconds": float(raw.get("minimum_duration_seconds", 0.5)),
                "minimum_order_gap": float(raw.get("minimum_order_gap", 0.025)),
                "minimum_forward_progress": float(raw.get("minimum_forward_progress", 0.04)),
                "maximum_track_gap_seconds": float(raw.get("maximum_track_gap_seconds", 0.25)),
                "maximum_maneuver_seconds": float(raw.get("maximum_maneuver_seconds", 5.0)),
            }
            reason = raw.get("unsupported_reason")
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as exc:
            raise ValueError(f"Invalid overtaking config structure: {exc}") from exc

        if width <= 0 or height <= 0:
            raise ValueError("frame_width and frame_height must be positive")
        if direction is not None and (len(direction) != 2 or math.hypot(*direction) <= 0.0):
            raise ValueError("progress_direction must be a nonzero [dx, dy] vector")
        if direction is not None:
            magnitude = math.hypot(*direction)
            direction = (direction[0] / magnitude, direction[1] / magnitude)
        if settings["minimum_observations"] < 4:
            raise ValueError("minimum_observations must be at least 4")
        if settings["minimum_duration_seconds"] <= 0 or settings["maximum_maneuver_seconds"] < settings["minimum_duration_seconds"]:
            raise ValueError("maneuver duration limits are invalid")
        if settings["minimum_order_gap"] <= 0 or settings["minimum_forward_progress"] <= 0:
            raise ValueError("progress and ordering thresholds must be positive")
        if settings["maximum_track_gap_seconds"] <= 0:
            raise ValueError("track gap must be positive")

        return cls(
            width,
            height,
            travel_lane,
            passing_lane,
            direction,
            zones,
            str(basis).strip() if basis and str(basis).strip() else None,
            **settings,
            unsupported_reason=str(reason) if reason else None,
        )

    @property
    def unsupported_reasons(self) -> tuple[str, ...]:
        reasons = []
        if self.travel_lane is None:
            reasons.append("travel-lane polygon is not configured")
        if self.passing_lane is None:
            reasons.append("passing-lane polygon is not configured")
        if self.progress_direction is None:
            reasons.append("fixed-view direction of travel is not configured")
        if not self.prohibited_zones:
            reasons.append("no manually configured prohibited-passing zone is supplied")
        if self.prohibition_basis is None:
            reasons.append("prohibition basis is not documented")
        if self.unsupported_reason:
            reasons.append(self.unsupported_reason)
        return tuple(reasons)

    @property
    def is_supported(self) -> bool:
        return not self.unsupported_reasons


class OvertakingRule:
    """Require a sustained same-direction pass and return across configured lanes."""

    def __init__(self, config: OvertakingConfig) -> None:
        self.config = config
        self.histories: dict[int, deque[TrackObservation]] = defaultdict(deque)
        self.last_seen: dict[int, float] = {}
        self.reported_pairs: set[tuple[int, int]] = set()

    def _lane(self, point: Point) -> str | None:
        if self.config.travel_lane and _point_in_polygon(point, self.config.travel_lane):
            return "travel"
        if self.config.passing_lane and _point_in_polygon(point, self.config.passing_lane):
            return "passing"
        return None

    def update(self, detections: list[Any], timestamp_seconds: float) -> list[OvertakingCandidate]:
        if not self.config.is_supported:
            return []

        current: dict[int, Any] = {}
        direction = self.config.progress_direction
        assert direction is not None
        for detection in detections:
            if detection.name not in VEHICLE_CLASSES or detection.track_id is None:
                continue
            track_id = detection.track_id
            current[track_id] = detection
            x1, _, x2, y2 = detection.xyxy
            point = ((x1 + x2) / (2.0 * self.config.frame_width), y2 / self.config.frame_height)
            progress = point[0] * direction[0] + point[1] * direction[1]
            history = self.histories[track_id]
            if history and timestamp_seconds - history[-1].timestamp_seconds > self.config.maximum_track_gap_seconds:
                history.clear()
            observation = TrackObservation(
                timestamp_seconds, point, progress, self._lane(point), detection.confidence
            )
            if history and history[-1].timestamp_seconds == timestamp_seconds:
                history[-1] = observation
            else:
                history.append(observation)
            self.last_seen[track_id] = timestamp_seconds
            while history and timestamp_seconds - history[0].timestamp_seconds > self.config.maximum_maneuver_seconds:
                history.popleft()

        for track_id in list(self.histories):
            if timestamp_seconds - self.last_seen.get(track_id, timestamp_seconds) > self.config.maximum_track_gap_seconds:
                self.histories.pop(track_id, None)
                self.last_seen.pop(track_id, None)

        candidates: list[OvertakingCandidate] = []
        ordered_ids = sorted(current)
        for passing_id in ordered_ids:
            actor_history = self.histories[passing_id]
            for passed_id in ordered_ids:
                if passed_id == passing_id:
                    continue
                pair = (passing_id, passed_id)
                if pair in self.reported_pairs:
                    continue
                target_history = self.histories[passed_id]
                maneuver = self._find_maneuver(actor_history, target_history)
                if maneuver is None:
                    continue
                start, end, zone_index, sample_count, start_gap, end_gap = maneuver
                actor_detection = current[passing_id]
                target_detection = current[passed_id]
                candidates.append(
                    OvertakingCandidate(
                        passing_id,
                        passed_id,
                        actor_detection.name,
                        timestamp_seconds,
                        actor_detection.confidence,
                        target_detection.confidence,
                        start_gap,
                        end_gap,
                        sample_count,
                        end.timestamp_seconds - start.timestamp_seconds,
                        self.config.prohibition_basis or "",
                        zone_index,
                    )
                )
                self.reported_pairs.add(pair)
        return candidates

    def _find_maneuver(
        self,
        actor_history: deque[TrackObservation],
        target_history: deque[TrackObservation],
    ) -> tuple[TrackObservation, TrackObservation, int, int, float, float] | None:
        target_by_time = {obs.timestamp_seconds: obs for obs in target_history}
        common = [(actor, target_by_time[actor.timestamp_seconds])
                  for actor in actor_history if actor.timestamp_seconds in target_by_time]
        if len(common) < self.config.minimum_observations:
            return None
        if common[-1][0].timestamp_seconds - common[0][0].timestamp_seconds < self.config.minimum_duration_seconds:
            return None

        actor_start, target_start = common[0]
        actor_end, target_end = common[-1]
        if actor_start.lane != "travel" or target_start.lane != "travel":
            return None
        if actor_end.lane != "travel" or target_end.lane != "travel":
            return None
        start_gap = actor_start.progress - target_start.progress
        end_gap = actor_end.progress - target_end.progress
        if start_gap > -self.config.minimum_order_gap or end_gap < self.config.minimum_order_gap:
            return None
        if actor_end.progress - actor_start.progress < self.config.minimum_forward_progress:
            return None
        if target_end.progress - target_start.progress < self.config.minimum_forward_progress:
            return None
        actor_steps = [pair[0].progress for pair in common]
        target_steps = [pair[1].progress for pair in common]
        reverse_tolerance = self.config.minimum_order_gap * 0.2
        for steps in (actor_steps, target_steps):
            forward_fraction = sum(
                1 for previous, current in zip(steps, steps[1:])
                if current - previous >= -reverse_tolerance
            ) / max(1, len(steps) - 1)
            if forward_fraction < 0.75:
                return None
        if any(target.lane != "travel" for _, target in common):
            return None

        pass_samples = [
            (index, actor, target)
            for index, (actor, target) in enumerate(common)
            if actor.lane == "passing"
        ]
        if not pass_samples:
            return None
        crossed_while_passing = any(
            actor.progress >= target.progress
            for _, actor, target in pass_samples
        )
        if not crossed_while_passing:
            return None
        first_pass_index, last_pass_index = pass_samples[0][0], pass_samples[-1][0]
        zone_index = None
        for index, actor, _ in pass_samples:
            if first_pass_index <= index <= last_pass_index:
                zone_index = next(
                    (zone_idx for zone_idx, zone in enumerate(self.config.prohibited_zones)
                     if _point_in_polygon(actor.point, zone)),
                    None,
                )
                if zone_index is not None:
                    break
        if zone_index is None:
            return None
        return actor_start, actor_end, zone_index, len(common), start_gap, end_gap


def candidate_record(
    candidate: OvertakingCandidate,
    event_id: str,
    evidence_image: str,
    video_filename: str,
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "video_filename": video_filename,
        "video_timestamp_seconds": round(candidate.timestamp_seconds, 3),
        "video_timestamp": _format_time(candidate.timestamp_seconds),
        "tracking_id": candidate.passing_track_id,
        "other_vehicle_tracking_id": candidate.passed_track_id,
        "vehicle_class": candidate.vehicle_class,
        "candidate_type": "possible_overtaking_in_configured_prohibited_zone",
        "review_status": "NEEDS_REVIEW",
        "configured_prohibition_basis": candidate.prohibition_basis,
        "legal_status": "not_determined",
        "maneuver_evidence": {
            "observed_frames": candidate.observed_frames,
            "duration_seconds": round(candidate.maneuver_duration_seconds, 3),
            "prohibited_zone_index": candidate.prohibited_zone_index,
            "initial_order_gap_normalized": round(candidate.start_gap, 5),
            "final_order_gap_normalized": round(candidate.end_gap, 5),
        },
        "detection_evidence_score": round(min(candidate.passing_confidence, candidate.passed_confidence), 4),
        "detection_evidence_score_definition": "Minimum detector confidence of the two tracked vehicles; not a probability of overtaking or illegality.",
        "evidence_note": "Persistent trajectories fit the configured behind-to-ahead pass sequence and intersect a manually configured prohibited-passing zone. Lane geometry and legal conditions require independent review; this is not a confirmed traffic violation.",
        "evidence_image": evidence_image,
    }


def _format_time(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"
