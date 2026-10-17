"""Generate the working web app from the approved BRD (AI), in the chosen language, with an honest fallback."""
import asyncio
from fastapi import APIRouter
from models import CompileIn
from services import llm, microapps, sarvam
from services.compiler import document

router = APIRouter()
MAX_HTML = 400_000
HTML_LANG = {"hindi": "hi", "marathi": "mr", "tamil": "ta", "telugu": "te", "bengali": "bn", "kannada": "kn", "english": "en"}
# Phrased to translate unambiguously (Sarvam rendered "Rule fires" as "the rule sets fire").
LABELS = {"tryValue": "Try a value", "fires": "Rule applies", "idle": "No action", "defaultCheck": "Behaves as described above",
          "checksPassed": "checks completed", "openQuestions": "Open questions", "empty": "No approved requirements yet."}


def brd_for_prompt(brd, translations=None):
    shown = {k: v for k, v in (translations or {}).items() if k and v}
    return {
        **({"display_translations": dict(list(shown.items())[:150])} if shown else {}),
        "title": brd["project_name"], "type": brd["document_type"],
        "sections": {k: [i["text"] for i in v] for k, v in brd["sections"].items() if v},
        "functional_requirements": [{"id": r["req_id"], "title": r["title"], "rule": r["rule"], "acceptance": r["acceptance"]} for r in brd["business_rules"]],
        "open_questions": brd["open_questions"],
    }


def looks_like_html(html):
    low = html.lower()
    return "<html" in low and "</html>" in low and "<body" in low and len(html) <= MAX_HTML


async def translate_many(texts, language):
    return await sarvam.translate_many(texts, language)


async def fallback(body):
    """Without AI: BRDs get the rule-driven requirement simulator (translated with Sarvam when possible);
    other modes keep their templates. Returns (html, note_about_language)."""
    if body.mode != "business":
        note = None if body.app_language == "english" else "The template for this mode is available in English only."
        return microapps.get_bespoke_app_html(body.mode, body.metadata, body.rules, body.domain), note
    doc = document(body)
    rules = [{**r, **rule.model_dump(), "req_id": r["req_id"]} for r, rule in zip(doc["business_rules"], body.rules)]
    title, questions, labels = doc["project_name"], doc["open_questions"], {"sub": f"Interactive check of {len(rules)} approved requirements. Built directly from the BRD (no AI)."} | LABELS
    language, note = body.app_language, None
    if language != "english":
        if not sarvam.enabled():
            note = "Sarvam is not configured, so the app is shown in English."
        else:
            try:
                logic = {r["req_id"]: r["rule"] for r in rules}
                texts = [title, *questions, *labels.values(), *logic.values()] + [x for r in rules for x in (r["title"], r["action"], *r["acceptance"])]
                tr = await translate_many(texts, language)
                title, questions = tr.get(title, title), [tr.get(q, q) for q in questions]
                labels = {k: tr.get(v, v) for k, v in labels.items()}
                for r in rules:
                    r["display"] = {"title": tr.get(r["title"], r["title"]), "logic": tr.get(logic[r["req_id"]], logic[r["req_id"]]),
                                    "action": tr.get(r["action"], r["action"]), "acceptance": [tr.get(a, a) for a in r["acceptance"]]}
            except Exception:
                note, language = "Sarvam Translate failed, so the app is shown in English. Retry to translate.", "english"
    return microapps.requirements_app(title, rules, questions, labels, HTML_LANG[language if not note else "english"]), note


@router.post("/api/app/generate")
async def generate(body: CompileIn):
    if not body.rules:
        html, _ = await fallback(body)
        return {"html": html, "generator": "template", "language": "english", "note": "No approved requirements yet."}
    if llm.live():
        try:
            html = await llm.complete_text(llm.app_synthesis_prompt(brd_for_prompt(document(body), body.translations), body.app_language))
            if not looks_like_html(html):
                raise ValueError("Model did not return a complete HTML document")
            return {"html": html, "generator": "ai:" + llm.main_brain(), "language": body.app_language, "note": None}
        except Exception:
            reason = "AI app generation failed. Showing the requirement simulator built directly from your BRD; retry to generate again."
    else:
        reason = "AI app generation is not configured. Showing the requirement simulator built directly from your BRD."
    html, language_note = await fallback(body)
    shown = "english" if language_note else body.app_language
    return {"html": html, "generator": "template", "language": shown, "note": " ".join(filter(None, [reason, language_note]))}
