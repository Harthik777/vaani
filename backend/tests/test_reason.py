"""Executable requirements (scenario) and agent mediation (resolve) with fake models; honest 503 without one."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app
from services import config, llm
import mocks

EN = mocks.MEETING["transcript"]["english"]
RULES = mocks.MEETING["rules"]["english"]


class ReasonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(config, "DATA_DIR", Path(self.tmp.name)), patch.object(config, "USE_REAL_LLM", False), patch.object(config, "USE_REAL_SARVAM", False)]
        for p in self.patches:
            p.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def live(self):
        return [patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "test"), patch.object(config, "AGENT_LLM", "main")]

    def test_scenario_needs_a_model_and_maps_every_rule(self):
        r = self.client.post("/api/agent/scenario", json={"rules": RULES, "scenario": "Stock is 70 kg and a 25,000 rupee order arrived."})
        self.assertEqual(r.status_code, 503)
        fake = {"results": [{"id": RULES[0]["id"], "fires": False, "because": "70 kg is above 50 kg"}, {"id": "ghost", "fires": True, "because": "x"}]}
        with patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "test"), patch.object(config, "AGENT_LLM", "main"), \
                patch.object(llm, "agent_json", new=AsyncMock(return_value=(fake, "gemini:fake"))):
            r = self.client.post("/api/agent/scenario", json={"rules": RULES, "scenario": "Stock is 70 kg and a 25,000 rupee order arrived."})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual([x["id"] for x in body["results"]], [x["id"] for x in RULES])  # every rule answered, no ghosts
        self.assertFalse(body["results"][0]["fires"])
        self.assertIn("no answer", body["results"][1]["because"])

    def test_resolve_proposes_a_verified_rule_with_an_exception(self):
        owner, manager = RULES[0], RULES[3]
        conflict = {"rule_ids": [owner["id"], manager["id"]], "topic": "threshold", "explanation": "50 vs 100"}
        fake = {"title": "Seasonal reorder threshold", "condition": "cardamom stock falls below 50 kg", "action": "send the reorder alert",
                "exception": "in festival season, alert at 100 kg", "source_quote": manager["source_quote"], "question": "Is 100 kg only for festival season?", "why": "Both positions kept."}
        with patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "test"), patch.object(config, "AGENT_LLM", "main"), \
                patch.object(llm, "complete_json", new=AsyncMock(return_value=fake)):
            r = self.client.post("/api/agent/resolve", json={"rules": RULES, "conflict": conflict, "transcript": EN})
        self.assertEqual(r.status_code, 200, r.text)
        p = r.json()["proposal"]
        self.assertEqual(p["speaker"], "Owner + Manager")
        self.assertIn(p["source_quote"], EN)
        self.assertTrue({"50", "100"} <= set(p["source_quote"].replace(",", " ").split()) or "100" in p["source_quote"], p["source_quote"])
        self.assertEqual(p["verification"]["status"], "verified")  # the quote chosen carries every number the rule uses
        self.assertEqual(r.json()["question"], "Is 100 kg only for festival season?")
        # a quote the model invented is repaired or replaced; it never passes through unverified
        fake2 = {**fake, "source_quote": "words nobody said at all", "exception": None}
        with patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "test"), patch.object(config, "AGENT_LLM", "main"), \
                patch.object(llm, "complete_json", new=AsyncMock(return_value=fake2)):
            p2 = self.client.post("/api/agent/resolve", json={"rules": RULES, "conflict": conflict, "transcript": EN}).json()["proposal"]
        self.assertIn(p2["source_quote"], EN)
        self.assertEqual(self.client.post("/api/agent/resolve", json={"rules": RULES, "conflict": {"rule_ids": ["nope", "x"]}, "transcript": EN}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
