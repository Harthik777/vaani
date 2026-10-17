"""Demo voices: Bulbul reads the meeting demo in two voices and each clip is stored as labelled, synthesised evidence."""
import base64
import io
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app
from routes import demo
from services import config, sarvam
import mocks


def tiny_wav(seconds=0.5, rate=8000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(b"\x00\x00" * int(rate * seconds))
    return base64.b64encode(buf.getvalue()).decode()


class DemoVoiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(config, "DATA_DIR", Path(self.tmp.name)), patch.object(config, "USE_REAL_LLM", False)]
        for p in self.patches:
            p.start()
        demo._ready.clear()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_text_only_without_sarvam(self):
        with patch.object(config, "USE_REAL_SARVAM", False):
            self.assertEqual(self.client.post("/api/demo/voices", json={"lang": "hindi"}).status_code, 503)

    def test_two_voices_become_playable_labelled_evidence(self):
        calls = []
        async def fake_synthesize(text, lang, dict_id=None, speaker=None):
            calls.append((lang, speaker)); return [tiny_wav()]
        with patch.object(config, "USE_REAL_SARVAM", True), patch.object(config, "SARVAM_API_KEY", "k"), patch.object(sarvam, "synthesize", fake_synthesize):
            body = self.client.post("/api/demo/voices", json={"lang": "hindi"}).json()
            lines = [l for l in mocks.MEETING["transcript"]["hindi"].split("\n") if l.startswith("[")]
            self.assertEqual(len(body["evidence"]), len(lines))
            self.assertFalse(body["cached"])
            self.assertEqual({c[1] for c in calls}, {demo.DEMO_VOICES["hindi"]["Owner"], demo.DEMO_VOICES["hindi"]["Manager"]})
            first = body["evidence"][0]
            self.assertEqual(first["speaker"], "Owner")
            self.assertTrue(first["synthetic"])
            self.assertEqual(first["duration"], 0.5)
            self.assertIn(first["transcript"], mocks.MEETING["transcript"]["hindi"])
            self.assertEqual(first["timestamps"]["end_time_seconds"], [0.5])
            audio = self.client.get("/api/evidence/" + first["id"], headers={"Authorization": "Bearer " + first["key"]})
            self.assertEqual(audio.status_code, 200)
            self.assertEqual(audio.headers["content-type"], "audio/wav")
            self.assertTrue(self.client.post("/api/demo/voices", json={"lang": "hindi"}).json()["cached"])
            # the quotes the demo extracts fall inside single spoken lines, so every requirement gets a clip
            for r in mocks.MEETING["rules"]["hindi"]:
                self.assertTrue(any(r["source_quote"] in e["transcript"] for e in body["evidence"]), r["source_quote"])


if __name__ == "__main__":
    unittest.main()
