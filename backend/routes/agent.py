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
    except Exception:
        # The AI check failed: fall back to asking every unanswered checklist question, and say so.
        items = [{"key": c["key"], "label": c["label"], "status": "answered" if c["key"] in body.answered else "missing", "source_quote": None} for c in agent.CHECKLIST]
        questions = [{"key": c["key"], "label": c["label"], "question": c["question"], "question_local": None} for c in agent.CHECKLIST if c["key"] not in body.answered]
        done = sum(1 for i in items if i["status"] == "answered")
        return {"items": items, "questions": questions, "completeness": int(100 * done / len(items) + 0.5), "brain": "checklist only (AI check failed)",
                "translated_with_sarvam": False, "ai_checked": False, "sample_answers": {}, "warning": "The AI coverage check failed, so every open checklist question is asked."}


@router.post("/api/agent/conflicts")
async def conflicts(body: ConflictsIn):
    try:
        return await agent.conflicts([r.model_dump() for r in body.rules], body.transcript, body.demo)
    except Exception:
        return {"conflicts": [], "brain": None, "note": "The conflict check failed. Review requirements from different speakers manually."}
