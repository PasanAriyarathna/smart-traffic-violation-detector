"""License-plate OCR helpers and Character Error Rate (CER) utilities.

OCR is optional at runtime: install ``easyocr`` to enable reading. Records for
research and blockchain integration should store hashes, not raw plate text.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any


_PLATE_ALLOWED = re.compile(r"[^A-Z0-9]")


def normalize_plate_text(text: str) -> str:
    """Normalize OCR output for comparison and hashing (uppercase alphanumeric)."""
    folded = unicodedata.normalize("NFKD", text)
    ascii_text = folded.encode("ascii", "ignore").decode("ascii")
    return _PLATE_ALLOWED.sub("", ascii_text.upper())


def hash_plate_text(normalized_text: str, *, salt: str = "") -> str:
    """SHA-256 hex digest of normalized plate text with optional application salt."""
    payload = f"{salt}:{normalized_text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def hash_evidence_bytes(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def character_error_rate(reference: str, hypothesis: str) -> float:
    """Levenshtein CER: edit distance divided by reference length."""
    ref = normalize_plate_text(reference)
    hyp = normalize_plate_text(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    distance = _levenshtein(ref, hyp)
    return distance / len(ref)


def _levenshtein(first: str, second: str) -> int:
    if first == second:
        return 0
    if not first:
        return len(second)
    if not second:
        return len(first)
    previous = list(range(len(second) + 1))
    for i, char_a in enumerate(first, start=1):
        current = [i]
        for j, char_b in enumerate(second, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (char_a != char_b)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


@dataclass(frozen=True)
class PlateReadResult:
    raw_text: str
    normalized_text: str
    confidence: float
    plate_hash: str


class PlateOCRReader:
    """Lazy EasyOCR reader; disabled when the dependency is missing."""

    def __init__(self, languages: tuple[str, ...] = ("en",), gpu: bool = False) -> None:
        self._languages = languages
        self._gpu = gpu
        self._reader: Any | None = None
        self._load_error: str | None = None

    @property
    def available(self) -> bool:
        return self._ensure_reader()

    @property
    def unavailable_reason(self) -> str | None:
        self._ensure_reader()
        return self._load_error

    def _ensure_reader(self) -> bool:
        if self._reader is not None:
            return True
        if self._load_error is not None:
            return False
        try:
            import easyocr  # type: ignore
        except ImportError:
            self._load_error = (
                "easyocr is not installed. Install optional OCR dependencies from "
                "requirements-ocr.txt"
            )
            return False
        try:
            self._reader = easyocr.Reader(
                list(self._languages),
                gpu=self._gpu,
                verbose=False,
            )
        except Exception as exc:  # pragma: no cover - hardware/runtime specific
            self._load_error = f"Could not initialize EasyOCR: {exc}"
            return False
        return True

    def read_crop(self, crop_bgr: Any, *, hash_salt: str = "") -> PlateReadResult | None:
        if not self._ensure_reader() or crop_bgr is None or crop_bgr.size == 0:
            return None
        assert self._reader is not None
        try:
            results = self._reader.readtext(crop_bgr, detail=1, paragraph=False)
        except Exception:
            return None
        if not results:
            return None
        best = max(results, key=lambda item: float(item[2]))
        raw_text = str(best[1]).strip()
        normalized = normalize_plate_text(raw_text)
        if not normalized:
            return None
        confidence = float(best[2])
        return PlateReadResult(
            raw_text=raw_text,
            normalized_text=normalized,
            confidence=confidence,
            plate_hash=hash_plate_text(normalized, salt=hash_salt),
        )


def best_plate_for_vehicle(
    vehicle_xyxy: tuple[float, float, float, float],
    plate_detections: list[tuple[tuple[float, float, float, float], PlateReadResult | None]],
) -> PlateReadResult | None:
    """Pick the plate detection with highest overlap inside the vehicle box."""
    vx1, vy1, vx2, vy2 = vehicle_xyxy
    vehicle_area = max(1.0, (vx2 - vx1) * (vy2 - vy1))
    best: PlateReadResult | None = None
    best_score = 0.0
    for plate_box, reading in plate_detections:
        if reading is None:
            continue
        px1, py1, px2, py2 = plate_box
        ix1 = max(vx1, px1)
        iy1 = max(vy1, py1)
        ix2 = min(vx2, px2)
        iy2 = min(vy2, py2)
        inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        score = inter / vehicle_area
        if score > best_score:
            best_score = score
            best = reading
    return best if best_score >= 0.01 else None
