"""Partial end-to-end experiment with separate stage outputs."""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from experiment_utils import git_commit, new_experiment_dir, sha256_file, write_manifest


def main() -> int:
    import cv2

    video = ROOT / "datasets" / "raw_clips" / "no helmet events" / "not wearing helmets.mp4"
    if not video.is_file():
        video = None
    exp_dir = new_experiment_dir("end_to_end", "pipeline_smoke")
    stages: dict = {"experiment_id": "pipeline_smoke", "git_commit": git_commit()}

    if video is None:
        stages["status"] = "blocked"
        stages["blocker"] = "Test video not found at expected raw_clips path"
        (exp_dir / "stages.json").write_text(json.dumps(stages, indent=2), encoding="utf-8")
        write_manifest(
            exp_dir,
            experiment_id="pipeline_smoke",
            category="end_to_end",
            command=[sys.executable, "scripts/run_end_to_end_experiment.py"],
            exit_code=2,
            config={"video": None},
            status="blocked",
            limitations=[stages["blocker"]],
        )
        print(json.dumps(stages, indent=2))
        return 2

    stages["input_video"] = str(video)
    stages["input_video_sha256"] = sha256_file(video)
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    stages["video_duration_seconds_est"] = round(frame_count / fps, 3) if fps else None
    stages["frame_count"] = frame_count

    jsonl = (
        ROOT
        / "runs"
        / "violation_detector"
        / "not wearing helmets_20261009_124822"
        / "events.jsonl"
    )
    if jsonl.is_file():
        events = [
            json.loads(line)
            for line in jsonl.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        stages["detector_stage"] = {
            "status": "inherited_from_prior_run",
            "jsonl": str(jsonl),
            "candidate_count": len(events),
            "candidate_type": events[0].get("candidate_type") if events else None,
        }
    else:
        stages["detector_stage"] = {"status": "missing_artifact"}

    stages["api_db_stage"] = {
        "status": "not_run_in_this_script",
        "note": "Use tests/test_api_integration.py with temporary SQLite",
    }
    stages["blockchain_stage"] = {
        "status": "blocked_without_env",
        "note": "Sepolia credentials not configured (.env absent)",
    }
    stages["hash_stage"] = {
        "status": "not_automated_in_pipeline",
        "note": "Evidence hashes must be computed at verify/log-chain time",
    }

    (exp_dir / "stages.json").write_text(json.dumps(stages, indent=2), encoding="utf-8")
    write_manifest(
        exp_dir,
        experiment_id="pipeline_smoke",
        category="end_to_end",
        command=[sys.executable, "scripts/run_end_to_end_experiment.py"],
        exit_code=0,
        config={"video": str(video)},
        metrics={"candidate_count": stages.get("detector_stage", {}).get("candidate_count")},
        limitations=["Partial E2E — detector output reused; chain not executed"],
        status="partial",
    )
    print(json.dumps(stages, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
