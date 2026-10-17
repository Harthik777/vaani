import logging
from copy import deepcopy
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from models import Mode, Rule
import mocks
from services import llm, verify
from services.agent import meeting_language, speaker_of, validate_conflicts

router = APIRouter()
log = logging.getLogger("vaani.extract")

class ExtractIn(BaseModel):
    transcript: str = Field(min_length=1, max_length=100000)
    domain: str = ""
    mode: Mode = "business"
    demo: bool = False


def _demo(body):
    """Demo fixtures only for the exact sample text (interview answers may be appended after it)."""
    meeting = meeting_language(body.transcript)
    if meeting and body.mode == "business":
        rules = deepcopy(mocks.MEETING["rules"][meeting])
        return {"rules": rules, "review_notes": list(mocks.MEETING["review_notes"])}
    samples = mocks.MOCKS_BY_MODE[body.mode]["transcript"].values()
    base = next((t for t in samples if body.transcript == t or body.transcript.startswith(t + "\n")), None)
    if base is None:
        return None
    result = deepcopy(mocks.MOCKS_BY_MODE[body.mode]["rules"])
    for rule in result["rules"]:
        rule["source_quote"] = base
    return result


def _ground_quote(r, transcript):
    """Repair case differences and one-or-two-character copy slips; the quote always ends up as real transcript text."""
    quote = (r.get("source_quote") or "").strip()
    r["_repaired_from"] = None
    if quote and quote not in transcript:
        idx = transcript.lower().find(quote.lower())
        fixed = transcript[idx:idx + len(quote)] if idx != -1 else verify.repair_quote(quote, transcript)
        if fixed:
            r["_repaired_from"], quote = quote, fixed
    r["source_quote"] = quote
    return r


@router.post("/api/extract")
async def extract(body: ExtractIn):
    if body.demo:
        result = _demo(body)
        if result is None:
            raise HTTPException(422, "Edited input requires live extraction or manual rule entry")
        rules = result["rules"]
        for r in rules:
            r["verification"] = verify.verify_rule(r, body.transcript)
        meeting = meeting_language(body.transcript) and body.mode == "business"
        return {"rules": rules, "review_notes": result.get("review_notes", []), "rejected": [], "demo": True, "brain": "demo fixture",
                "conflicts": validate_conflicts(mocks.MEETING["conflicts"], rules) if meeting else []}
    if not llm.live():
        raise HTTPException(503, "Live extraction is not configured. Enter rules manually or choose Use demo.")
    result, last = None, None
    for attempt in range(2):  # one retry: provider hiccups should not end a live demo
        try:
            result = await llm.complete_json(llm.extraction_prompt(body.mode, body.transcript, body.domain), fast=True)
            # An empty list is a valid answer (e.g. a personal chat with no requirement); only a missing list is malformed.
            if isinstance(result.get("rules"), list):
                break
            log.warning("extraction attempt %d: model JSON had no rules list (keys: %s)", attempt + 1, list(result)[:8])
            last, result = ValueError("Model returned no rules"), None
        except Exception as exc:
            last = exc
            log.warning("extraction attempt %d failed: %s: %s", attempt + 1, type(exc).__name__, exc)
    if result is None:
        raise HTTPException(502, "Extraction failed or returned malformed rules. Retry or enter rules manually.") from last
    kept, rejected, ids = [], [], set()
    for raw in result["rules"][:100]:
        if not isinstance(raw, dict):
            continue
        try:
            grounded = _ground_quote(dict(raw), body.transcript)
            r = Rule.model_validate(grounded).model_dump()
        except Exception as exc:
            log.warning("malformed rule from model: %s", exc)
            rejected.append({"title": str(raw.get("title", "Untitled"))[:200], "text": f'IF {raw.get("condition")} THEN {raw.get("action")}',
                             "source_quote": str(raw.get("source_quote") or "")[:300], "reason": "Malformed requirement from the AI"})
            continue
        if r["id"] in ids:
            r["id"] = f'{r["id"]}-{len(ids) + 1}'
        ids.add(r["id"])
        check = verify.verify_rule(r, body.transcript)
        if check["status"] == "rejected":
            rejected.append({"title": r["title"], "text": f'IF {r["condition"]} THEN {r["action"]}', "source_quote": r["source_quote"],
                             "reason": "No source quote" if check["quote"] == "missing" else "Quote not found in what was said"})
            continue
        if grounded["_repaired_from"]:
            check["quote_note"] = f'Quote corrected to the exact words spoken (the AI copied: "{grounded["_repaired_from"][:200]}")'
        r["verification"] = check
        r["speaker"] = r.get("speaker") or speaker_of(r["source_quote"], body.transcript)
        kept.append(r)
    notes = result.get("review_notes", [])
    notes = notes if isinstance(notes, list) else []
    if not kept and not rejected and not notes:
        notes = ["No business or software requirement was found in what was said. Describe what you need, or enter rules manually."]
    return {"rules": kept, "review_notes": notes, "rejected": rejected, "demo": False,
            "conflicts": validate_conflicts(result.get("conflicts"), kept), "brain": llm.main_brain(fast=True)}
