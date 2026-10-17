"""Deadlines from speech (grounded or marked to confirm), the .ics file, Google Calendar links, and the OAuth push gates."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app
from services import config, llm, deadlines, google_sync, store
import mocks

EN = mocks.MEETING["transcript"]["english"]
RULES = mocks.MEETING["rules"]["english"]


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(config, "DATA_DIR", Path(self.tmp.name)), patch.object(config, "USE_REAL_LLM", False), patch.object(config, "USE_REAL_SARVAM", False),
                        patch.object(config, "GOOGLE_CLIENT_ID", ""), patch.object(config, "GOOGLE_CLIENT_SECRET", "")]
        for p in self.patches:
            p.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def body(self):
        return {"mode": "business", "rules": RULES, "transcript": EN, "metadata": {"title": "Spice stock app"}, "answers": [{"key": "timeline", "question": "By when?", "answer": "Before Diwali, so by 5 November 2026.", "speaker": "Owner"}]}

    def test_deadlines_are_grounded_or_marked_to_confirm(self):
        self.assertEqual(self.client.post("/api/brd/deadlines", json=self.body()).status_code, 503)
        fake = {"deadlines": [{"title": "Launch before Diwali", "date": "2026-11-05", "kind": "deadline", "source_quote": "Before Diwali, so by 5 November 2026.", "note": "Owner's timeline answer"},
                              {"title": "Daily sales report", "date": "2026-10-19", "kind": "recurring", "source_quote": "not the real words", "note": "every evening"},
                              {"title": "bad", "date": "sometime", "kind": "deadline", "source_quote": "", "note": ""}]}
        with patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "test"), patch.object(llm, "complete_json", new=AsyncMock(return_value=fake)):
            r = self.client.post("/api/brd/deadlines", json=self.body())
        self.assertEqual(r.status_code, 200, r.text)
        found = r.json()["deadlines"]
        self.assertEqual([d["status"] for d in found], ["grounded", "confirm"])  # the undated entry is dropped
        self.assertEqual(found[0]["source_quote"], "Before Diwali, so by 5 November 2026.")
        self.assertIsNone(found[1]["source_quote"])
        self.assertIn("calendar.google.com/calendar/render?action=TEMPLATE", found[0]["google_link"])
        self.assertIn("dates=20261105/20261106", found[0]["google_link"])
        ics = self.client.post("/api/brd/ics", json={"deadlines": found, "project": "Spice stock app"})
        self.assertEqual(ics.status_code, 200)
        self.assertTrue(ics.headers["content-type"].startswith("text/calendar"))
        text = ics.text
        self.assertEqual(text.count("BEGIN:VEVENT"), 2)
        self.assertIn("DTSTART;VALUE=DATE:20261105", text)
        self.assertIn("RRULE:FREQ=DAILY;COUNT=30", text)
        self.assertIn("SUMMARY:Launch before Diwali", text)

    def test_google_is_honest_when_not_configured_and_gated_when_it_is(self):
        self.assertEqual(self.client.get("/api/google/status?email=a@b.co").json(), {"configured": False, "connected": False})
        self.assertEqual(self.client.get("/api/google/start").status_code, 503)
        self.assertEqual(self.client.post("/api/google/push", json={**self.body(), "email": "a@b.co"}).status_code, 503)
        with patch.object(config, "GOOGLE_CLIENT_ID", "id"), patch.object(config, "GOOGLE_CLIENT_SECRET", "secret"):
            self.assertTrue(self.client.get("/api/health").json()["google"])
            url = self.client.get("/api/google/start?email=a@b.co").json()["url"]
            self.assertIn("accounts.google.com", url); self.assertIn("drive.file", url); self.assertIn("calendar.events", url)
            self.assertEqual(self.client.post("/api/google/push", json={**self.body(), "email": "a@b.co"}).status_code, 401)
            store.put_account("google:a@b.co", {"refresh_token": "r", "access_token": "t", "expires_at": 9e12})
            self.assertTrue(self.client.get("/api/google/status?email=A@b.co").json()["connected"])
            calls = []
            class FakeClient:
                async def __aenter__(self): return self
                async def __aexit__(self, *a): return False
                async def post(self, url, **kw):
                    calls.append(url)
                    import httpx
                    if "upload/drive" in url:
                        return httpx.Response(200, json={"id": "doc1", "webViewLink": "https://docs.google.com/document/d/doc1/edit"}, request=httpx.Request("POST", url))
                    return httpx.Response(200, json={"htmlLink": "https://calendar.google.com/event?eid=1"}, request=httpx.Request("POST", url))
            with patch.object(google_sync.httpx, "AsyncClient", return_value=FakeClient()):
                r = self.client.post("/api/google/push", json={**self.body(), "email": "a@b.co", "deadlines": [{"id": "d1", "title": "Launch", "date": "2026-11-05", "kind": "deadline", "note": "x"}]})
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json()["doc_url"], "https://docs.google.com/document/d/doc1/edit")
            self.assertEqual(r.json()["events"][0]["link"], "https://calendar.google.com/event?eid=1")
            self.assertTrue(any("upload/drive/v3/files" in u for u in calls) and any("calendar/v3" in u for u in calls))


if __name__ == "__main__":
    unittest.main()
