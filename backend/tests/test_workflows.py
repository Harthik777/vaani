"""Regression tests for the audit's data integrity and workflow failures."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app
from services import config, llm, sarvam, store
import mocks

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = patch.object(config, "DATA_DIR", Path(self.tmp.name))
        self.directory.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.directory.stop()
        self.tmp.cleanup()

    def rule(self, **changes):
        return {"id": "r1", "title": "Sample", "condition": "source condition", "action": "source action", "source_quote": "source condition", "approved_at": "2026-10-15T10:00:00Z", "approved_by": "Reviewer", **changes}

    def publish(self, mode="awareness", **changes):
        return self.client.post("/api/portals", json={"mode": mode, "rules": [self.rule()], "transcript": "source condition", "demo": True, **changes})

    def test_all_modes_all_languages_are_explicit_demos(self):
        for mode, bag in mocks.MOCKS_BY_MODE.items():
            for language in ["hindi", "marathi", "tamil", "telugu", "bengali", "kannada", "english"]:
                with self.subTest(mode=mode, language=language):
                    text = bag["transcript"][language]
                    self.assertNotIn("??", text)
                    response = self.client.post("/api/stt", data={"demo": "true", "mode": mode, "lang": language})
                    self.assertEqual(response.json()["transcript"], text)
                    extraction = self.client.post("/api/extract", json={"mode": mode, "transcript": text, "demo": True}).json()
                    self.assertTrue(extraction["rules"])
                    self.assertNotIn("followup", extraction)
                    self.assertTrue(all(r["source_quote"] in text for r in extraction["rules"]))

    def test_edited_demo_cannot_masquerade_as_extraction(self):
        self.assertEqual(self.client.post("/api/extract", json={"transcript": "a different deal", "mode": "deals", "demo": True}).status_code, 422)

    def test_unconfigured_live_calls_never_return_demo(self):
        with patch.object(config, "USE_REAL_LLM", False), patch.object(config, "USE_REAL_SARVAM", False):
            self.assertEqual(self.client.post("/api/extract", json={"transcript": "my real words"}).status_code, 503)
            response = self.client.post("/api/stt", files={"audio": ("a.webm", b"audio", "audio/webm")})
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("transcript", response.json())

    def test_unknown_mode_language_and_missing_audio_rejected(self):
        self.assertEqual(self.client.post("/api/extract", json={"mode": "unknown", "transcript": "x"}).status_code, 422)
        self.assertEqual(self.client.post("/api/stt", data={"demo": "true", "lang": "unknown"}).status_code, 422)
        self.assertEqual(self.client.post("/api/stt").status_code, 422)

    def test_live_prompt_router_and_source_grounding(self):
        for mode in mocks.MOCKS_BY_MODE:
            with self.subTest(mode=mode), patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "test"), patch.object(llm, "complete_json", new=AsyncMock(return_value={"rules": [self.rule()], "review_notes": []})) as call:
                response = self.client.post("/api/extract", json={"mode": mode, "transcript": "source condition"})
                self.assertEqual(response.status_code, 200)
                self.assertIn(llm.MODE_PROMPTS[mode], call.call_args.args[0])
                self.assertIn("not an interviewer", call.call_args.args[0])

    def test_hallucinated_quotes_and_bad_llm_results_rejected(self):
        for response in ({"rules": []}, {"unexpected": []}):
            with self.subTest(response=response), patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "test"), patch.object(llm, "complete_json", new=AsyncMock(return_value=response)):
                self.assertEqual(self.client.post("/api/extract", json={"transcript": "source condition"}).status_code, 502)
        # An invented quote is not silently dropped: it is returned as a visible rejection.
        with patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "test"), patch.object(llm, "complete_json", new=AsyncMock(return_value={"rules": [self.rule(source_quote="not in source"), self.rule(id="r2")]})):
            body = self.client.post("/api/extract", json={"transcript": "source condition"}).json()
            self.assertEqual([r["id"] for r in body["rules"]], ["r2"])
            self.assertEqual(body["rejected"][0]["reason"], "Quote not found in what was said")
        # Duplicate ids are made unique and a malformed rule is rejected on its own, not the whole batch.
        with patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "test"), patch.object(llm, "complete_json", new=AsyncMock(return_value={"rules": [self.rule(), self.rule(), {"id": "r9", "title": "Bad", "confidence": "SURE"}]})):
            body = self.client.post("/api/extract", json={"transcript": "source condition"}).json()
            self.assertEqual(len({r["id"] for r in body["rules"]}), 2)
            self.assertEqual(body["rejected"][0]["reason"], "Malformed requirement from the AI")
        # A transient provider error is retried once.
        with patch.object(config, "USE_REAL_LLM", True), patch.object(config, "LLM_API_KEY", "test"), patch.object(llm, "complete_json", new=AsyncMock(side_effect=[RuntimeError("503"), {"rules": [self.rule()]}])):
            self.assertEqual(self.client.post("/api/extract", json={"transcript": "source condition"}).status_code, 200)

    def test_stt_preserves_mime_language_and_provider_timestamps(self):
        result = {"transcript": "actual words", "timestamps": {"words": ["actual words"], "start_time_seconds": [0], "end_time_seconds": [1]}}
        with patch.object(config, "USE_REAL_SARVAM", True), patch.object(config, "SARVAM_API_KEY", "test"), patch.object(sarvam, "transcribe", new=AsyncMock(return_value=result)) as call:
            response = self.client.post("/api/stt", data={"lang": "tamil", "mode": "audit"}, files={"audio": ("a.webm", b"recorded", "audio/webm")})
            self.assertEqual(response.json()["timestamps"], result["timestamps"])
            self.assertEqual(call.call_args.args, (b"recorded", "tamil", "a.webm", "audio/webm"))

    def test_documents_and_screens_preserve_only_submitted_rules(self):
        for mode in mocks.MOCKS_BY_MODE:
            for rules in ([], [self.rule(action="ONLY THIS ACTION", exception="explicit exception")]):
                with self.subTest(mode=mode, rules=rules):
                    body = {"mode": mode, "rules": rules}
                    document = self.client.post("/api/brd", json=body).json()
                    screens = self.client.post("/api/screenspec", json=body).json()
                    self.assertEqual(len(document["business_rules"]), len(rules))
                    self.assertEqual(document["mode"], mode)
                    if rules:
                        self.assertIn("UNLESS explicit exception", document["business_rules"][0]["rule"])
                        self.assertIn("ONLY THIS ACTION", json.dumps(screens))
                    self.assertNotIn("Grade-B", json.dumps(document))

    def test_invalid_clip_ranges_rejected(self):
        for changes in ({"start": 0}, {"start": 2, "end": 1, "evidence_id": "a"}, {"start": 0, "end": 2}):
            self.assertEqual(self.client.post("/api/brd", json={"rules": [self.rule(**changes)]}).status_code, 422)

    def test_evidence_hash_and_access_control(self):
        content = b"original audio bytes"
        result = self.client.post("/api/evidence", files={"audio": ("a.webm", content, "audio/webm")}).json()
        self.assertEqual(result["sha256"], hashlib.sha256(content).hexdigest())
        url = "/api/evidence/" + result["id"]
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(url, headers={"Authorization": "Bearer wrong"}).status_code, 404)
        self.assertEqual(self.client.get(url, headers={"Authorization": "Bearer " + result["key"]}).content, content)

    def test_empty_and_wrong_type_audio_rejected(self):
        self.assertEqual(self.client.post("/api/evidence", files={"audio": ("a.webm", b"", "audio/webm")}).status_code, 413)
        self.assertEqual(self.client.post("/api/evidence", files={"audio": ("a.html", b"x", "text/html")}).status_code, 415)

    def test_public_portal_is_durable_and_has_preview(self):
        response = self.publish(metadata={"title": "<script>alert(1)</script>"})
        self.assertEqual(response.status_code, 200)
        item = response.json()
        self.assertTrue(item["public"])
        with TestClient(app) as other_client:
            self.assertEqual(other_client.get("/api/portals/" + item["id"]).json()["rules"][0]["id"], "r1")
        html = self.client.get("/p/" + item["id"]).text
        self.assertNotIn("<script>alert", html)
        self.assertIn("og:image", html)
        self.assertEqual(self.client.get("/p/" + item["id"] + "/card.svg").status_code, 200)
        png = self.client.get("/p/" + item["id"] + "/card.png")
        self.assertEqual(png.headers["content-type"], "image/png")
        self.assertTrue(png.content.startswith(b"\x89PNG"))

    def test_private_modes_require_capability_and_do_not_leak_previews(self):
        for mode in ("business", "audit", "deals"):
            item = self.publish(mode).json()
            self.assertFalse(item["public"])
            self.assertIn("#key=", item["url"])
            url = "/api/portals/" + item["id"]
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.get("/p/" + item["id"]).status_code, 404)
            self.assertEqual(self.client.get(url, headers={"Authorization": "Bearer " + item["key"]}).status_code, 200)
            row = store.get(item["id"], "portal", internal=True)
            self.assertNotEqual(row["key_hash"], item["key"])

    def test_portal_audio_requires_portal_access_and_membership(self):
        evidence = self.client.post("/api/evidence", files={"audio": ("a.webm", b"audio", "audio/webm")}).json()
        item = self.publish("audit", evidence=[evidence], rules=[self.rule(evidence_id=evidence["id"], start=0, end=1)]).json()
        url = f'/api/portals/{item["id"]}/audio/{evidence["id"]}'
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(url, headers={"Authorization": "Bearer " + item["key"]}).content, b"audio")
        public = self.publish().json()
        self.assertEqual(self.client.get(f'/api/portals/{public["id"]}/audio/{evidence["id"]}').status_code, 404)
        data = self.client.get("/api/portals/" + item["id"], headers={"Authorization": "Bearer " + item["key"]}).json()
        self.assertNotIn("key", data["evidence"][0])

    def test_publication_rejects_missing_approval_or_evidence(self):
        for kwargs in ({"rules": []}, {"rules": [self.rule(approved_at=None)]}, {"rules": [self.rule(approved_by=None)]}, {"rules": [self.rule(evidence_id="missing")]}, {"rules": [self.rule(source_quote="invented")]}, {"rules": [self.rule(), self.rule()]}):
            self.assertEqual(self.publish(**kwargs).status_code, 422)

    def test_publisher_key_enforced_when_configured(self):
        with patch.object(config, "PUBLISH_API_KEY", "publisher-secret"):
            self.assertEqual(self.publish().status_code, 401)
            response = self.client.post("/api/portals", headers={"Authorization": "Bearer publisher-secret"}, json={"mode": "awareness", "rules": [self.rule()], "transcript": "source condition"})
            self.assertEqual(response.status_code, 200)

    def test_ticket_is_durable_and_truthfully_queued(self):
        item = self.client.post("/api/tickets", json={"kind": "maintenance", "asset": "Pier 4", "description": "Reviewed actions"}).json()
        self.assertIn("queued locally", item["status"])
        self.assertEqual(store.get(item["id"], "ticket", item["key"])["payload"]["asset"], "Pier 4")

    def test_work_order_dispatch_success_and_failure_are_distinguished(self):
        import httpx
        fake = AsyncMock()
        fake.__aenter__.return_value = fake
        response = httpx.Response(200, request=httpx.Request("POST", "https://example.test/tickets"))
        fake.post.return_value = response
        with patch.object(config, "WORK_ORDER_URL", "https://example.test/tickets"), patch("routes.tickets.httpx.AsyncClient", return_value=fake):
            first = self.client.post("/api/tickets", json={"kind": "maintenance", "asset": "Pier 4", "description": "Actions"}).json()
            self.assertEqual(first["status"], "accepted by configured dispatch service")
            self.assertEqual(fake.post.call_args.kwargs["headers"]["Idempotency-Key"], first["id"])
            fake.post.side_effect = httpx.ConnectError("offline")
            second = self.client.post("/api/tickets", json={"kind": "maintenance", "asset": "Pier 4", "description": "Actions"}).json()
            self.assertIn("dispatch service unavailable", second["status"])

    def test_sarvam_http_adapter_uses_actual_audio_and_language_codes(self):
        import asyncio
        import httpx
        fake = AsyncMock()
        fake.__aenter__.return_value = fake
        fake.post.return_value = httpx.Response(200, json={"transcript": "source words"}, request=httpx.Request("POST", "https://api.sarvam.ai/speech-to-text"))
        with patch("services.sarvam.httpx.AsyncClient", return_value=fake):
            result = asyncio.run(sarvam.transcribe(b"original", "bengali", "source.ogg", "audio/ogg"))
            self.assertEqual(result["transcript"], "source words")
            self.assertEqual(fake.post.call_args.kwargs["files"]["file"], ("source.ogg", b"original", "audio/ogg"))
            self.assertEqual(fake.post.call_args.kwargs["data"]["language_code"], "bn-IN")

if __name__ == "__main__":
    unittest.main()
