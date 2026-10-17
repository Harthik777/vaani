"""The WhatsApp interview bot: session state, TwiML replies, voice notes through Sarvam, the brd command."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app
from services import config, wabot, sarvam
import mocks


class WaBotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(config, "DATA_DIR", Path(self.tmp.name)), patch.object(config, "TWILIO_ACCOUNT_SID", "AC1"),
                        patch.object(config, "TWILIO_AUTH_TOKEN", "t"), patch.object(config, "TWILIO_WHATSAPP_FROM", "whatsapp:+1415"),
                        patch.object(config, "PUBLIC_API_URL", "http://localhost:8000")]
        for p in self.patches:
            p.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def post(self, **fields):
        data = {"From": "whatsapp:+919876543210", "Body": "", "NumMedia": "0", **fields}
        r = self.client.post("/api/whatsapp/inbound", data=data)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.headers["content-type"].startswith("application/xml"))
        return r.text

    def test_greeting_and_language_switch(self):
        xml = self.post(Body="hi")
        self.assertIn("<Response><Message><Body>", xml)
        self.assertIn("VAANI", xml)
        xml = self.post(Body="lang kannada")
        self.assertIn("ನಮಸ್ಕಾರ", xml)
        self.assertEqual(wabot.load("whatsapp:+919876543210")["lang"], "kannada")

    def test_text_message_becomes_transcript_and_a_question_comes_back(self):
        with patch.object(config, "USE_REAL_SARVAM", False), patch.object(config, "USE_REAL_LLM", False):
            xml = self.post(Body="हमें स्टॉक ट्रैक करने के लिए ऐप चाहिए")
        s = wabot.load("whatsapp:+919876543210")
        self.assertEqual(s["tx"], "[Owner] हमें स्टॉक ट्रैक करने के लिए ऐप चाहिए")
        self.assertEqual(s["lang"], "hindi")  # detected from the script
        self.assertIn("✔ सुना", xml)
        self.assertIn("complete", xml)  # the next checklist question with the completeness figure
        self.assertIsNotNone(s["pending_key"])
        with patch.object(config, "USE_REAL_SARVAM", False), patch.object(config, "USE_REAL_LLM", False):
            self.post(Body="लगभग 12 लोग")
        s = wabot.load("whatsapp:+919876543210")
        self.assertEqual(len(s["answers"]), 1)
        self.assertIn("[Owner] लगभग 12 लोग", s["tx"])

    def test_voice_note_is_fetched_from_twilio_and_transcribed(self):
        fetched = {}
        async def fake_fetch(url):
            fetched["url"] = url
            return b"OGGdata", "audio/ogg"
        transcribed = {}
        async def fake_transcribe(data, lang, filename="", content_type="", keyterms=None):
            transcribed.update(lang=lang, filename=filename, content_type=content_type)
            return {"transcript": "इलायची का stock 50 kg से कम हो तो alert"}
        with patch.object(config, "USE_REAL_SARVAM", True), patch.object(config, "SARVAM_API_KEY", "k"), patch.object(config, "USE_REAL_LLM", False), \
             patch.object(wabot, "fetch_media", fake_fetch), patch.object(sarvam, "transcribe", fake_transcribe):
            xml = self.post(NumMedia="1", MediaUrl0="https://api.twilio.com/media/1", MediaContentType0="audio/ogg")
        self.assertEqual(fetched["url"], "https://api.twilio.com/media/1")
        self.assertEqual((transcribed["lang"], transcribed["filename"], transcribed["content_type"]), ("hindi", "note.ogg", "audio/ogg"))
        self.assertIn("इलायची", wabot.load("whatsapp:+919876543210")["tx"])
        self.assertIn("✔ सुना", xml)

    def test_brd_command_extracts_and_publishes_a_portal(self):
        tx = mocks.MEETING["transcript"]["hindi"]
        s = wabot.load("whatsapp:+919876543210"); s["tx"] = tx; s["lang"] = "hindi"; wabot.save(s)
        fake_rules = [{**r, "speaker": "Owner"} for r in mocks.MEETING["rules"]["hindi"]]
        async def fake_extract(body):
            return {"rules": fake_rules, "review_notes": [], "rejected": [], "demo": False, "brain": "test"}
        with patch("routes.extract.extract", fake_extract), patch.object(config, "USE_REAL_LLM", False), patch.object(config, "USE_REAL_SARVAM", False):
            xml = self.post(Body="brd")
        self.assertIn("VAANI BRD", xml)
        self.assertIn("?portal=", xml)
        self.assertIn("#key=", xml)
        self.assertIn("5 requirements, 5 verified", xml)
        link = wabot.load("whatsapp:+919876543210")["portal"]
        ident, key = link.split("?portal=")[1].split("#key=")
        r = self.client.get("/api/portals/" + ident, headers={"Authorization": "Bearer " + key})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["brd"]["business_rules"]), 5)

    def test_reset_and_non_whatsapp_sender(self):
        s = wabot.load("whatsapp:+919876543210"); s["tx"] = "[Owner] x"; wabot.save(s)
        self.post(Body="new")
        self.assertEqual(wabot.load("whatsapp:+919876543210")["tx"], "")
        self.assertEqual(self.client.post("/api/whatsapp/inbound", data={"From": "+919876543210", "Body": "hi"}).status_code, 400)

    def test_twiml_escapes_and_media(self):
        xml = wabot.twiml([{"body": "a < b & c", "media": ["https://x/y.png"]}])
        self.assertIn("<Body>a &lt; b &amp; c</Body>", xml)
        self.assertIn("<Media>https://x/y.png</Media>", xml)


if __name__ == "__main__":
    unittest.main()
