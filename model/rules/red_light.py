"""Opt-in fixed-camera red-light crossing candidates.

Signal colors are supplied as manually reviewed time intervals. This module
does not infer a signal state from the detector's generic ``traffic_light``
class and never confirms a legal violation.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


Point = tuple[float, float]


@dataclass(frozen=True)
class SignalInterval:
    start_seconds: float
    end_seconds: float
    state: str


@dataclass(frozen=True)
class RedLightCandidate:
    track_id: int
    vehicle_class: str
    confidence: float
    timestamp_seconds: float
    signal_state: str
    previous_center: Point
    current_center: Point


@dataclass(frozen=True)
class RedLightConfig:
    frame_width: int
    frame_height: int
    traffic_light_regions: tuple[tuple[float, float, float, float], ...]
    stop_line: tuple[Point, Point] | None
    approach_side: int | None
    signal_intervals: tuple[SignalInterval, ...]
    cooldown_seconds: float = 10.0
    unsupported_reason: str | None = None

    @classmethod
    def from_file(cls, path: str | Path) -> "RedLightConfig":
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read red-light config {path}: {exc}") from exc
        try:
            width, height = int(raw["frame_width"]), int(raw["frame_height"])
            regions = tuple(tuple(float(v) for v in rect) for rect in raw.get("traffic_light_regions", []))
            raw_line = raw.get("stop_line")
            line = (
                tuple(tuple(float(v) for v in point) for point in raw_line)
                if raw_line is not None
                else None
            )
            raw_approach_side = raw.get("approach_side")
            approach_side = int(raw_approach_side) if raw_approach_side is not None else None
            intervals = tuple(
                SignalInterval(float(item["start_seconds"]), float(item["end_seconds"]), str(item["state"]).lower())
                for item in raw.get("signal_states", [])
            )
            cooldown = float(raw.get("cooldown_seconds", 10.0))
            unsupported_reason = raw.get("unsupported_reason")
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Invalid red-light config structure: {exc}") from exc

        if width <= 0 or height <= 0:
            raise ValueError("frame_width and frame_height must be positive")
        if (line is None) != (approach_side is None):
            raise ValueError("stop_line and approach_side must either both be configured or both be omitted")
        if line is not None and (
            len(line) != 2 or any(len(point) != 2 for point in line) or line[0] == line[1]
        ):
            raise ValueError("stop_line must contain two distinct [x, y] pixel coordinates")
        if line is not None and any(not (0 <= x <= width and 0 <= y <= height) for x, y in line):
            raise ValueError("stop_line coordinates must lie within the configured frame")
        if approach_side is not None and approach_side not in (-1, 1):
            raise ValueError("approach_side must be -1 or 1")
        for region in regions:
            if len(region) != 4 or not (0 <= region[0] < region[2] <= 1 and 0 <= region[1] < region[3] <= 1):
                raise ValueError("Each traffic-light region must be normalized [x1, y1, x2, y2] within 0..1")
        if cooldown < 0:
            raise ValueError("cooldown_seconds cannot be negative")
        for interval in intervals:
            if interval.start_seconds < 0 or interval.end_seconds <= interval.start_seconds:
                raise ValueError("Signal intervals need start >= 0 and end > start")
            if interval.state not in {"red", "amber", "green", "unknown"}:
                raise ValueError("Signal state must be red, amber, green, or unknown")
        ordered = sorted(intervals, key=lambda item: item.start_seconds)
        if any(current.start_seconds < previous.end_seconds for previous, current in zip(ordered, ordered[1:])):
            raise ValueError("Signal-state intervals must not overlap")
        return cls(
            width,
            height,
            regions,
            (line[0], line[1]) if line is not None else None,
            approach_side,
            intervals,
            cooldown,
            str(unsupported_reason) if unsupported_reason else None,
        )

    @property
    def unsupported_reasons(self) -> tuple[str, ...]:
        reasons = []
        if not self.traffic_light_regions:
            reasons.append("no traffic-light ROI is configured for a specific movement")
        if self.stop_line is None or self.approach_side is None:
            reasons.append("stop-line segment and crossing direction are unconfigured")
        if not self.signal_intervals:
            reasons.append("no manually reviewed signal-state intervals are configured")
        if self.unsupported_reason:
            reasons.append(self.unsupported_reason)
        return tuple(reasons)

    @property
    def is_supported(self) -> bool:
        return not self.unsupported_reasons

    def state_at(self, timestamp_seconds: float) -> str:
        """Return red/amber/green only for a covered manual interval; else unknown."""
        for interval in self.signal_intervals:
            if interval.start_seconds <= timestamp_seconds < interval.end_seconds:
                return interval.state
        return "unknown"

    def state_during(self, start_seconds: float, end_seconds: float) -> str:
        """Require one reviewed interval to cover the entire sampled crossing."""
        for interval in self.signal_intervals:
            if interval.start_seconds <= start_seconds and end_seconds < interval.end_seconds:
                return interval.state
        return "unknown"


class RedLightRule:
    """Detect one-way tracked-vehicle crossings while a reviewed state is red."""

    def __init__(self, config: RedLightConfig) -> None:
        self.config = config
        self.previous: dict[int, tuple[Point, str, float]] = {}
        self.last_event: dict[int, float] = {}

    def _signed_side(self, point: Point) -> float:
        if self.config.stop_line is None:
            return 0.0
        (x1, y1), (x2, y2) = self.config.stop_line
        return (x2 - x1) * (point[1] - y1) - (y2 - y1) * (point[0] - x1)

    def _crosses_segment(self, previous: Point, current: Point) -> bool:
        if self.config.stop_line is None or self.config.approach_side is None:
            return False
        line_a, line_b = self.config.stop_line
        d1 = self._signed_side(previous)
        d2 = self._signed_side(current)
        side = self.config.approach_side
        if d1 * side <= 0 or d2 * side >= 0:
            return False
        # Confirm intersection lies on the finite configured line, not its extension.
        vehicle_dx, vehicle_dy = current[0] - previous[0], current[1] - previous[1]
        line_dx, line_dy = line_b[0] - line_a[0], line_b[1] - line_a[1]
        denominator = vehicle_dx * line_dy - vehicle_dy * line_dx
        if abs(denominator) < 1e-9:
            return False
        t = ((line_a[0] - previous[0]) * line_dy - (line_a[1] - previous[1]) * line_dx) / denominator
        u = ((line_a[0] - previous[0]) * vehicle_dy - (line_a[1] - previous[1]) * vehicle_dx) / denominator
        return 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0

    def update(self, vehicles: list[Any], timestamp_seconds: float) -> list[RedLightCandidate]:
        if not self.config.is_supported:
            return []
        candidates: list[RedLightCandidate] = []
        current_ids: set[int] = set()
        for vehicle in vehicles:
            track_id = vehicle.track_id
            if track_id is None:
                continue
            current_ids.add(track_id)
            x1, y1, x2, y2 = vehicle.xyxy
            center = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
            previous = self.previous.get(track_id)
            if previous and previous[1] == vehicle.name and self._crosses_segment(previous[0], center):
                state = self.config.state_during(previous[2], timestamp_seconds)
                last = self.last_event.get(track_id, float("-inf"))
                if state == "red" and timestamp_seconds - last > self.config.cooldown_seconds:
                    candidates.append(
                        RedLightCandidate(track_id, vehicle.name, vehicle.confidence, timestamp_seconds,
                                          state, previous[0], center)
                    )
                    self.last_event[track_id] = timestamp_seconds
            self.previous[track_id] = (center, vehicle.name, timestamp_seconds)

        # Dropping lost IDs avoids stale position jumps if a tracker later reuses an ID.
        for track_id in set(self.previous) - current_ids:
            self.previous.pop(track_id, None)
        return candidates


def candidate_record(candidate: RedLightCandidate, event_id: str, evidence_image: str, video_filename: str) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "video_filename": video_filename,
        "video_timestamp_seconds": round(candidate.timestamp_seconds, 3),
        "video_timestamp": _format_time(candidate.timestamp_seconds),
        "tracking_id": candidate.track_id,
        "vehicle_class": candidate.vehicle_class,
        "candidate_type": "vehicle_crossed_configured_stop_line_during_reviewed_red_interval",
        "review_status": "NEEDS_REVIEW",
        "signal_state_evidence": "manually reviewed time interval; not inferred by the model",
        "signal_state": candidate.signal_state,
        "stop_line_crossing": {
            "previous_center_px": list(candidate.previous_center),
            "current_center_px": list(candidate.current_center),
        },
        "detection_evidence_score": round(candidate.confidence, 4),
        "detection_evidence_score_definition": "Vehicle detector confidence only; not a probability of a traffic violation.",
        "evidence_note": "A tracked vehicle crossed the configured finite stop line during an explicitly reviewed red interval. This remains a review candidate, not a confirmed violation.",
        "evidence_image": evidence_image,
    }


def _format_time(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"
