from services import verify
"""Only submitted rules reach documents and ScreenSpecs. Mirrors frontend/src/data/compiler.js."""
from models import DOCUMENT_TYPES
from services import microapps, verify
import mocks

CHECKLIST = mocks.BRD["CHECKLIST"]
SECTIONS = mocks.BRD["SECTIONS"]
ANSWER_SECTIONS = mocks.BRD["ANSWER_SECTIONS"]
PROFILE_FIELDS = {
    "awareness": ["speaker", "designation", "event", "area"],
    "audit": ["asset", "gps", "inspected_at", "inspector"],
    "deals": ["buyer", "seller", "goods", "value", "delivery", "terms"],
    "business": ["owner", "site"]
}


def rule_text(r):
    return f'IF {r["condition"]} THEN {r["action"]}' + (f' UNLESS {r["exception"]}' if r.get("exception") else "")


def requirement_id(index):
    return f"FR-{index + 1:02d}"


def answer_sections(answers, transcript):
    """Interview answers become spoken items, quoted verbatim (they are part of the transcript)."""
    sections = {s["key"]: [] for s in SECTIONS}
    labels = {c["key"]: c["label"] for c in CHECKLIST}
    for a in answers:
        target = ANSWER_SECTIONS.get(a.key)
        text = a.answer.strip()
        if target and text and text in transcript:
            sections[target].append({"text": f"{labels.get(a.key, a.key)}: {text}", "source_quote": text, "origin": "spoken",
                                     "numbers": verify.check_numbers(text, text)})
    return sections


def verified_sections(raw, transcript):
    """Re-check AI-drafted sections on the server: nothing ungrounded reaches the document."""
    sections, rejected = {s["key"]: [] for s in SECTIONS}, []
    for key, items in (raw or {}).items():
        if key not in sections or not isinstance(items, list):
            continue
        for item in items[:30]:
            if not isinstance(item, dict):
                continue
            clean, reason = verify.verify_item(item, transcript)
            if clean:
                sections[key].append(clean)
            elif reason != "empty":
                rejected.append({"section": key, "text": str(item.get("text", ""))[:500], "reason": reason})
    return sections, rejected


def verified_acceptance(raw, rules):
    """Acceptance criteria may only reuse numbers from their own requirement (text or quote)."""
    by_id, kept, rejected = {r["id"]: r for r in rules}, [], []
    for item in raw or []:
        rule = by_id.get(str(item.get("rule_id", "")))
        text = str(item.get("text", "")).strip()
        if not rule or not text:
            continue
        allowed = set(verify.numbers(rule_text(rule) + " " + rule.get("source_quote", "")))
        extra = [n for n in verify.numbers(text) if n not in allowed]
        if extra:
            rejected.append({"section": "acceptance", "text": text[:500], "reason": "number(s) " + ", ".join(extra) + f" not in {rule['id']}"})
        else:
            kept.append({"rule_id": rule["id"], "text": text})
    return kept, rejected


def merge(base, extra):
    for key, items in extra.items():
        seen = {i["text"] for i in base.get(key, [])}
        base.setdefault(key, []).extend(i for i in items if i["text"] not in seen)
    return base


def document(body):
    rules = [r.model_dump() for r in body.rules]
    transcript = body.transcript or ""
    sections = answer_sections(body.answers, transcript)
    ai_sections, rejected = verified_sections(body.sections, transcript)
    sections = merge(sections, ai_sections)
    acceptance, rejected_acceptance = verified_acceptance(body.acceptance, rules)
    functional = []
    for i, r in enumerate(rules):
        check = verify.verify_rule(r, transcript) if transcript else {"quote": "not checked", "numbers": [], "status": "not_checked"}
        functional.append({
            "req_id": requirement_id(i), "id": r["id"], "title": r["title"], "rule": rule_text(r), "type": r["type"],
            "priority": "Reviewed requirement", "source_quote": r.get("source_quote", ""), "speaker": r.get("speaker"),
            "evidence_id": r.get("evidence_id"), "start": r.get("start"), "end": r.get("end"),
            "approved_at": r.get("approved_at"), "approved_by": r.get("approved_by"), "verification": check,
            "acceptance": [a["text"] for a in acceptance if a["rule_id"] == r["id"]],
        })
    answered = {a.key for a in body.answers}
    covered = {c.get("key") for c in body.coverage if c.get("covered") or c.get("status") == "covered"}
    open_questions = [f'{c["label"]}: {c["question"]}' for c in CHECKLIST if c["key"] not in answered | covered] if body.coverage or body.answers else []
    ids = {r["id"] for r in rules}
    for r in body.rules:
        for v in verify.vague_terms(" ".join(str(getattr(r, k, "") or "") for k in ("title", "condition", "action", "exception"))):
            open_questions.append(f'Clarify "{v["term"]}" in {r.title}: {v["question"]}')
    open_questions += [f'Conflict to resolve: {c.get("explanation", "")}' for c in body.conflicts
                       if c.get("explanation") and set(c.get("rule_ids") or []) <= ids]
    if body.metadata.get("review_notes"):
        open_questions.append(body.metadata["review_notes"])
    return {
        "project_name": body.metadata.get("title") or DOCUMENT_TYPES[body.mode],
        "document_type": DOCUMENT_TYPES[body.mode],
        "mode": body.mode,
        "demo": body.demo,
        "metadata": body.metadata,
        "problem_statement": body.domain,
        "sections": sections,
        "section_titles": {s["key"]: s["title"] for s in SECTIONS},
        "scope": [r["title"] for r in rules],
        "business_rules": functional,
        "open_questions": open_questions,
        "rejected": rejected + rejected_acceptance,
        "status": "Draft for sign-off. Generated from recorded speech and reviewed rule by rule.",
        "authorization": "Business owner: ____________________   IT / vendor lead: ____________________   Date: __________",
    }


def screens(body):
    cards = [{"type": "statTile", "label": key.replace("_", " ").title(), "props": {"value": body.metadata.get(key) or "Not provided"}} for key in PROFILE_FIELDS[body.mode]]
    for r in body.rules:
        cards.extend([
            {"type": "alert", "label": r.title, "props": {"level": r.type if r.type in ["critical", "moderate", "compliant"] else "info", "detail": f"IF {r.condition} THEN {r.action}" + (f" UNLESS {r.exception}" if r.exception else "")}},
            {"type": "quotePlayer", "label": r.source_quote or "Source recording", "props": {"ruleId": r.id, "evidenceId": r.evidence_id, "start": r.start, "end": r.end}},
        ])
    actions = [{"type": "checklist", "label": "Reviewed actions", "props": {"items": [r.action for r in body.rules]}}]
    if body.mode == "awareness":
        actions += [
            {"type": "contactCard", "label": "Health helpline", "props": {"number": "104"}},
            {"type": "contactCard", "label": "Ambulance", "props": {"number": "108"}},
            {"type": "mapLink", "label": "Find primary health centers", "props": {}},
            {"type": "button", "label": "Copy advisory link", "props": {"action": "share"}}
        ]
    elif body.mode == "audit":
        actions += [{"type": "button", "label": "Create maintenance ticket", "props": {"action": "dispatch"}}]
    elif body.mode == "deals":
        actions += [
            {"type": "milestones", "label": "Order progress", "props": {}},
            {"type": "qualityForm", "label": "Warehouse inspection", "props": {}},
            {"type": "button", "label": "Prepare milestone payment", "props": {"action": "pay"}}
        ]
    else:
        actions += [{"type": "button", "label": "Create procurement ticket", "props": {"action": "order"}}]

    app_html = microapps.get_bespoke_app_html(body.mode, body.metadata, body.rules, body.domain)

    return {
        "screens": [
            {"screenId": "requirements", "title": DOCUMENT_TYPES[body.mode], "appHtml": app_html, "components": cards},
            {"screenId": "actions", "title": "Actions", "appHtml": app_html, "components": actions}
        ],
        "appHtml": app_html,
        "demo": body.demo
    }
