from fastapi import APIRouter
from pydantic import BaseModel, Field
from models import Language, Mode, Rule
from services import agent

router = APIRouter()

class GapsIn(BaseModel):
    transcript: str = Field(min_length=1, max_length=100000)
    mode: Mode = "business"
    lang: Language = "english"
    answered: list[str] = Field(default_factory=list, max_length=20)
    demo: bool = False

class ConflictsIn(BaseModel):
    rules: list[Rule] = Field(default_factory=list, max_length=100)
    transcript: str = Field(default="", max_length=100000)
    demo: bool = False


@router.post("/api/agent/gaps")
async def gaps(body: GapsIn):
    try:
        return await agent.assess(body.transcript, body.mode, body.lang, body.answered, body.demo)
    except Exception as exc:
        # The AI check failed: fall back to asking every unanswered checklist question, say so, and log why.
        print(f"[agent] coverage check failed, asking the full checklist: {type(exc).__name__}: {exc}")
        items = [{"key": c["key"], "label": c["label"], "status": "answered" if c["key"] in body.answered else "missing", "source_quote": None} for c in agent.CHECKLIST]
        questions = [{"key": c["key"], "label": c["label"], "question": c["question"], "question_local": None} for c in agent.CHECKLIST if c["key"] not in body.answered]
        questions, translated = await agent.localize(questions, body.lang)  # the speaker still gets questions in their language
        done = sum(1 for i in items if i["status"] == "answered")
        reason = "the AI service is busy (rate limit)" if "429" in str(exc) or "503" in str(exc) else "the AI service did not answer"
        return {"items": items, "questions": [{k: v for k, v in q.items() if k != "translation_error"} for q in questions],
                "completeness": int(100 * done / len(items) + 0.5), "brain": "checklist only (AI check failed)",
                "translated_with_sarvam": translated, "ai_checked": False, "sample_answers": {},
                "warning": f"The AI coverage check failed because {reason}, so every open checklist question is asked. Retry to check again."}


@router.post("/api/agent/conflicts")
async def conflicts(body: ConflictsIn):
    try:
        return await agent.conflicts([r.model_dump() for r in body.rules], body.transcript, body.demo)
    except Exception:
        return {"conflicts": [], "brain": None, "note": "The conflict check failed. Review requirements from different speakers manually."}
