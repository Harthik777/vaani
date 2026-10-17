"""WhatsApp hand-off through Twilio: number normalisation, honest 503 without credentials, request shape, media rules."""
import asyncio
import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
import httpx
from fastapi.testclient import TestClient
from main import app
from services import config, whatsapp


class WhatsAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(config, "DATA_DIR", Path(self.tmp.name))]
        for p in self.patches:
            p.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    @contextlib.contextmanager
    def creds(self):
        with patch.object(config, "TWILIO_ACCOUNT_SID", "ACtest"), patch.object(config, "TWILIO_AUTH_TOKEN", "tok"),              patch.object(config, "TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"):
            yield

    def test_number_normalisation(self):
        self.assertEqual(whatsapp.normalise("98765 43210"), "whatsapp:+919876543210")
        self.assertEqual(whatsapp.normalise("+91 98765-43210"), "whatsapp:+919876543210")
        self.assertEqual(whatsapp.normalise("whatsapp:+919876543210"), "whatsapp:+919876543210")
        self.assertEqual(whatsapp.normalise("0 98765 43210"), "whatsapp:+919876543210")
        with self.assertRaises(ValueError):
            whatsapp.normalise("12")

    def test_route_is_honest_without_credentials(self):
        r = self.client.post("/api/whatsapp/send", json={"to": "+919876543210", "summary": "x"})
        self.assertEqual(r.status_code, 503)
        self.assertIn("TWILIO_ACCOUNT_SID", r.json()["detail"])
        self.assertFalse(self.client.get("/api/health").json()["whatsapp"])

    def test_send_posts_twilio_message_with_text_and_portal_link(self):
        fake = AsyncMock(); fake.__aenter__.return_value = fake
        fake.post.return_value = httpx.Response(201, json={"sid": "SM1", "status": "queued"}, headers={"content-type": "application/json"},
                                                request=httpx.Request("POST", "https://api.twilio.com/x"))
        with patch.object(config, "USE_REAL_SARVAM", False), patch("services.whatsapp.httpx.AsyncClient", return_value=fake), self.creds():
            self.assertTrue(self.client.get("/api/health").json()["whatsapp"])
            r = self.client.post("/api/whatsapp/send", json={"to": "98765 43210", "portal_url": "http://localhost:8000/p/abc#key=k",
                                                             "title": "Spice stock app", "summary": "Five requirements. Reorder below 100 kg.", "lang": "hindi"})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual((body["sid"], body["status"], body["to"]), ("SM1", "queued", "whatsapp:+919876543210"))
        sent = fake.post.call_args.kwargs["data"]
        self.assertEqual(sent["From"], "whatsapp:+14155238886")
        self.assertEqual(sent["To"], "whatsapp:+919876543210")
        self.assertIn("Spice stock app", sent["Body"])
        self.assertIn("http://localhost:8000/p/abc#key=k", sent["Body"])
        self.assertNotIn("MediaUrl", sent)  # localhost is not reachable by WhatsApp
        self.assertTrue(fake.post.call_args.args[0].endswith("/Accounts/ACtest/Messages.json"))

    def test_media_only_when_public_https(self):
        with patch.object(config, "PUBLIC_API_URL", "http://localhost:8000"):
            self.assertFalse(whatsapp.public_media_allowed())
        with patch.object(config, "PUBLIC_API_URL", "https://abc123.ngrok-free.app"):
            self.assertTrue(whatsapp.public_media_allowed())

    def test_twilio_error_surfaces_as_502(self):
        fake = AsyncMock(); fake.__aenter__.return_value = fake
        fake.post.return_value = httpx.Response(400, json={"message": "Recipient has not joined the sandbox"}, headers={"content-type": "application/json"},
                                                request=httpx.Request("POST", "https://api.twilio.com/x"))
        with patch.object(config, "USE_REAL_SARVAM", False), patch("services.whatsapp.httpx.AsyncClient", return_value=fake), self.creds():
            r = self.client.post("/api/whatsapp/send", json={"to": "+919876543210", "summary": "x", "lang": "english"})
        self.assertEqual(r.status_code, 502)
        self.assertIn("sandbox", r.json()["detail"])

    def test_media_route_serves_only_known_wavs(self):
        (Path(self.tmp.name) / "media").mkdir()
        (Path(self.tmp.name) / "media" / "abc.wav").write_bytes(b"RIFF")
        self.assertEqual(self.client.get("/api/media/abc.wav").status_code, 200)
        self.assertEqual(self.client.get("/api/media/missing.wav").status_code, 404)
        self.assertEqual(self.client.get("/api/media/..%2Fvaani.sqlite3").status_code, 404)


if __name__ == "__main__":
    unittest.main()
