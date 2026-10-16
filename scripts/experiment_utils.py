"""Shared helpers for reproducible experiment manifests."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def environment_info() -> dict[str, Any]:
    info: dict[str, Any] = {
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
    }
    for module_name, key in (
        ("ultralytics", "ultralytics"),
        ("torch", "torch"),
        ("cv2", "opencv"),
        ("numpy", "numpy"),
    ):
        try:
            mod = __import__(module_name)
            info[key] = getattr(mod, "__version__", str(mod))
        except ImportError:
            info[key] = None
    return info


def new_experiment_dir(category: str, experiment_id: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = PROJECT_ROOT / "docs" / "evaluation" / category / f"{experiment_id}_{stamp}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def write_manifest(
    exp_dir: Path,
    *,
    experiment_id: str,
    category: str,
    command: list[str],
    exit_code: int,
    config: dict[str, Any],
    metrics: dict[str, Any] | None = None,
    limitations: list[str] | None = None,
    status: str = "completed",
) -> Path:
    manifest = {
        "experiment_id": experiment_id,
        "category": category,
        "status": status,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "environment": environment_info(),
        "command": command,
        "exit_code": exit_code,
        "config": config,
        "metrics": metrics or {},
        "limitations": limitations or [],
        "output_directory": str(exp_dir.resolve()),
    }
    path = exp_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path
