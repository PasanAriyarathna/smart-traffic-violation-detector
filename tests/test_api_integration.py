"""API integration tests using a temporary SQLite database."""

from __future__ import annotations

import gc
import importlib
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BackendIntegrationTests(unittest.TestCase):
    _tmpdir: tempfile.TemporaryDirectory[str]
    main_module: object

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(cls._tmpdir.name) / "test_events.sqlite3"
        os.environ["STVD_DB_PATH"] = str(db_path)
        os.environ["PYTHONPATH"] = str(PROJECT_ROOT)
        import backend.app.main as main_module

        cls.main_module = importlib.reload(main_module)

    @classmethod
    def tearDownClass(cls) -> None:
        gc.collect()
        cls._tmpdir.cleanup()

    def _client(self) -> TestClient:
        return TestClient(self.main_module.app)  # type: ignore[attr-defined]

    def test_health(self) -> None:
        with self._client() as client:
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "ok")

    def test_import_and_verify(self) -> None:
        jsonl = (
            PROJECT_ROOT
            / "runs"
            / "violation_detector"
            / "not wearing helmets_20261009_124822"
            / "events.jsonl"
        )
        if not jsonl.is_file():
            self.skipTest("Helmet JSONL artifact not available")
        rel = jsonl.relative_to(PROJECT_ROOT).as_posix()
        with self._client() as client:
            response = client.post("/events/import", json={"jsonl_path": rel})
            self.assertEqual(response.status_code, 200)
            self.assertGreater(response.json()["imported"], 0)

            listed = client.get("/events")
            self.assertEqual(listed.status_code, 200)
            events = listed.json()
            self.assertTrue(events)
            event_id = events[0]["event_id"]

            verify = client.post(
                f"/events/{event_id}/verify",
                json={"reviewer_note": "integration test verify"},
            )
            self.assertEqual(verify.status_code, 200)
            self.assertEqual(verify.json()["review_status"], "VERIFIED")

            chain = client.post(
                f"/events/{event_id}/log-chain",
                json={
                    "evidence_hash_hex": "a" * 64,
                    "plate_hash_hex": "b" * 64,
                },
            )
            self.assertEqual(chain.status_code, 503)

            reject = client.post(
                f"/events/{event_id}/reject",
                json={"reviewer_note": "integration test reject"},
            )
            self.assertEqual(reject.status_code, 200)
            self.assertEqual(reject.json()["review_status"], "REJECTED")

    def test_import_missing_jsonl(self) -> None:
        with self._client() as client:
            response = client.post(
                "/events/import",
                json={"jsonl_path": "runs/does_not_exist/events.jsonl"},
            )
            self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
