"""Google Drive (the BRD as a Google Doc) and Google Calendar (the inferred deadlines) through OAuth 2.0.

Free: create an OAuth client (type "Web application") in Google Cloud Console, add the redirect URI
http://localhost:8000/api/google/callback, enable the Drive API and the Calendar API, then in backend/.env:
  GOOGLE_CLIENT_ID=...
  GOOGLE_CLIENT_SECRET=...
Without these the routes answer 503 and the interface shows the credential-free path (.ics + "Add to Google Calendar").
Tokens are kept per Google account in the local store (refresh token), never sent anywhere but Google.
"""
import base64
import json
import secrets
import time

import httpx

from services import config, store

AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/userinfo.email openid"
_pending: dict[str, float] = {}


def enabled() -> bool:
    return bool(config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET)


def start_url(login_hint=""):
    state = secrets.token_urlsafe(16)
    _pending[state] = time.time()
    from urllib.parse import urlencode
    return AUTH + "?" + urlencode({"client_id": config.GOOGLE_CLIENT_ID, "redirect_uri": config.GOOGLE_REDIRECT, "response_type": "code", "scope": SCOPES,
                                   "access_type": "offline", "prompt": "consent", "include_granted_scopes": "true", "state": state, **({"login_hint": login_hint} if login_hint else {})}), state


def _account_id(email):
    return "google:" + email.strip().lower()


async def finish(code, state, client=None):
    """Exchange the code, learn the account's email, keep the refresh token. Returns the email."""
    if state not in _pending or time.time() - _pending.pop(state) > 600:
        raise ValueError("Sign-in expired or was not started here. Start again.")
    async with (client or httpx.AsyncClient(timeout=30)) as c:
        r = await c.post(TOKEN, data={"code": code, "client_id": config.GOOGLE_CLIENT_ID, "client_secret": config.GOOGLE_CLIENT_SECRET,
                                      "redirect_uri": config.GOOGLE_REDIRECT, "grant_type": "authorization_code"})
        r.raise_for_status()
        tok = r.json()
        email = ""
        if tok.get("id_token"):
            payload = tok["id_token"].split(".")[1]
            payload += "=" * (-len(payload) % 4)
            email = json.loads(base64.urlsafe_b64decode(payload)).get("email", "")
        if not email:
            u = await c.get("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": "Bearer " + tok["access_token"]})
            email = u.json().get("email", "")
    if not email:
        raise ValueError("Google did not return an email address.")
    store.put_account(_account_id(email), {"refresh_token": tok.get("refresh_token"), "access_token": tok["access_token"], "expires_at": time.time() + int(tok.get("expires_in", 3600)) - 60})
    return email


def connected(email) -> bool:
    return bool(email) and store.get_account(_account_id(email)) is not None


async def _token(email, client):
    acct = store.get_account(_account_id(email))
    if not acct:
        raise LookupError("This Google account is not connected yet.")
    if acct.get("expires_at", 0) > time.time():
        return acct["access_token"]
    r = await client.post(TOKEN, data={"refresh_token": acct["refresh_token"], "client_id": config.GOOGLE_CLIENT_ID, "client_secret": config.GOOGLE_CLIENT_SECRET, "grant_type": "refresh_token"})
    r.raise_for_status()
    tok = r.json()
    acct.update(access_token=tok["access_token"], expires_at=time.time() + int(tok.get("expires_in", 3600)) - 60)
    store.put_account(_account_id(email), acct)
    return acct["access_token"]


async def push(email, name, docx_bytes, deadlines, project, client=None):
    """Upload the .docx converted to a Google Doc, then one all-day Calendar event per deadline. Returns links."""
    out = {"doc_url": None, "events": []}
    async with (client or httpx.AsyncClient(timeout=60)) as c:
        token = await _token(email, c)
        h = {"Authorization": "Bearer " + token}
        meta = json.dumps({"name": name, "mimeType": "application/vnd.google-apps.document"})
        boundary = "vaani" + secrets.token_hex(8)
        body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
                f"--{boundary}\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n").encode() + docx_bytes + f"\r\n--{boundary}--".encode()
        r = await c.post("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink", content=body,
                         headers={**h, "Content-Type": f"multipart/related; boundary={boundary}"})
        r.raise_for_status()
        f = r.json()
        out["doc_url"] = f.get("webViewLink") or f"https://docs.google.com/document/d/{f.get('id')}/edit"
        for d in deadlines:
            ev = {"summary": f"{d['title']} · {project}", "description": (d.get("source_quote") or d.get("note") or "") + f"\nFrom the BRD: {out['doc_url']}",
                  "start": {"date": d["date"]}, "end": {"date": d["date"]}}
            if d.get("kind") == "recurring":
                ev["recurrence"] = ["RRULE:FREQ=WEEKLY;COUNT=8"]
            r = await c.post("https://www.googleapis.com/calendar/v3/calendars/primary/events", json=ev, headers=h)
            if r.status_code < 300:
                out["events"].append({"id": d["id"], "title": d["title"], "link": r.json().get("htmlLink")})
            else:
                out["events"].append({"id": d["id"], "title": d["title"], "error": r.text[:120]})
    return out
