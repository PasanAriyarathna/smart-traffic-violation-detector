"""Conservative license-plate crop enhancement for OCR preprocessing."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Minimum display/OCR-friendly size (does not invent missing pixels).
DEFAULT_MIN_WIDTH = 200
DEFAULT_MIN_HEIGHT = 50
# Tiny detector crops (e.g. 10×9 px) need strong upscaling; capped to limit interpolation artifacts.
DEFAULT_MAX_SCALE = 20.0

CLAHE_STD_THRESHOLD = 38.0
BLUR_LAPLACIAN_THRESHOLD = 3500.0


@dataclass(frozen=True)
class CropAnalysis:
    width: int
    height: int
    laplacian_variance: float
    gray_std: float
    issues: tuple[str, ...]


@dataclass(frozen=True)
class EnhanceResult:
    image_bgr: np.ndarray
    methods: tuple[str, ...]
    scale_factor: float
    analysis: CropAnalysis


def analyze_crop(image_bgr: np.ndarray) -> CropAnalysis:
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    std = float(gray.std())
    issues: list[str] = []
    if w < 40 or h < 20:
        issues.append("very_low_resolution")
    elif w < 80 or h < 35:
        issues.append("low_resolution")
    if lap < BLUR_LAPLACIAN_THRESHOLD:
        issues.append("soft_or_blurry")
    if std < CLAHE_STD_THRESHOLD:
        issues.append("low_contrast")
    if w / max(h, 1) < 2.0 or w / max(h, 1) > 8.0:
        issues.append("unusual_aspect_ratio")
    return CropAnalysis(w, h, lap, std, tuple(issues))


def _unsharp_mild(image_bgr: np.ndarray, amount: float = 0.35) -> np.ndarray:
    blurred = cv2.GaussianBlur(image_bgr, (0, 0), sigmaX=1.0)
    return cv2.addWeighted(image_bgr, 1.0 + amount, blurred, -amount, 0)


def enhance_plate_crop(
    image_bgr: np.ndarray,
    *,
    min_width: int = DEFAULT_MIN_WIDTH,
    min_height: int = DEFAULT_MIN_HEIGHT,
    max_scale: float = DEFAULT_MAX_SCALE,
) -> EnhanceResult:
    """Enhance a BGR crop for OCR. Does not alter plate content by generative means."""
    if image_bgr is None or image_bgr.size == 0:
        raise ValueError("empty image")
    analysis = analyze_crop(image_bgr)
    methods: list[str] = []
    out = image_bgr.copy()
    h, w = out.shape[:2]
    scale = max(min_width / max(w, 1), min_height / max(h, 1), 1.0)
    scale = min(scale, max_scale)
    if scale > 1.001:
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        out = cv2.resize(out, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        methods.append(f"upscale_lanczos4_x{scale:.2f}")

    # Mild denoise: bilateral on tiny crops; slightly stronger only when already upscaled.
    if out.shape[0] * out.shape[1] < 120_000:
        out = cv2.bilateralFilter(out, d=5, sigmaColor=40, sigmaSpace=40)
        methods.append("bilateral_denoise_mild")
    else:
        out = cv2.fastNlMeansDenoisingColored(out, None, 3, 3, 7, 21)
        methods.append("nlmeans_denoise_light")

    gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
    if float(gray.std()) < CLAHE_STD_THRESHOLD:
        lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_channel = clahe.apply(l_channel)
        out = cv2.cvtColor(cv2.merge([l_channel, a, b]), cv2.COLOR_LAB2BGR)
        methods.append("clahe_l_channel")

    lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if lap < BLUR_LAPLACIAN_THRESHOLD:
        out = _unsharp_mild(out, amount=0.3)
        methods.append("unsharp_mild")

    if not methods:
        methods.append("passthrough")
    return EnhanceResult(
        image_bgr=out,
        methods=tuple(methods),
        scale_factor=scale,
        analysis=analysis,
    )
