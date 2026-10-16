"""Parse and validate human-reviewed red-light signal interval CSV rows."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

VALID_STATES = frozenset({"red", "amber", "green", "unknown"})


@dataclass(frozen=True)
class SignalIntervalRow:
    start_seconds: float
    end_seconds: float
    state: str


def parse_interval_csv(path: Path) -> list[SignalIntervalRow]:
    """Read interval rows from CSV (row_type=interval or legacy complete rows)."""
    rows: list[SignalIntervalRow] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        for line_no, raw in enumerate(reader, start=2):
            row_type = (raw.get("row_type") or "interval").strip().lower()
            if row_type == "observation":
                continue
            if row_type not in ("interval", ""):
                raise ValueError(f"Line {line_no}: invalid row_type {row_type!r}")
            start_s = (raw.get("interval_start_seconds") or "").strip()
            end_s = (raw.get("interval_end_seconds") or "").strip()
            state = (raw.get("reviewer_confirmed_state") or "").strip().lower()
            if not start_s and not end_s and not state:
                continue
            if not start_s or not end_s or not state:
                raise ValueError(
                    f"Line {line_no}: interval rows require interval_start_seconds, "
                    "interval_end_seconds, and reviewer_confirmed_state"
                )
            rows.append(
                SignalIntervalRow(float(start_s), float(end_s), state)
            )
    return rows


def validate_intervals(
    intervals: list[SignalIntervalRow],
    *,
    video_duration_seconds: float | None = None,
    require_full_coverage: bool = False,
) -> list[str]:
    """Return list of error messages; empty means valid."""
    errors: list[str] = []
    if not intervals:
        errors.append("No interval rows found.")
        return errors

    for index, item in enumerate(intervals, start=1):
        if item.start_seconds < 0:
            errors.append(f"Interval {index}: start_seconds must be >= 0")
        if item.end_seconds <= item.start_seconds:
            errors.append(f"Interval {index}: end_seconds must be > start_seconds")
        if item.state not in VALID_STATES:
            errors.append(f"Interval {index}: invalid state {item.state!r}")
        if video_duration_seconds is not None:
            if item.start_seconds > video_duration_seconds:
                errors.append(
                    f"Interval {index}: start {item.start_seconds}s exceeds video duration "
                    f"{video_duration_seconds}s"
                )
            if item.end_seconds > video_duration_seconds + 0.05:
                errors.append(
                    f"Interval {index}: end {item.end_seconds}s exceeds video duration "
                    f"{video_duration_seconds}s"
                )

    ordered = sorted(intervals, key=lambda item: item.start_seconds)
    for previous, current in zip(ordered, ordered[1:]):
        if current.start_seconds < previous.end_seconds:
            errors.append(
                f"Overlapping intervals: [{previous.start_seconds}, {previous.end_seconds}) "
                f"and [{current.start_seconds}, {current.end_seconds})"
            )

    if require_full_coverage and video_duration_seconds is not None and ordered:
        if ordered[0].start_seconds > 0.01:
            errors.append("Intervals do not cover video start (gap before first interval).")
        if ordered[-1].end_seconds < video_duration_seconds - 0.05:
            errors.append("Intervals do not cover video end (gap after last interval).")

    return errors
