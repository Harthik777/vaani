"""In-app guide: answers "what do I do now?" for the current step, in the user's language.

Deterministic answers always exist (so the guide works offline and in the demo); when an LLM is configured the
question goes to the interview agent's brain (Sarvam 105B first) with the step context, and the answer is
translated with Sarvam Translate for non-English users. Nothing here touches the user's data: it only sees the
step name, counts, and the question text.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from models import Language
from services import agent, llm, sarvam

router = APIRouter()

STEPS = {
    "landing": ("Start", "Pick your language, then press Start capturing. Everything else is optional."),
    "record": ("Speak", "Tap the microphone and describe the app you need, in your own words. Pick who is speaking first if several people talk. "
               "You can also upload a recorded meeting or a photo of notes. Then press Next: agent checks for gaps."),
    "interview": ("Agent questions", "The agent found what is already covered and asks only what is missing. Answer by voice or by typing, "
                  "or press Skip; skipped items become open questions. Press Extract requirements when you are done."),
    "extract": ("Review", "Each requirement quotes the speaker exactly. Green means verified. A number nobody said is blocked in red. "
                "If two people disagreed, choose whose version to keep. Press Fix this only where something is wrong, then Review and approve."),
    "signoff": ("Approve", "Listen to the original clip, hear the rule read back, then approve or skip. You can also say haan or nahi. "
                "Your name is already filled in; change it if someone else is approving."),
    "brd": ("BRD + App", "The document is ready. Switch BRD + app to your language, listen to the summary, download Word or Jira CSV, "
            "try the app on the right, then publish to get a QR code and a WhatsApp link for the owner."),
}
FAQ = [
    (("number", "red", "blocked", "not spoken", "48"), "A red number means nobody said it. Either change it back to what was said, or ask the speaker and record the answer. The verifier never lets an unspoken number into the BRD."),
    (("conflict", "disagree", "owner", "manager", "keep"), "When two speakers gave different values for the same thing, both versions are shown with their voices. Keep one, or Decide later to list it as an open question."),
    (("language", "hindi", "kannada", "tamil", "translate"), "Pick the language on the Start step. On the BRD step, Switch BRD + app puts the whole document and the app in that language."),
    (("upload", "recording", "meeting", "call", "voice note"), "On the Speak step press Upload a recorded meeting. Sarvam separates the speakers; the first voice is named Owner and the second Manager, and you can rename them."),
    (("photo", "notes", "pdf", "handwritten"), "On the Speak step press Photo or PDF of notes. Sarvam reads the page and the lines join the transcript as Notes."),
    (("download", "pdf", "word", "jira", "export"), "On the BRD step the Download BRD bar has PDF, Word, Markdown and Jira CSV. Jira CSV is always English for the vendor."),
    (("whatsapp", "qr", "share", "send", "owner"), "On the BRD step press Publish reviewed version. Two QR codes appear: one opens the BRD with the voice clips, one opens WhatsApp with the link."),
    (("vague", "jaldi", "simple", "clarify", "magnifier"), "A magnifier chip marks a vague word such as jaldi or simple, with the question to ask. Answer it so the vendor gets a number, not an adjective."),
    (("voice", "haan", "nahi", "say", "approve by voice"), "On the Approve step press Say haan or nahi to decide, then speak. Haan approves, nahi skips, and the word is recorded with the approval."),
    (("start over", "reset", "restart", "new"), "On the BRD step press Start over. On earlier steps use Back; the microphone button clears the old transcript when you record again."),
]
LANG_NAMES = {"hindi": "Hindi", "marathi": "Marathi", "tamil": "Tamil", "telugu": "Telugu", "bengali": "Bengali", "kannada": "Kannada", "english": "English"}


class HelpIn(BaseModel):
    question: str = Field(default="", max_length=600)
    phase: str = Field(default="landing", max_length=20)
    lang: Language = "english"
    counts: dict[str, int] = Field(default_factory=dict)


def deterministic(question: str, phase: str) -> str:
    q = (question or "").lower()
    for keys, answer in FAQ:
        if any(k in q for k in keys):
            return answer
    return STEPS.get(phase, STEPS["landing"])[1]


def suggestions(phase: str) -> list[str]:
    base = {
        "landing": ["What do I do first?", "Which language should I pick?", "Can I upload a recording instead?"],
        "record": ["How do I add the manager as a speaker?", "Can I upload a call recording?", "What if I typed in Roman script?"],
        "interview": ["What if I don't know the budget yet?", "Can I answer by voice?", "What happens to skipped questions?"],
        "extract": ["Why is a number red?", "The owner and manager disagree, what now?", "What is a vague term?"],
        "signoff": ["How do I approve by voice?", "Can someone else approve?", "What does a clip play?"],
        "brd": ["How do I send this to the owner?", "How do I get it in Hindi?", "What is the Jira CSV for?"],
    }
    return base.get(phase, base["landing"])


@router.post("/api/help")
async def help_(body: HelpIn):
    fallback = deterministic(body.question, body.phase)
    answer, brain = fallback, "guide"
    if body.question.strip() and llm.live():
        step = STEPS.get(body.phase, STEPS["landing"])
        prompt = ("You are the in-app guide for Vaani, a voice-first tool where an Indian business owner speaks their requirements and a "
                  "verified Business Requirements Document is produced for their IT vendor. Steps: Start, Speak, Agent questions, Review, Approve, BRD + App. "
                  f"The user is on the step '{step[0]}'. What this step does: {step[1]} Counts on screen: {body.counts}. "
                  "Answer the user's question in at most three short sentences, plain words, no marketing. If it is about something the tool cannot do, say so. "
                  f"Reply in {LANG_NAMES.get(body.lang, 'English')}. Return JSON: {{\"answer\": \"...\"}}\nQuestion: " + body.question.strip())
        try:
            result, brain = await llm.agent_json(prompt, system=agent.SYSTEM)
            text = str(result.get("answer") or "").strip()
            if text:
                answer = text
        except Exception:
            brain = "guide"
    if brain == "guide" and body.lang != "english" and sarvam.enabled():
        try:
            answer = await sarvam.translate(answer, body.lang)
        except Exception:
            pass
    return {"answer": answer, "brain": brain, "step": STEPS.get(body.phase, STEPS["landing"])[0], "suggestions": suggestions(body.phase)}
