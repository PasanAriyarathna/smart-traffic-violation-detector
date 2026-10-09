"""Video inference and conservative violation-review candidate generation.

This module does not make confirmed legal or traffic-violation decisions.
Its helmet rule only flags a tracked person/motorcycle association for review
when no helmet detection overlaps the person's approximate head region.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from dataclasses import dataclass, replace
import json
import math
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
try:  # Support both `python model/violation_detector.py` and package imports.
    from .rules.red_light import RedLightConfig, RedLightRule, candidate_record
    from .rules.overtaking import (
        OvertakingConfig,
        OvertakingRule,
        candidate_record as overtaking_candidate_record,
    )
except ImportError:
    from rules.red_light import RedLightConfig, RedLightRule, candidate_record
    from rules.overtaking import (
        OvertakingConfig,
        OvertakingRule,
        candidate_record as overtaking_candidate_record,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS = (
    PROJECT_ROOT
    / "runs"
    / "detect"
    / "runs"
    / "traffic_violation"
    / "yolov8n_v1"
    / "weights"
    / "best.pt"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "runs" / "violation_detector"
SUPPORTED_VIDEO_EXTENSIONS = {
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".webm",
}


@dataclass(frozen=True)
class Detection:
    """One YOLO detection with optional tracker identity."""

    class_id: int
    name: str
    confidence: float
    xyxy: tuple[float, float, float, float]
    track_id: int | None


@dataclass(frozen=True)
class ReviewCandidate:
    """A geometrically plausible, unconfirmed person/motorcycle association."""

    person: Detection
    motorcycle: Detection
    association_score: float
    supporting_frames: int = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run YOLO tracking on a traffic video and write annotated video "
            "plus conservative review candidates."
        )
    )
    parser.add_argument("--source", required=True, help="Input traffic video path")
    parser.add_argument(
        "--weights",
        default=str(DEFAULT_WEIGHTS),
        help=f"YOLO weights (default: {DEFAULT_WEIGHTS})",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Parent folder for a unique output run directory",
    )
    parser.add_argument("--output-video", help="Optional explicit annotated-video path")
    parser.add_argument("--evidence-dir", help="Optional explicit evidence-image folder")
    parser.add_argument("--records", help="Optional explicit JSONL event-record path")
    parser.add_argument(
        "--red-light-config",
        help="Optional fixed-camera JSON config with stop line and manually reviewed signal-state intervals",
    )
    parser.add_argument(
        "--overtaking-config",
        help="Optional fixed-camera JSON config with lane polygons, travel direction, and prohibited-passing zones",
    )
    parser.add_argument(
        "--conf", type=float, default=0.25, help="YOLO detection confidence threshold"
    )
    parser.add_argument(
        "--rule-conf",
        type=float,
        default=0.45,
        help="Minimum person/motorcycle confidence for a review candidate",
    )
    parser.add_argument(
        "--tracker",
        default="bytetrack.yaml",
        help="Ultralytics tracker configuration (default: bytetrack.yaml)",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=10.0,
        help="Seconds without a candidate before the rider's event can be recorded again",
    )
    parser.add_argument(
        "--association-frames",
        type=int,
        default=3,
        help="Same tracked person/bike pair must qualify this many frames before recording",
    )
    parser.add_argument(
        "--association-window",
        type=float,
        default=1.0,
        help="Time window for collecting association-support frames",
    )
    parser.add_argument(
        "--association-margin",
        type=float,
        default=0.12,
        help="Minimum score gap over the next motorcycle association; otherwise skip as ambiguous",
    )
    parser.add_argument(
        "--association-min-score",
        type=float,
        default=0.30,
        help="Minimum geometric association score for a review candidate",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        help="Optional frame limit, useful for a short smoke test",
    )
    return parser


def _validate_arguments(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not 0.0 < args.conf <= 1.0:
        parser.error("--conf must be greater than 0 and at most 1")
    if not 0.0 < args.rule_conf <= 1.0:
        parser.error("--rule-conf must be greater than 0 and at most 1")
    if args.cooldown < 0.0:
        parser.error("--cooldown cannot be negative")
    if args.association_frames < 1:
        parser.error("--association-frames must be at least 1")
    if args.association_window <= 0.0:
        parser.error("--association-window must be greater than 0")
    if not 0.0 <= args.association_margin <= 1.0:
        parser.error("--association-margin must be between 0 and 1")
    if not 0.0 <= args.association_min_score <= 1.0:
        parser.error("--association-min-score must be between 0 and 1")
    if args.max_frames is not None and args.max_frames < 1:
        parser.error("--max-frames must be at least 1")


def _load_yolo(weights_path: Path) -> Any:
    if not weights_path.is_file():
        raise FileNotFoundError(f"Model weights not found: {weights_path}")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError(
            "Ultralytics is unavailable in this Python environment. "
            "Activate the project environment and install the project's chosen dependencies."
        ) from exc

    try:
        model = YOLO(str(weights_path))
    except Exception as exc:  # Ultralytics can raise several load/format exceptions.
        raise RuntimeError(f"Could not load YOLO weights at {weights_path}: {exc}") from exc
    if getattr(model, "task", None) != "detect":
        raise RuntimeError(
            f"Expected an object-detection model, got task={getattr(model, 'task', None)!r}."
        )
    return model


def _class_name(names: Any, class_id: int) -> str:
    try:
        return str(names[class_id])
    except (KeyError, IndexError, TypeError):
        return str(class_id)


def _extract_detections(result: Any, names: Any) -> list[Detection]:
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    coordinates = boxes.xyxy.cpu().tolist()
    class_ids = boxes.cls.cpu().tolist()
    confidences = boxes.conf.cpu().tolist()
    raw_ids = boxes.id
    track_ids = raw_ids.int().cpu().tolist() if raw_ids is not None else [None] * len(coordinates)

    detections: list[Detection] = []
    for box, raw_class_id, confidence, raw_track_id in zip(
        coordinates, class_ids, confidences, track_ids
    ):
        class_id = int(raw_class_id)
        track_id = int(raw_track_id) if raw_track_id is not None else None
        detections.append(
            Detection(
                class_id=class_id,
                name=_class_name(names, class_id),
                confidence=float(confidence),
                xyxy=tuple(float(value) for value in box),
                track_id=track_id,
            )
        )
    return detections


def _box_area(box: tuple[float, float, float, float]) -> float:
    x1, y1, x2, y2 = box
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _intersection_area(
    first: tuple[float, float, float, float], second: tuple[float, float, float, float]
) -> float:
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[2], second[2])
    y2 = min(first[3], second[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _suppress_duplicate_detections(
    detections: list[Detection], iou_threshold: float = 0.84
) -> list[Detection]:
    """Drop near-identical same-class boxes left after tracking/NMS."""
    kept: list[Detection] = []
    for detection in sorted(detections, key=lambda item: item.confidence, reverse=True):
        area = _box_area(detection.xyxy)
        duplicate = False
        for previous in kept:
            if previous.class_id != detection.class_id:
                continue
            previous_area = _box_area(previous.xyxy)
            intersection = _intersection_area(previous.xyxy, detection.xyxy)
            union = area + previous_area - intersection
            iou = intersection / union if union > 0.0 else 0.0
            containment = intersection / min(area, previous_area) if min(area, previous_area) else 0.0
            if iou >= iou_threshold or containment >= 0.94:
                duplicate = True
                break
        if not duplicate:
            kept.append(detection)
    return kept


def _center(box: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def _person_motorcycle_association_score(
    person: Detection, motorcycle: Detection, frame_height: int
) -> float | None:
    """Score rider-like geometry; this is not a probability or a violation score."""
    px1, py1, px2, py2 = person.xyxy
    mx1, my1, mx2, my2 = motorcycle.xyxy
    person_width = px2 - px1
    person_height = py2 - py1
    motorcycle_width = mx2 - mx1
    motorcycle_height = my2 - my1
    if min(person_width, person_height, motorcycle_width, motorcycle_height) <= 0.0:
        return None

    person_center_x, _ = _center(person.xyxy)
    motorcycle_center_x, _ = _center(motorcycle.xyxy)
    horizontal_offset = abs(person_center_x - motorcycle_center_x) / motorcycle_width
    if horizontal_offset > 0.75:
        return None

    # The rider's lower-body anchor should be near the motorcycle's vertical
    # extent. This rejects many side-by-side box overlaps without assuming one
    # fixed camera perspective.
    lower_body_anchor_y = py1 + 0.76 * person_height
    vertical_padding = max(0.10 * motorcycle_height, 0.015 * frame_height)
    if not (my1 - vertical_padding <= lower_body_anchor_y <= my2 + 0.12 * person_height):
        return None

    person_area = max(1.0, person_width * person_height)
    overlap_ratio = _intersection_area(person.xyxy, motorcycle.xyxy) / person_area
    lower_person_region = (px1, py1 + 0.55 * person_height, px2, py2)
    lower_region_area = max(1.0, _box_area(lower_person_region))
    lower_overlap = _intersection_area(lower_person_region, motorcycle.xyxy) / lower_region_area
    horizontal_intersection = max(0.0, min(px2, mx2) - max(px1, mx1))
    horizontal_overlap = horizontal_intersection / max(1.0, min(person_width, motorcycle_width))
    vertical_gap = max(0.0, my1 - py2, py1 - my2)
    allowed_gap = max(0.025 * frame_height, 0.16 * motorcycle_height)
    if lower_overlap < 0.08 and (horizontal_overlap < 0.25 or vertical_gap > allowed_gap):
        return None

    horizontal_score = max(0.0, 1.0 - horizontal_offset / 0.75)
    overlap_score = min(1.0, max(lower_overlap / 0.40, horizontal_overlap * 0.65))
    vertical_score = max(0.0, 1.0 - vertical_gap / max(1.0, allowed_gap))
    return 0.40 * horizontal_score + 0.40 * overlap_score + 0.20 * vertical_score


def _helmet_overlaps_head(person: Detection, helmets: list[Detection]) -> bool:
    x1, y1, x2, y2 = person.xyxy
    person_width = max(1.0, x2 - x1)
    person_height = max(1.0, y2 - y1)
    # Extend above and to the sides for camera angle, partial occlusion, and
    # slightly loose person boxes. This intentionally favors suppressing a
    # false review candidate over calling a helmet absent.
    head_region = (
        x1 - 0.22 * person_width,
        y1 - 0.16 * person_height,
        x2 + 0.22 * person_width,
        y1 + 0.48 * person_height,
    )
    for helmet in helmets:
        helmet_x, helmet_y = _center(helmet.xyxy)
        helmet_area = max(1.0, _box_area(helmet.xyxy))
        overlap_ratio = _intersection_area(head_region, helmet.xyxy) / helmet_area
        if head_region[0] <= helmet_x <= head_region[2] and head_region[1] <= helmet_y <= head_region[3]:
            return True
        if overlap_ratio >= 0.15:
            return True
    return False


def _find_helmet_review_candidates(
    detections: list[Detection],
    rule_confidence: float,
    frame_height: int,
    association_margin: float,
    minimum_association_score: float,
) -> tuple[list[ReviewCandidate], set[int]]:
    people = [d for d in detections if d.name == "person" and d.confidence >= rule_confidence]
    motorcycles = [
        d for d in detections if d.name == "motorcycle" and d.confidence >= rule_confidence
    ]
    helmets = [d for d in detections if d.name == "helmet" and d.confidence >= rule_confidence]

    candidates: list[ReviewCandidate] = []
    reset_person_tracks: set[int] = set()
    for person in people:
        if _helmet_overlaps_head(person, helmets):
            if person.track_id is not None:
                reset_person_tracks.add(person.track_id)
            continue

        scored = [
            (score, motorcycle)
            for motorcycle in motorcycles
            if (score := _person_motorcycle_association_score(person, motorcycle, frame_height))
            is not None
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            continue

        if len(scored) > 1 and scored[0][0] - scored[1][0] < association_margin:
            if person.track_id is not None:
                reset_person_tracks.add(person.track_id)
            continue

        association_score, motorcycle = scored[0]
        if association_score < minimum_association_score:
            continue
        # Temporal confirmation needs stable tracker identities. If either ID
        # is unavailable, skip rather than manufacture a persistent association.
        if person.track_id is None or motorcycle.track_id is None:
            if person.track_id is not None:
                reset_person_tracks.add(person.track_id)
            continue
        candidates.append(ReviewCandidate(person, motorcycle, association_score))
    return candidates, reset_person_tracks


class CandidateStabilizer:
    """Require repeated same-track evidence and deduplicate one incident per rider."""

    def __init__(self, min_frames: int, window_seconds: float, inactivity_seconds: float) -> None:
        self.min_frames = min_frames
        self.window_seconds = window_seconds
        self.inactivity_seconds = inactivity_seconds
        self.history: dict[tuple[int, int], deque[tuple[float, ReviewCandidate]]] = defaultdict(deque)
        self.active_riders: dict[int, float] = {}

    def _clear_rider_history(self, person_track_id: int) -> None:
        for pair in [pair for pair in self.history if pair[0] == person_track_id]:
            self.history.pop(pair, None)

    def update(
        self,
        candidates: list[ReviewCandidate],
        reset_person_tracks: set[int],
        video_seconds: float,
    ) -> list[ReviewCandidate]:
        for person_track_id in reset_person_tracks:
            self._clear_rider_history(person_track_id)

        expired = [
            person_track_id
            for person_track_id, last_seen in self.active_riders.items()
            if video_seconds - last_seen > self.inactivity_seconds
        ]
        for person_track_id in expired:
            self.active_riders.pop(person_track_id, None)
            self._clear_rider_history(person_track_id)

        ready: list[ReviewCandidate] = []
        for candidate in candidates:
            person_track_id = candidate.person.track_id
            motorcycle_track_id = candidate.motorcycle.track_id
            if person_track_id is None or motorcycle_track_id is None:
                continue

            if person_track_id in self.active_riders:
                self.active_riders[person_track_id] = video_seconds
                continue

            key = (person_track_id, motorcycle_track_id)
            observations = self.history[key]
            while observations and video_seconds - observations[0][0] > self.window_seconds:
                observations.popleft()
            if not observations or observations[-1][0] != video_seconds:
                observations.append((video_seconds, candidate))
            if len(observations) >= self.min_frames:
                ready.append(replace(candidate, supporting_frames=len(observations)))
                self.active_riders[person_track_id] = video_seconds
                self._clear_rider_history(person_track_id)
        return ready


def _draw_detections(
    frame: Any,
    detections: list[Detection],
    candidates: list[ReviewCandidate],
    highlighted_detections: list[Detection] | None = None,
) -> Any:
    # The model detects plate regions but does not read plate text. Blur regions
    # before writing any exported video or evidence image to reduce exposure.
    frame_height, frame_width = frame.shape[:2]
    for detection in detections:
        if detection.name != "number_plate":
            continue
        raw_x1, raw_y1, raw_x2, raw_y2 = detection.xyxy
        x1 = max(0, min(frame_width, int(round(raw_x1))))
        y1 = max(0, min(frame_height, int(round(raw_y1))))
        x2 = max(0, min(frame_width, int(round(raw_x2))))
        y2 = max(0, min(frame_height, int(round(raw_y2))))
        if x2 <= x1 or y2 <= y1:
            continue
        region = frame[y1:y2, x1:x2]
        kernel_size = max(9, (min(x2 - x1, y2 - y1) // 2) * 2 + 1)
        frame[y1:y2, x1:x2] = cv2.GaussianBlur(region, (kernel_size, kernel_size), 0)

    candidate_detections = {
        id(detection)
        for candidate in candidates
        for detection in (candidate.person, candidate.motorcycle)
    }
    candidate_detections.update(id(detection) for detection in (highlighted_detections or []))
    palette = (
        (255, 170, 0),
        (0, 190, 0),
        (200, 0, 200),
        (255, 120, 80),
        (160, 200, 0),
        (0, 180, 220),
        (220, 120, 0),
        (180, 180, 180),
    )

    # Draw boxes first; labels are laid out afterward so their placements can
    # account for all detected objects and previously placed labels.
    for detection in detections:
        x1 = max(0, min(frame_width - 1, int(round(detection.xyxy[0]))))
        y1 = max(0, min(frame_height - 1, int(round(detection.xyxy[1]))))
        x2 = max(0, min(frame_width - 1, int(round(detection.xyxy[2]))))
        y2 = max(0, min(frame_height - 1, int(round(detection.xyxy[3]))))
        if x2 <= x1 or y2 <= y1:
            continue
        color = (
            (0, 145, 255)
            if id(detection) in candidate_detections
            else palette[detection.class_id % len(palette)]
        )
        thickness = max(1, min(2, round(min(frame_width, frame_height) / 720)))
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    occupied_labels: list[tuple[int, int, int, int]] = []
    label_order = sorted(
        detections,
        key=lambda item: (id(item) in candidate_detections, item.confidence),
        reverse=True,
    )
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.42
    text_thickness = 1
    for detection in label_order:
        x1, y1, x2, y2 = (int(round(value)) for value in detection.xyxy)
        if x2 <= x1 or y2 <= y1:
            continue
        color = (
            (0, 145, 255)
            if id(detection) in candidate_detections
            else palette[detection.class_id % len(palette)]
        )
        label = f"{detection.name} {detection.confidence:.2f}"
        if detection.track_id is not None:
            label += f" #{detection.track_id}"
        (text_width, text_height), baseline = cv2.getTextSize(
            label, font, font_scale, text_thickness
        )
        label_width = text_width + 8
        label_height = text_height + baseline + 6
        anchors = (
            (x1, y1 - label_height - 2),
            (x2 - label_width, y1 - label_height - 2),
            (x1, y2 + 2),
            (x2 - label_width, y2 + 2),
            (x1 - label_width - 2, y1),
            (x2 + 2, y1),
            (x1, y1 + 2),
        )

        best_rect: tuple[int, int, int, int] | None = None
        best_score = float("inf")
        detection_area = (x1, y1, x2, y2)
        for preference, (left, top) in enumerate(anchors):
            left = max(0, min(max(0, frame_width - label_width), left))
            top = max(0, min(max(0, frame_height - label_height), top))
            rect = (left, top, left + label_width, top + label_height)
            label_area = max(1.0, float(label_width * label_height))
            previous_overlap = sum(
                _intersection_area(rect, occupied) / label_area
                for occupied in occupied_labels
            )
            object_overlap = 0.0
            for other in detections:
                other_box = tuple(int(round(value)) for value in other.xyxy)
                ratio = _intersection_area(rect, other_box) / label_area
                object_overlap += ratio * (0.25 if other is detection else 1.0)
            score = 100.0 * previous_overlap + 8.0 * object_overlap + preference * 0.01
            if score < best_score:
                best_score = score
                best_rect = rect

        if best_rect is None:
            continue
        left, top, right, bottom = best_rect
        occupied_labels.append(best_rect)
        cv2.rectangle(frame, (left, top), (right, bottom), color, -1)
        cv2.putText(
            frame,
            label,
            (left + 4, top + text_height + 3),
            font,
            font_scale,
            (255, 255, 255),
            text_thickness,
            cv2.LINE_AA,
        )
    return frame


def _draw_red_light_configuration(frame: Any, config: RedLightConfig) -> None:
    """Show configured manual-review regions and stop line in the output."""
    height, width = frame.shape[:2]
    for x1, y1, x2, y2 in config.traffic_light_regions:
        rect = (round(x1 * width), round(y1 * height), round(x2 * width), round(y2 * height))
        cv2.rectangle(frame, rect[:2], rect[2:], (255, 255, 0), 2)
        cv2.putText(frame, "signal ROI (manual state)", (rect[0], max(16, rect[1] - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1, cv2.LINE_AA)
    if config.stop_line is not None:
        start, end = config.stop_line
        cv2.line(frame, tuple(round(v) for v in start), tuple(round(v) for v in end), (255, 255, 0), 2)
        cv2.putText(frame, "configured stop line", (round(start[0]), max(16, round(start[1]) - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1, cv2.LINE_AA)


def _record_red_light_candidate(
    record_file: Any,
    evidence_dir: Path,
    annotated_frame: Any,
    source_path: Path,
    candidate: Any,
) -> bool:
    event_id = str(uuid.uuid4())
    evidence_path = evidence_dir / f"{event_id}.jpg"
    if not cv2.imwrite(str(evidence_path), annotated_frame):
        print(f"WARNING: Could not write evidence image: {evidence_path}", file=sys.stderr)
        return False
    event = candidate_record(
        candidate, event_id, str(evidence_path.resolve()), source_path.name
    )
    record_file.write(json.dumps(event, ensure_ascii=False) + "\n")
    record_file.flush()
    return True


def _draw_overtaking_configuration(frame: Any, config: OvertakingConfig) -> None:
    """Overlay configured lane and prohibition polygons for visual checking."""
    height, width = frame.shape[:2]
    for polygon, color, label in (
        (config.travel_lane, (255, 200, 0), "travel lane"),
        (config.passing_lane, (0, 220, 255), "passing lane"),
    ):
        if polygon:
            points = [(round(x * width), round(y * height)) for x, y in polygon]
            cv2.polylines(frame, [np.array(points, dtype="int32")], True, color, 2)
            cv2.putText(frame, label, points[0], cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    for index, polygon in enumerate(config.prohibited_zones):
        points = [(round(x * width), round(y * height)) for x, y in polygon]
        cv2.polylines(frame, [np.array(points, dtype="int32")], True, (0, 0, 255), 2)
        cv2.putText(frame, f"configured no-pass zone {index}", points[0],
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)


def _record_overtaking_candidate(
    record_file: Any,
    evidence_dir: Path,
    annotated_frame: Any,
    source_path: Path,
    candidate: Any,
) -> bool:
    event_id = str(uuid.uuid4())
    evidence_path = evidence_dir / f"{event_id}.jpg"
    if not cv2.imwrite(str(evidence_path), annotated_frame):
        print(f"WARNING: Could not write evidence image: {evidence_path}", file=sys.stderr)
        return False
    event = overtaking_candidate_record(
        candidate, event_id, str(evidence_path.resolve()), source_path.name
    )
    record_file.write(json.dumps(event, ensure_ascii=False) + "\n")
    record_file.flush()
    return True


def _new_run_directory(output_root: Path, source_stem: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{source_stem}_{timestamp}"
    for suffix in range(1000):
        name = base_name if suffix == 0 else f"{base_name}_{suffix:03d}"
        candidate = output_root / name
        try:
            candidate.mkdir(exist_ok=False)
            return candidate
        except FileExistsError:
            continue
    raise FileExistsError(f"Could not allocate a unique output directory in {output_root}")


def _resolve_output_paths(args: argparse.Namespace, source_path: Path) -> tuple[Path, Path, Path]:
    needs_run_directory = not (args.output_video and args.evidence_dir and args.records)
    run_directory = (
        _new_run_directory(Path(args.output_dir).expanduser(), source_path.stem)
        if needs_run_directory
        else None
    )

    output_video = (
        Path(args.output_video).expanduser()
        if args.output_video
        else run_directory / "annotated.mp4"
    )
    evidence_dir = (
        Path(args.evidence_dir).expanduser()
        if args.evidence_dir
        else run_directory / "evidence"
    )
    records_path = (
        Path(args.records).expanduser()
        if args.records
        else run_directory / "events.jsonl"
    )

    if output_video.exists():
        raise FileExistsError(f"Output video already exists; choose another path: {output_video}")
    if records_path.exists():
        raise FileExistsError(f"Record file already exists; choose another path: {records_path}")
    if evidence_dir.exists():
        raise FileExistsError(f"Evidence directory already exists; choose another path: {evidence_dir}")

    resolved_video = output_video.resolve()
    resolved_records = records_path.resolve()
    resolved_evidence = evidence_dir.resolve()
    if resolved_video == resolved_records:
        raise ValueError("Output video and record file must use distinct paths")
    for file_path in (resolved_video, resolved_records):
        if (
            file_path == resolved_evidence
            or resolved_evidence in file_path.parents
            or file_path in resolved_evidence.parents
        ):
            raise ValueError("Evidence directory must not overlap an output file path")
    if resolved_video in resolved_records.parents or resolved_records in resolved_video.parents:
        raise ValueError("Output video and record file paths must not overlap")

    output_video.parent.mkdir(parents=True, exist_ok=True)
    records_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=False)
    return output_video, evidence_dir, records_path


def _format_video_time(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"


def _record_candidate(
    record_file: Any,
    evidence_dir: Path,
    annotated_frame: Any,
    source_path: Path,
    video_seconds: float,
    candidate: ReviewCandidate,
) -> bool:
    person = candidate.person
    motorcycle = candidate.motorcycle
    event_id = str(uuid.uuid4())
    evidence_path = evidence_dir / f"{event_id}.jpg"
    if not cv2.imwrite(str(evidence_path), annotated_frame):
        print(f"WARNING: Could not write evidence image: {evidence_path}", file=sys.stderr)
        return False

    event = {
        "event_id": event_id,
        "video_filename": source_path.name,
        "video_timestamp_seconds": round(video_seconds, 3),
        "video_timestamp": _format_video_time(video_seconds),
        "tracking_id": person.track_id,
        "associated_motorcycle_tracking_id": motorcycle.track_id,
        "candidate_type": "helmet_not_observed_on_associated_rider",
        "review_status": "NEEDS_REVIEW",
        "detection_evidence_score": round(min(person.confidence, motorcycle.confidence), 4),
        "detection_evidence_score_definition": (
            "Minimum of the person and motorcycle detector confidences. It is not calibrated "
            "as a violation probability and does not measure legal or violation certainty."
        ),
        "association_score": round(candidate.association_score, 4),
        "association_score_definition": (
            "Uncalibrated 0-1 geometric heuristic combining horizontal alignment, lower-body "
            "overlap, and vertical proximity. It measures association plausibility only."
        ),
        "temporal_supporting_frames": candidate.supporting_frames,
        "evidence_note": (
            f"The person/motorcycle association met the geometric rule in "
            f"{candidate.supporting_frames} nearby frames, but no helmet detection matched "
            "the expanded approximate head region. Detection or association can be wrong; "
            "this is not proof of a violation. Review the video context."
        ),
        "evidence_image": str(evidence_path.resolve()),
    }
    record_file.write(json.dumps(event, ensure_ascii=False) + "\n")
    record_file.flush()
    return True


def run_detector(args: argparse.Namespace) -> int:
    source_path = Path(args.source).expanduser()
    weights_path = Path(args.weights).expanduser()
    if not source_path.is_file():
        raise FileNotFoundError(f"Input video not found: {source_path}")
    if source_path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
        raise ValueError(
            f"Unsupported video extension {source_path.suffix!r}; "
            f"supported extensions: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}"
        )

    model = _load_yolo(weights_path)
    names = model.names
    required_names = {"person", "motorcycle", "helmet"}
    available_names = {str(name) for name in names.values()} if isinstance(names, dict) else set(names)
    missing_names = required_names - available_names
    if missing_names:
        print(
            "WARNING: Helmet review candidate rule is disabled; model is missing classes: "
            + ", ".join(sorted(missing_names)),
            file=sys.stderr,
        )

    cap = cv2.VideoCapture(str(source_path))
    writer = None
    try:
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video or codec is unsupported: {source_path}")

        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if not math.isfinite(fps) or fps <= 0.0:
            fps = 25.0
            print("WARNING: Video FPS unavailable; using 25 FPS for output timing.", file=sys.stderr)

        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError(f"Video opened but contains no decodable frames: {source_path}")

        frame_height, frame_width = frame.shape[:2]
        red_light_config = None
        red_light_rule = None
        if args.red_light_config:
            red_light_config = RedLightConfig.from_file(args.red_light_config)
            if (red_light_config.frame_width, red_light_config.frame_height) != (frame_width, frame_height):
                raise ValueError(
                    "Red-light config frame dimensions do not match the source video "
                    f"({red_light_config.frame_width}x{red_light_config.frame_height} vs "
                    f"{frame_width}x{frame_height}); configure coordinates for this fixed view."
                )
            red_light_rule = RedLightRule(red_light_config)
            if not red_light_config.is_supported:
                print(
                    "WARNING: Red-light candidate generation is disabled: "
                    + "; ".join(red_light_config.unsupported_reasons)
                    + ". No red-light candidates will be created.",
                    file=sys.stderr,
                )
            else:
                print(
                    "Red-light signal states are read only from the manually reviewed config; "
                    "the model does not recognize signal colors.",
                    file=sys.stderr,
                )
        overtaking_config = None
        overtaking_rule = None
        if args.overtaking_config:
            overtaking_config = OvertakingConfig.from_file(args.overtaking_config)
            if (overtaking_config.frame_width, overtaking_config.frame_height) != (frame_width, frame_height):
                raise ValueError(
                    "Overtaking config frame dimensions do not match the source video "
                    f"({overtaking_config.frame_width}x{overtaking_config.frame_height} vs "
                    f"{frame_width}x{frame_height}); configure geometry for this fixed view."
                )
            overtaking_rule = OvertakingRule(overtaking_config)
            if not overtaking_config.is_supported:
                print(
                    "WARNING: Overtaking candidate generation is disabled: "
                    + "; ".join(overtaking_config.unsupported_reasons)
                    + ". No overtaking candidates will be created.",
                    file=sys.stderr,
                )
            else:
                print(
                    "Overtaking candidates require a configured trajectory sequence and "
                    "prohibition zone; legal status remains undetermined.",
                    file=sys.stderr,
                )
        output_video, evidence_dir, records_path = _resolve_output_paths(args, source_path)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(output_video), fourcc, fps, (frame_width, frame_height)
        )
        if not writer.isOpened():
            raise RuntimeError(f"Could not open video writer for output: {output_video}")

        frame_index = 0
        records_written = 0
        stabilizer = CandidateStabilizer(
            min_frames=args.association_frames,
            window_seconds=args.association_window,
            inactivity_seconds=args.cooldown,
        )
        with records_path.open("x", encoding="utf-8") as record_file:
            while True:
                predictions = model.track(
                    frame,
                    persist=True,
                    tracker=args.tracker,
                    conf=args.conf,
                    verbose=False,
                )
                result = predictions[0] if predictions else None
                detections = _suppress_duplicate_detections(
                    _extract_detections(result, names) if result is not None else []
                )
                candidates, reset_person_tracks = (
                    _find_helmet_review_candidates(
                        detections,
                        args.rule_conf,
                        frame_height,
                        args.association_margin,
                        args.association_min_score,
                    )
                    if not missing_names
                    else ([], set())
                )
                video_seconds = frame_index / fps
                ready_candidates = stabilizer.update(
                    candidates, reset_person_tracks, video_seconds
                )
                vehicle_detections = [
                    detection for detection in detections
                    if detection.name in {"car", "bus", "truck", "three_wheeler", "motorcycle"}
                ]
                red_light_candidates = (
                    red_light_rule.update(vehicle_detections, video_seconds)
                    if red_light_rule is not None
                    else []
                )
                overtaking_candidates = (
                    overtaking_rule.update(vehicle_detections, video_seconds)
                    if overtaking_rule is not None
                    else []
                )
                red_candidate_ids = {candidate.track_id for candidate in red_light_candidates}
                overtaking_candidate_ids = {
                    track_id
                    for candidate in overtaking_candidates
                    for track_id in (candidate.passing_track_id, candidate.passed_track_id)
                }
                red_candidate_detections = [
                    detection for detection in vehicle_detections
                    if detection.track_id in red_candidate_ids | overtaking_candidate_ids
                ]
                annotated = _draw_detections(
                    frame.copy(), detections, candidates, red_candidate_detections
                )
                if red_light_config is not None:
                    _draw_red_light_configuration(annotated, red_light_config)
                if overtaking_config is not None:
                    _draw_overtaking_configuration(annotated, overtaking_config)

                for candidate in ready_candidates:
                    if _record_candidate(
                        record_file,
                        evidence_dir,
                        annotated,
                        source_path,
                        video_seconds,
                        candidate,
                    ):
                        records_written += 1

                for candidate in red_light_candidates:
                    if _record_red_light_candidate(
                        record_file, evidence_dir, annotated, source_path, candidate
                    ):
                        records_written += 1

                for candidate in overtaking_candidates:
                    if _record_overtaking_candidate(
                        record_file, evidence_dir, annotated, source_path, candidate
                    ):
                        records_written += 1

                writer.write(annotated)
                frame_index += 1
                if args.max_frames is not None and frame_index >= args.max_frames:
                    break
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
    finally:
        cap.release()
        if writer is not None:
            writer.release()

    print(f"Processed frames: {frame_index}")
    print(f"Review candidates recorded: {records_written}")
    print(f"Annotated video: {output_video.resolve()}")
    print(f"JSONL records: {records_path.resolve()}")
    print(f"Evidence images: {evidence_dir.resolve()}")
    print("No candidate is a confirmed traffic violation.")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    _validate_arguments(parser, args)
    try:
        return run_detector(args)
    except (FileNotFoundError, FileExistsError, ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # Model/tracker backends may raise library-specific runtime exceptions.
        print(f"ERROR: Inference failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
