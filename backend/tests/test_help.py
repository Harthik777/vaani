"""The in-app guide: deterministic answers per step, FAQ matching, AI path with translation, honest fallback."""
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app
from services import config, llm, sarvam


class HelpTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_step_orientation_without_a_question(self):
        with patch.object(config, "USE_REAL_LLM", False), patch.object(config, "USE_REAL_SARVAM", False):
            r = self.client.post("/api/help", json={"question": "", "phase": "extract", "lang": "english"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["step"], "Review")
        self.assertIn("quotes the speaker exactly", body["answer"])
        self.assertEqual(body["brain"], "guide")
        self.assertEqual(len(body["suggestions"]), 3)

    def test_faq_matching_is_deterministic(self):
        with patch.object(config, "USE_REAL_LLM", False), patch.object(config, "USE_REAL_SARVAM", False):
            red = self.client.post("/api/help", json={"question": "why is 48 shown in red?", "phase": "extract", "lang": "english"}).json()
            share = self.client.post("/api/help", json={"question": "how do I send this on whatsapp", "phase": "brd", "lang": "english"}).json()
            unknown = self.client.post("/api/help", json={"question": "zzz", "phase": "signoff", "lang": "english"}).json()
        self.assertIn("nobody said it", red["answer"])
        self.assertIn("QR codes", share["answer"])
        self.assertIn("approve or skip", unknown["answer"])  # falls back to the step orientation

    def test_ai_answer_in_users_language(self):
        with patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "k"), patch.object(config, "USE_REAL_SARVAM", False), \
             patch.object(llm, "agent_json", AsyncMock(return_value=({"answer": "बजट अभी न बताएँ तो वह खुला प्रश्न बनेगा।"}, "sarvam:x"))) as fake:
            r = self.client.post("/api/help", json={"question": "बजट नहीं पता", "phase": "interview", "lang": "hindi", "counts": {"completeness": 50}})
        self.assertEqual(r.json()["answer"], "बजट अभी न बताएँ तो वह खुला प्रश्न बनेगा।")
        self.assertEqual(r.json()["brain"], "sarvam:x")
        prompt = fake.call_args.args[0]
        self.assertIn("Agent questions", prompt)
        self.assertIn("Reply in Hindi", prompt)
        self.assertIn("'completeness': 50", prompt)

    def test_ai_failure_falls_back_and_translates(self):
        with patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "k"), patch.object(config, "USE_REAL_SARVAM", True), patch.object(config, "SARVAM_API_KEY", "k"), \
             patch.object(llm, "agent_json", AsyncMock(side_effect=RuntimeError("down"))), patch.object(sarvam, "translate", AsyncMock(return_value="अनुवादित")):
            r = self.client.post("/api/help", json={"question": "what now", "phase": "brd", "lang": "hindi"})
        self.assertEqual(r.json()["answer"], "अनुवादित")
        self.assertEqual(r.json()["brain"], "guide")

    def test_unknown_phase_and_long_question_are_safe(self):
        with patch.object(config, "USE_REAL_LLM", False), patch.object(config, "USE_REAL_SARVAM", False):
            self.assertEqual(self.client.post("/api/help", json={"question": "x", "phase": "nope", "lang": "english"}).json()["step"], "Start")
            self.assertEqual(self.client.post("/api/help", json={"question": "x" * 700, "phase": "brd", "lang": "english"}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
