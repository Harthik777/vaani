"""Regression tests for problems found in the real test of 17 Oct 2026 (friend message, then spice context; 30-60 s waits)."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from fastapi.testclient import TestClient
from main import app
from services import config, llm, sarvam


class RealTestFixes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(config, "DATA_DIR", Path(self.tmp.name)), patch.object(config, "CACHE_ENABLED", False)]
        for p in self.patches:
            p.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def live(self):
        return [patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "test")]

    def sarvam_reply(self, status, payload):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = httpx.Response(status, json=payload, request=httpx.Request("POST", "https://api.sarvam.ai/x"))
        return client

    def test_extraction_returns_speakers_and_conflicts_in_one_call(self):
        tx = "[Owner] Limit 30 appointments a day.\n[Receptionist] Limit 25 appointments a day."
        answer = {"rules": [
            {"id": "r1", "title": "Owner limit", "condition": "more than 30 bookings", "action": "stop booking", "source_quote": "Limit 30 appointments a day."},
            {"id": "r2", "title": "Receptionist limit", "condition": "more than 25 bookings", "action": "stop booking", "source_quote": "Limit 25 appointments a day."}],
            "conflicts": [{"rule_ids": ["r1", "r2"], "topic": "daily limit", "explanation": "Owner 30 vs Receptionist 25"},
                          {"rule_ids": ["r1", "r9"], "topic": "unknown rule", "explanation": "x"}],
            "review_notes": []}
        ps = self.live() + [patch.object(llm, "complete_json", new=AsyncMock(return_value=answer))]
        for p in ps:
            p.start()
        try:
            body = self.client.post("/api/extract", json={"transcript": tx}).json()
        finally:
            for p in ps:
                p.stop()
        self.assertEqual([r["speaker"] for r in body["rules"]], ["Owner", "Receptionist"])
        self.assertEqual([c["rule_ids"] for c in body["conflicts"]], [["r1", "r2"]])

    def test_extraction_and_agent_use_the_fast_model(self):
        ps = self.live() + [patch.object(llm, "complete_json", new=AsyncMock(return_value={"rules": [], "review_notes": []}))]
        for p in ps:
            p.start()
        try:
            self.client.post("/api/extract", json={"transcript": "hello"})
            self.assertTrue(llm.complete_json.call_args.kwargs.get("fast"))
        finally:
            for p in ps:
                p.stop()
        self.assertEqual(config.AGENT_LLM, "main")

    def test_rejected_key_and_used_up_credits_are_explained(self):
        for status, code, words in ((403, "invalid_api_key_error", "rejected the API key"), (402, "insufficient_quota_error", "credits are used up")):
            sarvam._translations.clear()
            fake = self.sarvam_reply(status, {"error": {"message": "x", "code": code}})
            with self.subTest(status=status), patch.object(config, "USE_REAL_SARVAM", True), patch.object(config, "SARVAM_API_KEY", "k"), \
                    patch("services.sarvam.httpx.AsyncClient", return_value=fake):
                r = self.client.post("/api/translate", json={"texts": ["When do you need it?"], "target": "hindi"})
                self.assertEqual(r.status_code, status)
                self.assertIn(words, r.json()["detail"])
                stt = self.client.post("/api/stt", data={"lang": "hindi"}, files={"audio": ("a.webm", b"x", "audio/webm")})
                self.assertEqual(stt.status_code, status)
                self.assertIn("audio is preserved", stt.json()["detail"])


if __name__ == "__main__":
    unittest.main()
