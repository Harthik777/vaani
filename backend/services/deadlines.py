"""Deadlines and milestones inferred from what was said, as calendar entries.

The model turns spoken timing ("Diwali se pehle", "two weeks after the pilot", "every evening") into dated entries. Each entry
keeps the exact words it came from; a date that no words support is marked for confirmation, never silently invented.
Output: a list of entries, an .ics file (imports into Google Calendar, Outlook, iPhone) and per-entry Google Calendar links
that need no credentials.
"""
import json
import re
import uuid
from datetime import date, datetime, timedelta
from urllib.parse import quote

from services import llm

SCHEMA_HINT = ('Return JSON {"deadlines": [{"title", "date", "kind", "source_quote", "note"}]}. '
               'date is YYYY-MM-DD; kind is one of deadline, milestone, recurring, review. source_quote is copied verbatim '
               'from the words (English or the original language). note explains the date in one short sentence.')


def prompt(transcript, answers, rules, today):
    said = transcript.strip()
    extra = "\n".join(f'{a.get("question", "")}: {a.get("answer", "")}' for a in (answers or []) if a.get("answer"))
    reqs = "\n".join(f'- {r.get("title")}: IF {r.get("condition")} THEN {r.get("action")}' for r in (rules or []))
    return (f"Today is {today} (India). From the conversation below, list every deadline, milestone, launch date, review date or "
            "recurring obligation that the speakers stated or clearly implied (festivals like Diwali or Pongal resolve to their "
            "next date in India; 'two weeks after X' resolves relative to X; 'every evening' is recurring with the first date "
            "tomorrow). Do not invent dates that nothing in the words supports; if a timing is vague ('soon'), leave it out. "
            "At most 8 entries.\n"
            f"Conversation:\n{said}\n\nInterview answers:\n{extra or '(none)'}\n\nRequirements:\n{reqs or '(none)'}\n\n{SCHEMA_HINT}")


def _valid_date(value):
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


async def infer(transcript, answers, rules, today=None):
    """Dated entries from speech. Each one is grounded: the quote must appear in the transcript or the answers."""
    if not llm.live():
        raise RuntimeError("Deadline detection needs a configured AI model.")
    today = today or date.today().isoformat()
    result = await llm.complete_json(prompt(transcript, answers, rules, today), fast=False)
    haystack = transcript + "\n" + "\n".join(str(a.get("answer", "")) for a in (answers or []))
    out = []
    for item in (result.get("deadlines") or []) if isinstance(result, dict) else []:
        if not isinstance(item, dict):
            continue
        when = _valid_date(item.get("date"))
        title = str(item.get("title") or "").strip()[:120]
        if not when or not title:
            continue
        q = str(item.get("source_quote") or "").strip()
        if q and q not in haystack:
            from services import verify
            q = verify.repair_quote(q, haystack) or ""
        grounded = bool(q) and q in haystack
        out.append({"id": "d" + str(len(out) + 1), "title": title, "date": when.isoformat(), "kind": str(item.get("kind") or "deadline")[:20],
                    "source_quote": q if grounded else None, "note": str(item.get("note") or "")[:200],
                    "status": "grounded" if grounded else "confirm"})
    return out[:8]


def google_link(entry, project):
    """A Google Calendar 'add event' link: works for any Google account, no API key or OAuth needed."""
    d = _valid_date(entry["date"]) or date.today()
    span = f"{d.strftime('%Y%m%d')}/{(d + timedelta(days=1)).strftime('%Y%m%d')}"
    details = (entry.get("source_quote") or entry.get("note") or "") + f"\nFrom the BRD: {project} (VAANI)"
    return ("https://calendar.google.com/calendar/render?action=TEMPLATE&text=" + quote(f"{entry['title']} · {project}")
            + "&dates=" + span + "&details=" + quote(details))


def ics(entries, project):
    """RFC 5545 all-day events, one per entry; recurring entries repeat weekly for 8 weeks."""
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//VAANI//BRD deadlines//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    for e in entries:
        d = _valid_date(e["date"])
        if not d:
            continue
        esc = lambda s: re.sub(r"([,;\\])", r"\\\1", str(s or "")).replace("\n", "\\n")
        lines += ["BEGIN:VEVENT", f"UID:{uuid.uuid4()}@vaani", f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
                  f"DTEND;VALUE=DATE:{(d + timedelta(days=1)).strftime('%Y%m%d')}", f"SUMMARY:{esc(e['title'] + ' · ' + project)}",
                  f"DESCRIPTION:{esc((e.get('source_quote') or e.get('note') or '') + ' (from the BRD, VAANI)')}"]
        if e.get("kind") == "recurring":
            lines.append("RRULE:FREQ=DAILY;COUNT=30" if "evening" in (e.get("note") or "").lower() or "daily" in (e.get("note") or "").lower() else "RRULE:FREQ=WEEKLY;COUNT=8")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
