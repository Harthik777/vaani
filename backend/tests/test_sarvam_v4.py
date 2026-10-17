"""Sarvam v4-era adapter behaviour: codemix + keyterms on Saaras v4, per-language Bulbul v4-flash voices,
the 105B request shape that actually answers, the response cache and the chat circuit breaker."""
import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
import httpx
from fastapi.testclient import TestClient
from main import app
from services import config, sarvam, cache, llm


def fake_client(payload, status=200):
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.post.return_value = httpx.Response(status, json=payload, request=httpx.Request("POST", "https://api.sarvam.ai/x"))
    return client


class SarvamV4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(config, "DATA_DIR", Path(self.tmp.name)), patch.object(config, "CACHE_ENABLED", True),
                        patch.object(config, "USE_REAL_SARVAM", True), patch.object(config, "SARVAM_API_KEY", "k")]
        for p in self.patches:
            p.start()
        sarvam._chat_failures, sarvam._chat_paused_until = 0, 0.0
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_saaras_v4_sends_codemix_and_keyterms(self):
        fake = fake_client({"transcript": "मुझे stock alert चाहिए"})
        with patch.object(config, "SARVAM_STT_MODEL", "saaras:v4"), patch.object(config, "SARVAM_STT_MODE", "codemix"), \
             patch("services.sarvam.httpx.AsyncClient", return_value=fake):
            asyncio.run(sarvam.transcribe(b"audio", "kannada", "a.webm", "audio/webm", keyterms=["Grade-B", "Grade-B", " ", "x", "ಏಲಕ್ಕಿ"]))
        sent = fake.post.call_args.kwargs["data"]
        self.assertEqual(sent["language_code"], "kn-IN")
        self.assertEqual(sent["mode"], "codemix")
        self.assertEqual(json.loads(sent["keyterms"]), ["Grade-B", "ಏಲಕ್ಕಿ"])  # deduplicated, blanks and 1-char terms dropped

    def test_saaras_v3_never_receives_v4_only_fields(self):
        fake = fake_client({"transcript": "words"})
        with patch.object(config, "SARVAM_STT_MODEL", "saaras:v3"), patch("services.sarvam.httpx.AsyncClient", return_value=fake):
            asyncio.run(sarvam.transcribe(b"audio", "hindi", keyterms=["Grade-B"]))
        sent = fake.post.call_args.kwargs["data"]
        self.assertNotIn("keyterms", sent)
        self.assertNotIn("mode", sent)

    def test_stt_route_accepts_keyterms_form_field(self):
        fake = fake_client({"transcript": "ಏಲಕ್ಕಿ ಸ್ಟಾಕ್"})
        with patch.object(config, "SARVAM_STT_MODEL", "saaras:v4"), patch("services.sarvam.httpx.AsyncClient", return_value=fake):
            r = self.client.post("/api/stt", files={"audio": ("a.webm", b"audio", "audio/webm")},
                                 data={"lang": "kannada", "keyterms": json.dumps(["ಏಲಕ್ಕಿ", "K.R. Market"])})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["model"], "saaras:v4")
        self.assertEqual(json.loads(fake.post.call_args.kwargs["data"]["keyterms"]), ["ಏಲಕ್ಕಿ", "K.R. Market"])

    def test_bulbul_v4_flash_uses_a_persona_per_language(self):
        with patch.object(config, "SARVAM_TTS_MODEL", "bulbul:v4-flash"), patch.object(config, "SARVAM_TTS_SPEAKER", ""):
            self.assertEqual(sarvam.speaker_for("kannada"), "chaitra_kn_narration")
            self.assertEqual(sarvam.speaker_for("hindi"), "aparna_hi_customer")
            self.assertTrue(all("_" in sarvam.speaker_for(lang) for lang in sarvam.LANG_CODES))
        with patch.object(config, "SARVAM_TTS_MODEL", "bulbul:v4-flash"), patch.object(config, "SARVAM_TTS_SPEAKER", "shubh_enhi_ads"):
            self.assertEqual(sarvam.speaker_for("tamil"), "shubh_enhi_ads")  # explicit persona wins
        with patch.object(config, "SARVAM_TTS_MODEL", "bulbul:v3"), patch.object(config, "SARVAM_TTS_SPEAKER", ""):
            self.assertEqual(sarvam.speaker_for("kannada"), "shubh")  # v3 short names

    def test_tts_is_cached_so_a_rehearsal_makes_the_stage_run_instant(self):
        fake = fake_client({"audios": ["UklGRg=="]})
        with patch.object(config, "SARVAM_TTS_MODEL", "bulbul:v4-flash"), patch.object(config, "SARVAM_TTS_SPEAKER", ""), \
             patch("services.sarvam.httpx.AsyncClient", return_value=fake):
            first = self.client.post("/api/tts", json={"text": "ನಮಸ್ಕಾರ", "lang": "kannada"}).json()
            second = self.client.post("/api/tts", json={"text": "ನಮಸ್ಕಾರ", "lang": "kannada"}).json()
        self.assertEqual(first["audios"], second["audios"])
        self.assertEqual(fake.post.call_count, 1)
        self.assertEqual(fake.post.call_args.kwargs["json"]["speaker"], "chaitra_kn_narration")
        self.assertEqual(fake.post.call_args.kwargs["json"]["model"], "bulbul:v4-flash")

    def test_cache_is_keyed_on_content_and_can_be_disabled(self):
        cache.put("llm", cache.key("a"), "one")
        self.assertEqual(cache.get("llm", cache.key("a")), "one")
        self.assertIsNone(cache.get("llm", cache.key("b")))
        with patch.object(config, "CACHE_ENABLED", False):
            self.assertIsNone(cache.get("llm", cache.key("a")))
        self.assertEqual(cache.clear(), 1)

    def test_sarvam_chat_request_shape_answers_instead_of_reasoning_forever(self):
        fake = fake_client({"choices": [{"message": {"content": '{"items": []}'}, "finish_reason": "stop"}]})
        schema = {"type": "object", "properties": {"items": {"type": "array"}}, "required": ["items"], "additionalProperties": False}
        with patch.object(config, "SARVAM_LLM_MODEL", "sarvam-105b-conversations"), patch("services.sarvam.httpx.AsyncClient", return_value=fake):
            out = asyncio.run(sarvam.chat_json("prompt", system="sys", schema=schema))
        self.assertEqual(out, '{"items": []}')
        sent = fake.post.call_args.kwargs["json"]
        self.assertEqual(sent["model"], "sarvam-105b-conversations")
        self.assertEqual(sent["messages"][0], {"role": "system", "content": "sys"})
        self.assertEqual(sent["reasoning_effort"], "low")
        self.assertGreaterEqual(sent["max_tokens"], 1500)
        self.assertEqual(sent["response_format"]["type"], "json_schema")
        self.assertTrue(sent["response_format"]["json_schema"]["strict"])

    def test_empty_content_counts_as_failure_and_breaker_opens_after_two(self):
        fake = fake_client({"choices": [{"message": {"content": ""}, "finish_reason": "length"}]})
        with patch("services.sarvam.httpx.AsyncClient", return_value=fake):
            self.assertTrue(sarvam.chat_available())
            with self.assertRaises(RuntimeError):
                asyncio.run(sarvam.chat_json("p1"))
            self.assertTrue(sarvam.chat_available())  # one failure is tolerated
            with self.assertRaises(RuntimeError):
                asyncio.run(sarvam.chat_json("p2"))
            self.assertFalse(sarvam.chat_available())  # second failure pauses the model
            self.assertGreater(sarvam._chat_paused_until, time.time())

    def test_agent_falls_back_to_main_llm_when_sarvam_chat_fails(self):
        broken = fake_client({"choices": [{"message": {"content": ""}, "finish_reason": "length"}]})
        with patch.object(config, "AGENT_LLM", "sarvam"), patch("services.sarvam.httpx.AsyncClient", return_value=broken), \
             patch.object(config, "LLM_API_KEY", "main-key"), patch.object(config, "LLM_PROVIDER", "gemini"), \
             patch.object(llm, "_gemini_generate", AsyncMock(return_value='{"conflicts": []}')):
            result, brain = asyncio.run(llm.agent_json("prompt", system="sys", schema={"type": "object"}))
        self.assertEqual(result, {"conflicts": []})
        self.assertEqual(brain, "gemini:" + config.LLM_FAST_MODEL)  # the agent's fallback is the fast model

    def test_agent_uses_sarvam_when_it_answers(self):
        good = fake_client({"choices": [{"message": {"content": '{"conflicts": []}'}, "finish_reason": "stop"}]})
        with patch.object(config, "AGENT_LLM", "sarvam"), patch("services.sarvam.httpx.AsyncClient", return_value=good):
            result, brain = asyncio.run(llm.agent_json("prompt"))
        self.assertEqual(result, {"conflicts": []})
        self.assertEqual(brain, "sarvam:" + config.SARVAM_LLM_MODEL)

    def test_kannada_is_a_first_class_language(self):
        self.assertEqual(sarvam.LANG_CODES["kannada"], "kn-IN")
        r = self.client.post("/api/stt", data={"demo": "true", "mode": "business", "lang": "kannada"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("ಆರ್ಡರ್", r.json()["transcript"])
        import mocks
        tx = mocks.MEETING["transcript"]["kannada"]
        self.assertTrue(all(r["source_quote"] in tx for r in mocks.MEETING["rules"]["kannada"]))
        extraction = self.client.post("/api/extract", json={"mode": "business", "transcript": tx, "demo": True}).json()
        self.assertEqual({r["speaker"] for r in extraction["rules"]}, {"Owner", "Manager"})
        self.assertTrue(all(r["verification"]["status"] == "verified" for r in extraction["rules"]), extraction["rules"])


if __name__ == "__main__":
    unittest.main()
