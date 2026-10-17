"""Vague-term clarifier (deterministic), Roman-script transliteration route, pronunciation dictionary, colloquial register."""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
import httpx
from fastapi.testclient import TestClient
from main import app
from models import CompileIn, Rule
from services import config, sarvam, verify, compiler


def fake_client(responses):
    """responses: list of (status, json) consumed in order."""
    client = AsyncMock(); client.__aenter__.return_value = client
    seq = list(responses)
    async def post(url, **kw):
        status, body = seq.pop(0) if seq else (200, {})
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))
    client.post.side_effect = post
    return client


class ClarityTests(unittest.TestCase):
    def test_vague_terms_whole_word_multilingual(self):
        found = verify.vague_terms("Deliver jaldi and keep it simple; बहुत orders; ಬೇಗ alert")
        self.assertEqual([v["term"] for v in found], ["jaldi", "ಬೇಗ", "बहुत", "simple"])  # kinds in order: time, quantity, ease
        self.assertEqual(found[0]["kind"], "time")
        self.assertIn("hours or days", found[0]["question"])
        self.assertEqual(verify.vague_terms("Fastest route; simplest; goodwill"), [])  # no substring matches
        self.assertEqual(verify.vague_terms("cardamom stock falls below 50 kg alert the owner to reorder"), [])

    def test_verify_rule_carries_vague_without_changing_status(self):
        r = verify.verify_rule({"title": "Quick delivery", "condition": "an order is placed", "action": "deliver quickly", "source_quote": "deliver quickly"}, "we deliver quickly")
        self.assertEqual(r["status"], "verified")
        self.assertEqual([v["term"] for v in r["vague"]], ["quickly", "quick"])

    def test_document_lists_clarification_questions(self):
        rule = Rule(id="r1", title="Quick delivery", condition="an order is placed", action="deliver quickly", source_quote="deliver quickly", approved_at="t", approved_by="o")
        doc = compiler.document(CompileIn(rules=[rule], transcript="deliver quickly", mode="business"))
        qs = [q for q in doc["open_questions"] if q.startswith("Clarify")]
        self.assertEqual(len(qs), 2)
        self.assertIn('Clarify "quickly" in Quick delivery: How soon exactly?', qs[0])


class BreadthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(config, "DATA_DIR", Path(self.tmp.name)), patch.object(config, "USE_REAL_SARVAM", True), patch.object(config, "SARVAM_API_KEY", "k")]
        for p in self.patches: p.start()
        sarvam._dicts.clear()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        for p in self.patches: p.stop()
        self.tmp.cleanup()

    def test_transliterate_only_touches_roman_lines_and_keeps_speaker_tags(self):
        fake = fake_client([(200, {"transliterated_text": "डिलीवरी 2 घंटे में"})])
        with patch("services.sarvam.httpx.AsyncClient", return_value=fake):
            r = self.client.post("/api/transliterate", json={"text": "[Owner] delivery 2 ghante me\n[Manager] हमारा स्टाफ हिंदी बोलता है\n", "target": "hindi"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["text"], "[Owner] डिलीवरी 2 घंटे में\n[Manager] हमारा स्टाफ हिंदी बोलता है\n")
        self.assertTrue(r.json()["changed"])
        sent = fake.post.call_args.kwargs["json"]
        self.assertEqual((sent["input"], sent["source_language_code"], sent["target_language_code"], sent["numerals_format"]), ("delivery 2 ghante me", "en-IN", "hi-IN", "international"))
        self.assertEqual(fake.post.call_count, 1)  # the Devanagari line was never sent

    def test_transliterate_english_target_is_a_no_op(self):
        r = self.client.post("/api/transliterate", json={"text": "hello", "target": "english"})
        self.assertEqual(r.json(), {"text": "hello", "changed": False})

    def test_acronyms_become_spelled_pronunciations(self):
        self.assertEqual(sarvam.acronym_pronunciations(["HDFC", "UPI", "Indore", "a", "GST", "TOOLONGACRONYM"]), {"HDFC": "H D F C", "UPI": "U P I", "GST": "G S T"})

    def test_pronunciation_dictionary_created_once_and_used_by_tts(self):
        fake = fake_client([(200, {"dictionary_id": "p_123"}), (200, {"audios": ["UklGRg=="]}), (200, {"audios": ["UklGRg=="]})])
        with patch.object(config, "SARVAM_TTS_MODEL", "bulbul:v4-flash"), patch.object(config, "SARVAM_TTS_SPEAKER", ""), patch("services.sarvam.httpx.AsyncClient", return_value=fake):
            r1 = self.client.post("/api/tts", json={"text": "HDFC बैंक", "lang": "hindi", "keyterms": ["HDFC", "Indore"]})
            r2 = self.client.post("/api/tts", json={"text": "UPI भुगतान", "lang": "hindi", "keyterms": ["HDFC", "Indore"]})
        self.assertEqual((r1.status_code, r2.status_code), (200, 200))
        calls = fake.post.call_args_list
        self.assertTrue(calls[0].args[0].endswith("/text-to-speech/pronunciation-dictionary"))
        self.assertEqual(calls[0].kwargs["files"]["file"][2], "application/json")
        self.assertEqual(json.loads(calls[0].kwargs["files"]["file"][1]), {"pronunciations": {"hi-IN": {"HDFC": "H D F C"}}})
        self.assertEqual(calls[1].kwargs["json"]["dict_id"], "p_123")
        self.assertEqual(calls[2].kwargs["json"]["dict_id"], "p_123")
        self.assertEqual(len(calls), 3)  # dictionary created once, reused for the second request

    def test_tts_without_acronyms_sends_no_dictionary(self):
        fake = fake_client([(200, {"audios": ["UklGRg=="]})])
        with patch("services.sarvam.httpx.AsyncClient", return_value=fake):
            r = self.client.post("/api/tts", json={"text": "नमस्ते", "lang": "hindi", "keyterms": ["Indore", "cardamom"]})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("dict_id", fake.post.call_args.kwargs["json"])

    def test_colloquial_register_uses_mayura_and_falls_back_to_formal(self):
        fake = fake_client([(200, {"translated_text": "पाँच requirements approve हो गए"})])
        with patch("services.sarvam.httpx.AsyncClient", return_value=fake):
            out = asyncio.run(sarvam.translate_colloquial("Five requirements approved", "hindi"))
        self.assertEqual(out, "पाँच requirements approve हो गए")
        sent = fake.post.call_args.kwargs["json"]
        self.assertEqual((sent["model"], sent["mode"]), ("mayura:v1", "code-mixed"))
        sarvam._translations.clear()
        fake = fake_client([(400, {"error": "unsupported"}), (200, {"translated_text": "औपचारिक"})])
        with patch("services.sarvam.httpx.AsyncClient", return_value=fake):
            out = asyncio.run(sarvam.translate_colloquial("Formal text", "hindi"))
        self.assertEqual(out, "औपचारिक")
        self.assertEqual(fake.post.call_args.kwargs["json"]["model"], "sarvam-translate:v1")


if __name__ == "__main__":
    unittest.main()
