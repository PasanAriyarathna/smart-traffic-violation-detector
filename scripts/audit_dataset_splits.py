"""Read-only dataset split and filename overlap audit."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "datasets" / "training_copy"
OUTPUT = ROOT / "docs" / "evaluation" / "dataset" / "split_independence_audit.json"


def stem_key(name: str) -> str:
    """Roboflow-style stems often embed a source id before _jpg.rf."""
    base = Path(name).stem
    match = re.match(r"(.+)_jpg\.rf\.[a-f0-9]+", base)
    if match:
        return match.group(1)
    return base.split("_jpg")[0] if "_jpg" in base else base


def main() -> None:
    split_files: dict[str, list[str]] = {}
    split_keys: dict[str, set[str]] = {}
    for split in ("train", "valid", "test"):
        img_dir = DATA_ROOT / split / "images"
        files = sorted(p.name for p in img_dir.glob("*.*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
        split_files[split] = files
        split_keys[split] = {stem_key(name) for name in files}

    overlaps = {}
    for a, b in (("train", "valid"), ("train", "test"), ("valid", "test")):
        inter = split_keys[a] & split_keys[b]
        overlaps[f"{a}_vs_{b}"] = sorted(inter)

    counts = {split: len(files) for split, files in split_files.items()}
    payload = {
        "data_root": str(DATA_ROOT.resolve()),
        "image_counts": counts,
        "total_images": sum(counts.values()),
        "methodology_claims_note": (
            "Milestone 2 mentions 318 annotated images expanded to 768 and 70/20/10 split. "
            "Current local copy has 361 images across train/valid/test — treat as separate evidence."
        ),
        "stem_key_overlap_across_splits": overlaps,
        "interpretation": (
            "Shared stem keys across splits may indicate related frames or augmentation groups. "
            "This is not proof of same-video leakage without source-video metadata."
        ),
        "source_video_metadata_available": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
