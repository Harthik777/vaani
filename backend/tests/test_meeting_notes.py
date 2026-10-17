"""Meeting upload (batch diarization) and notes photo (Doc AI) routes, with the SDK calls mocked."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from services import config, sarvam

DIARIZED = {
    "transcript": "हम Indore में मसालों का थोक व्यापार करते हैं। हमारा staff सिर्फ हिंदी बोलता है।",
    "timestamps": {"words": ["a", "b"], "start_time_seconds": [0.0, 10.2], "end_time_seconds": [9.5, 19.9]},
    "diarized_transcript": {"entries": [
        {"transcript": "हम Indore में मसालों का थोक व्यापार करते हैं। जब इलायची का stock 50 kg से कम हो जाए तो app मुझे alert दे।", "start_time_seconds": 0.01, "end_time_seconds": 9.49, "speaker_id": "1"},
        {"transcript": "हमारा staff सिर्फ हिंदी बोलता है। alert तब आना चाहिए जब stock 100 kg से कम हो।", "start_time_seconds": 10.19, "end_time_seconds": 19.93, "speaker_id": "0"},
        {"transcript": "20,000 रुपये से ज़्यादा के हर order को मेरी मंज़ूरी चाहिए।", "start_time_seconds": 20.43, "end_time_seconds": 25.45, "speaker_id": "1"},
    ]},
    "language_code": "hi-IN",
}


def digitise_zip(blocks_by_page):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("notes.png/notes.html", "<html></html>")
        for i, blocks in enumerate(blocks_by_page, 1):
            z.writestr(f"notes.png/metadata/page_{i:03d}.json", json.dumps({"page_num": i, "blocks": blocks}, ensure_ascii=False))
        z.writestr("manifest.json", "{}")
    return buf.getvalue()


class MeetingNotesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(config, "DATA_DIR", Path(self.tmp.name)), patch.object(config, "USE_REAL_SARVAM", True),
                        patch.object(config, "SARVAM_API_KEY", "k"), patch.object(config, "SARVAM_STT_MODEL", "saaras:v4")]
        for p in self.patches:
            p.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_meeting_upload_returns_speaker_lines_and_evidence(self):
        seen = {}
        def fake_job(path, language_code, num_speakers, keyterms):
            seen.update(path=path, language_code=language_code, num_speakers=num_speakers, keyterms=keyterms)
            return DIARIZED
        with patch.object(sarvam, "_meeting_job", fake_job):
            r = self.client.post("/api/stt/meeting", files={"audio": ("call.wav", b"RIFFfake", "audio/wav")},
                                 data={"lang": "hindi", "num_speakers": "2", "keyterms": json.dumps(["इलायची"])})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual((seen["language_code"], seen["num_speakers"], seen["keyterms"]), ("hi-IN", 2, ["इलायची"]))
        self.assertEqual(body["speakers"], ["Speaker 1", "Speaker 2"])  # first voice heard is Speaker 1, whatever Sarvam's id
        self.assertEqual([l["speaker"] for l in body["lines"]], ["Speaker 1", "Speaker 2", "Speaker 1"])
        self.assertTrue(body["transcript"].startswith("[Speaker 1] हम Indore"))
        self.assertEqual(body["transcript"].count("\n"), 2)
        ev = body["evidence"]
        self.assertEqual(len(ev["sha256"]), 64)
        self.assertEqual(ev["timestamps"]["start_time_seconds"], [0.01, 10.19, 20.43])
        self.assertEqual(ev["timestamps"]["words"], [l["text"] for l in body["lines"]])
        self.assertIn(body["lines"][1]["text"], ev["transcript"])
        # the recording itself is retrievable as evidence with its key
        got = self.client.get("/api/evidence/" + ev["id"], headers={"Authorization": "Bearer " + ev["key"]})
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.content, b"RIFFfake")
        # the diarized lines go straight through extraction (demo off) grounding: quotes must be in the transcript
        self.assertTrue(all(l["text"] in body["transcript"] for l in body["lines"]))

    def test_meeting_upload_is_honest_without_sarvam_or_on_failure(self):
        with patch.object(config, "USE_REAL_SARVAM", False):
            r = self.client.post("/api/stt/meeting", files={"audio": ("call.wav", b"x", "audio/wav")}, data={"lang": "hindi"})
            self.assertEqual(r.status_code, 503)
        def boom(*a, **k):
            raise RuntimeError("batch job ended in state Failed")
        with patch.object(sarvam, "_meeting_job", boom):
            r = self.client.post("/api/stt/meeting", files={"audio": ("call.wav", b"x", "audio/wav")}, data={"lang": "hindi"})
            self.assertEqual(r.status_code, 502)
            self.assertIn("type the transcript", r.json()["detail"])
        self.assertEqual(self.client.post("/api/stt/meeting", files={"audio": ("a.txt", b"x", "text/plain")}).status_code, 415)

    def test_meeting_without_diarization_falls_back_to_one_speaker(self):
        with patch.object(sarvam, "_meeting_job", lambda *a, **k: {"transcript": "सब कुछ ठीक है।", "diarized_transcript": None}):
            r = self.client.post("/api/stt/meeting", files={"audio": ("call.wav", b"x", "audio/wav")}, data={"lang": "hindi"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["speakers"], ["Speaker 1"])
        self.assertEqual(r.json()["transcript"], "[Speaker 1] सब कुछ ठीक है।")

    def test_notes_photo_becomes_transcript_lines(self):
        z = digitise_zip([[{"reading_order": 2, "text": "2. बजट: 1.5 लाख रुपये"}, {"reading_order": 1, "text": "दुकान के लिए ऐप की ज़रूरतें\n\n1. स्टॉक 50 किलो से कम होने पर अलर्ट"}]])
        with patch.object(sarvam, "_digitise_job", lambda *a, **k: sarvam.parse_digitise_zip(z)):
            r = self.client.post("/api/notes", files={"file": ("notes.png", b"\x89PNG", "image/png")}, data={"lang": "hindi"})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["lines"], ["दुकान के लिए ऐप की ज़रूरतें", "1. स्टॉक 50 किलो से कम होने पर अलर्ट", "2. बजट: 1.5 लाख रुपये"])
        self.assertEqual(body["transcript"].split("\n")[0], "[Notes] दुकान के लिए ऐप की ज़रूरतें")
        self.assertEqual(body["pages"], 1)

    def test_notes_route_is_honest(self):
        with patch.object(config, "USE_REAL_SARVAM", False):
            self.assertEqual(self.client.post("/api/notes", files={"file": ("n.png", b"x", "image/png")}).status_code, 503)
        self.assertEqual(self.client.post("/api/notes", files={"file": ("n.txt", b"x", "text/plain")}).status_code, 415)
        with patch.object(sarvam, "_digitise_job", lambda *a, **k: {"text": "", "lines": [], "pages": 1}):
            self.assertEqual(self.client.post("/api/notes", files={"file": ("n.png", b"x", "image/png")}).status_code, 502)

    def test_health_advertises_batch_and_doc_ai(self):
        sv = self.client.get("/api/health").json()["sarvam"]
        self.assertEqual((sv["diarization"], sv["doc_ai"]), ("batch", "digitise"))


if __name__ == "__main__":
    unittest.main()
