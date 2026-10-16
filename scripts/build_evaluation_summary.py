"""Write docs/validation/evaluation_summary.json from verified artifacts and test logs."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "validation" / "evaluation_summary.json"


def run_pytest_summary() -> dict:
    cmd = [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    line = (proc.stdout + proc.stderr).strip().splitlines()[-1] if proc.stdout or proc.stderr else ""
    match = re.search(r"(\d+) passed", line)
    failed = re.search(r"(\d+) failed", line)
    sub = re.search(r"(\d+) subtests passed", line)
    return {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "summary_line": line,
        "passed": int(match.group(1)) if match else None,
        "failed": int(failed.group(1)) if failed else 0,
        "subtests_passed": int(sub.group(1)) if sub else 0,
    }


def main() -> None:
    detector_path = ROOT / "docs/evaluation/detector/detector_val_test_20261009T120646Z/metrics.json"
    detector = json.loads(detector_path.read_text(encoding="utf-8")) if detector_path.is_file() else None
    helmet = (
        json.loads((ROOT / "docs/evaluation/violations/helmet_metrics.json").read_text(encoding="utf-8"))
        if (ROOT / "docs/evaluation/violations/helmet_metrics.json").is_file()
        else None
    )
    blockchain = (
        json.loads((ROOT / "docs/evaluation/blockchain/blockchain_metrics.json").read_text(encoding="utf-8"))
        if (ROOT / "docs/evaluation/blockchain/blockchain_metrics.json").is_file()
        else None
    )
    ocr_metrics_path = ROOT / "docs/evaluation/ocr/ocr_metrics.json"
    ocr = json.loads(ocr_metrics_path.read_text(encoding="utf-8")) if ocr_metrics_path.is_file() else None
    helmet_val_path = ROOT / "docs/evaluation/violations/helmet_annotation_validation.json"
    helmet_val = json.loads(helmet_val_path.read_text(encoding="utf-8")) if helmet_val_path.is_file() else None
    leakage_path = ROOT / "docs/evaluation/dataset/split_leakage_audit.json"
    leakage = json.loads(leakage_path.read_text(encoding="utf-8")) if leakage_path.is_file() else None
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_branch": "feature/update-annotated-dataset",
        "pytest": run_pytest_summary(),
        "detector_test_split": detector,
        "helmet_rule": helmet,
        "helmet_annotation_validation": helmet_val,
        "ocr_metrics": ocr,
        "blockchain_local": blockchain,
        "dataset_leakage_audit": {
            "path": str(leakage_path) if leakage else None,
            "image_count": leakage.get("image_count") if leakage else None,
            "exact_sha256_cross_split": len(leakage.get("exact_duplicate_sha256_across_splits", []))
            if leakage
            else None,
            "stem_groups_spanning_splits": len(leakage.get("stem_groups_spanning_splits", []))
            if leakage
            else None,
            "corrected_manifest": "docs/evaluation/dataset/corrected_split_manifest_v1.json",
        },
        "ocr_cer": ocr.get("status") if ocr else "NOT_MEASURED",
        "tracking_quantitative": "NOT_MEASURED",
        "overtaking_real_video": "NOT_MEASURED",
        "red_light_real_video": "NOT_MEASURED",
        "sepolia_deployment": "NOT_MEASURED",
        "baseline_yolov5_mysql": "NOT_MEASURED",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
