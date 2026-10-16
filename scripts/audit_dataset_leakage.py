"""Hash-based split leakage audit and recommended group-wise split manifest (no file moves)."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "datasets" / "training_copy"
AUDIT_OUT = ROOT / "docs" / "evaluation" / "dataset" / "split_leakage_audit.json"
MANIFEST_OUT = ROOT / "docs" / "evaluation" / "dataset" / "corrected_split_manifest_v1.json"


def stem_key(name: str) -> str:
    base = Path(name).stem
    match = re.match(r"(.+)_jpg\.rf\.[a-f0-9]+", base)
    if match:
        return match.group(1)
    return base.split("_jpg")[0] if "_jpg" in base else base


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dhash64(path: Path) -> str | None:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return None
    resized = cv2.resize(image, (9, 8), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    bits = "".join("1" if bit else "0" for bit in diff.flatten())
    return format(int(bits, 2), "016x")


def hamming_hex(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def main() -> None:
    records: list[dict] = []
    by_split: dict[str, list[dict]] = defaultdict(list)

    for split in ("train", "valid", "test"):
        img_dir = DATA_ROOT / split / "images"
        if not img_dir.is_dir():
            continue
        for path in sorted(img_dir.glob("*.*")):
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            rec = {
                "split": split,
                "filename": path.name,
                "relative_path": str(path.relative_to(DATA_ROOT)).replace("\\", "/"),
                "stem_group": stem_key(path.name),
                "sha256": sha256_file(path),
                "dhash64": dhash64(path),
            }
            records.append(rec)
            by_split[split].append(rec)

    sha_groups: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        sha_groups[rec["sha256"]].append(rec)

    cross_split_sha = [
        {
            "sha256": digest,
            "files": [{"split": item["split"], "filename": item["filename"]} for item in items],
        }
        for digest, items in sha_groups.items()
        if len({item["split"] for item in items}) > 1
    ]

    stem_groups: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        stem_groups[rec["stem_group"]].append(rec)

    cross_split_stem = [
        {
            "stem_group": key,
            "splits": sorted({item["split"] for item in items}),
            "count": len(items),
        }
        for key, items in stem_groups.items()
        if len({item["split"] for item in items}) > 1
    ]

    near_dup_pairs: list[dict] = []
    all_recs = [rec for rec in records if rec["dhash64"]]
    for index, left in enumerate(all_recs):
        for right in all_recs[index + 1 :]:
            if left["split"] == right["split"]:
                continue
            dist = hamming_hex(left["dhash64"], right["dhash64"])
            if dist <= 5:
                near_dup_pairs.append(
                    {
                        "hamming": dist,
                        "left": {"split": left["split"], "filename": left["filename"]},
                        "right": {"split": right["split"], "filename": right["filename"]},
                    }
                )

    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_root": str(DATA_ROOT.resolve()),
        "image_count": len(records),
        "exact_duplicate_sha256_across_splits": cross_split_sha,
        "stem_groups_spanning_splits": cross_split_stem,
        "near_duplicate_dhash_hamming_le_5_across_splits": near_dup_pairs[:200],
        "near_duplicate_pair_count_truncated": len(near_dup_pairs),
        "note": "Original files under datasets/training_copy are unchanged.",
    }
    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    # Recommended split: assign each stem_group to one split (largest current membership wins).
    recommended: dict[str, str] = {}
    for group, items in stem_groups.items():
        counts = defaultdict(int)
        for item in items:
            counts[item["split"]] += 1
        recommended[group] = max(counts, key=lambda key: (counts[key], key))

    manifest_rows = []
    changes = 0
    for rec in records:
        target = recommended[rec["stem_group"]]
        manifest_rows.append(
            {
                "relative_path": rec["relative_path"],
                "current_split": rec["split"],
                "recommended_split": target,
                "stem_group": rec["stem_group"],
                "sha256": rec["sha256"],
            }
        )
        if target != rec["split"]:
            changes += 1

    manifest = {
        "generated_at_utc": audit["generated_at_utc"],
        "rules": [
            "Group images by stem_key (Roboflow frame id before _jpg.rf.*).",
            "Assign entire group to split with largest current membership.",
            "Does not modify files; use manifest to build datasets/training_copy_v1/ manually.",
        ],
        "files_to_move_count": changes,
        "rows": manifest_rows,
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {AUDIT_OUT} ({len(records)} images)")
    print(f"Wrote {MANIFEST_OUT} ({changes} files would change split if applied)")


if __name__ == "__main__":
    main()
