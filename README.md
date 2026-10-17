# Vaani (वाणी): the voice-first BRD agent

**Speak your requirements in your own language. Vaani's agent asks what you forgot, writes a Business Requirements Document in which every requirement can be played back in the speaker's own voice, and builds a first working version of the app.**

Track: *Business Requirements Document (BRD) Generation Agent*. Built on Sarvam AI's speech, voice and translation APIs.

---

## The problem
Indian business owners describe what they need in Hindi, Tamil, Telugu, Marathi or Bengali. The IT vendor who builds it needs a precise English BRD. Requirements get lost in between: missing deadlines and budgets, numbers changed in translation, and stakeholders who contradict each other. The result is rework.

## The workflow (6 steps)

| Step | What happens | Powered by |
|---|---|---|
| 1. Start | Choose the language (7: Hindi, Marathi, Tamil, Telugu, Bengali, Kannada, English) and accessibility mode (standard, low vision, Deaf/HoH typed input) | |
| 2. Speak | One owner-facing screen: pick who is speaking (Owner, Manager…), tap the microphone, watch the transcript arrive line by line with speaker chips. Or **upload a recorded meeting** (Sarvam separates the speakers automatically) or a **photo/PDF of notes** (Sarvam Doc AI reads it). Audio is hashed with SHA-256 and kept as evidence. Names and products already in the session are sent as keyterms. | **Sarvam Saaras v4** speech-to-text (codemix mode, keyterms, timestamps), **batch diarization**, **Doc AI** |
| 3. Agent questions | The agent checks the conversation against the 8 things every BRD needs (goal, users, features, timeline, budget, success measure, constraints, sign-off owner). It shows what is already covered, **with the exact words**, and asks only for what is missing: in your language, out loud. The completeness meter climbs as you answer. | **Sarvam 105B** (strict JSON schema; Gemini as fallback), **Sarvam Translate**, **Sarvam Bulbul** voice |
| 4. Review | Requirements are extracted with exact source quotes. The **verifier** checks each one, and the agent flags **conflicts between speakers** (for example, Owner says 50 kg, Manager says 100 kg). | Gemini (extraction) + **Sarvam 105B** (conflict check) + deterministic verifier |
| 5. Approve | Approve each requirement: hear the original voice clip, hear the rule read back in your own language, then say "haan" or "nahi" (or use the buttons). The spoken word is recorded against the approval. | **Sarvam Bulbul** + Translate + **Saaras** |
| 6. BRD + App | A full BRD (12 standard sections, functional requirements with traceability, acceptance criteria, open questions, a verification report and sign-off), plus a web app generated from the approved BRD. **⬇ Download BRD:** PDF, Word, Markdown, Jira CSV. **🌐 One language switch** puts the BRD (Sarvam translation under each English line) *and* the app into any of the 7 languages. Downloads then include the translation; the Jira CSV stays English for the vendor. **🔊 Listen** to a BRD summary in that language. Publish, then send the portal link on **WhatsApp**. | Gemini, **Sarvam Translate + Bulbul** |

## The verifier (why the AI can't slip things in)
- **Quotes must be exact.** Every requirement and every spoken BRD item must quote the transcript verbatim. If the AI mis-copies a quote by a character or two (seen live: a dropped Hindi vowel sign), Vaani swaps in the real transcript text and labels it. Anything else is rejected and shown struck through.
- **Numbers must be spoken.** Every number in a requirement must appear in its quote. Sarvam STT writes Hindi numbers as words ("पचास किलो"), so the model must name the exact spoken words for each number, and the UI shows them as "50 ← 'पचास'" for a human to confirm. English number words are parsed too, so "fifty kg" can't slip past.
- **AI suggestions may not invent numbers.** The AI may suggest typical risks or assumptions, labelled "AI suggestion: confirm", but any suggestion that contains a number nobody said is blocked. Seen live: "Zero missed orders" was blocked because nobody said zero.
- The same checks run in Python (`backend/services/verify.py`) and in the browser (`frontend/src/data/verify.js`), so user edits are re-checked instantly. Both versions are tested to give identical results.

## What uses Sarvam (models checked against docs.sarvam.ai on 2026-10-17)
| API | Model | Used for |
|---|---|---|
| Speech-to-text | `saaras:v4`, mode `codemix`, `keyterms` | Every recording and every spoken answer, with chunk timestamps for "hear the source" clips. Code-mixed speech ("मुझे stock alert चाहिए") stays readable; names and products from the session bias recognition. `saaras:v3` still works (set `SARVAM_STT_MODEL`). |
| Translate | `sarvam-translate:v1` | Agent questions in your language; the BRD and the app in any of the 7 languages; bilingual Word and Markdown downloads |
| Text-to-speech | `bulbul:v4-flash`, one persona per language | Agent asks questions aloud; rules read back during approval; "Listen to BRD summary". Kannada, Hindi, Tamil, Telugu, Marathi, Bengali and English voices (`services/sarvam.py` → `V4_SPEAKERS`). |
| Batch speech-to-text | `saaras:v4`, `with_diarization` | Uploaded meeting recordings (call recordings, WhatsApp voice notes): speakers separated automatically, timestamps per line, recording kept as evidence |
| Document intelligence | Doc AI `digitise` | A photo or PDF of handwritten or printed notes becomes `[Notes]` transcript lines |
| Chat | `sarvam-105b-conversations` | The interview agent: gap questions and the stakeholder-conflict check, with strict JSON schemas. On by default (`AGENT_LLM=sarvam`); falls back to the main LLM, and a circuit breaker stops waiting on it after two failures. Gemini keeps the long BRD draft and app generation. |

Sarvam's sync speech-to-text API does not offer speaker diarization (that is batch-only), so speakers are chosen in the UI before each recording.

**Stage insurance.** LLM answers, Bulbul audio and translations are cached on disk under `backend/data/cache` (hash of the full request). Rehearse once; the identical run on stage is instant. `VAANI_CACHE=off` disables it. The cache never stands in for a missing key.

## Quick start

### 1. Backend
```bash
cd Vaani_code/vaani-repo/backend
pip install -r requirements.txt
python main.py
```
Put `SARVAM_API_KEY` and `LLM_API_KEY` in `backend/.env` (see `.env.example`). Without keys, the demo still runs and every AI or Sarvam feature says clearly that it is not configured.

### 2. Frontend
```bash
cd Vaani_code/vaani-repo/frontend
npm install
npm run dev
```
Open http://localhost:5173. For the stage demo, choose **हिंदी** or **ಕನ್ನಡ** → **Start capturing** → **Use 2-speaker meeting demo**. The landing page shows only the BRD flow; the older document types (awareness, audit, deals) are at http://localhost:5173/?modes=all.

### 3. Offline single file (no backend)
```bash
cd Vaani_code/vaani-repo/frontend
npm run build:standalone
```
This writes `vaani-prototype.html`. The demo runs fully offline with sample data. Live AI and Sarvam features need the backend.

## Measured accuracy
```bash
cd Vaani_code/vaani-repo/backend
python benchmark.py          # writes ../BENCHMARK.md; --no-llm for the verifier only
```
Last run (17 Oct 2026): verifier 66/66 planted errors caught, 0 false blocks on 24 genuine requirements; conflict detector 7/7 found, 0 false alarms on Sarvam 105B.

## Tests
```bash
cd Vaani_code/vaani-repo/backend
python -m unittest tests/test_workflows.py tests/test_brd_agent.py tests/test_sarvam_v4.py tests/test_meeting_notes.py
```
64 tests cover the verifier, agent, conflicts, BRD drafting, exports, Sarvam request shapes (v4 codemix and keyterms, v4-flash voices, the 105B request that answers, the cache, the circuit breaker, Kannada, meeting diarization and Doc AI notes) and access control.

```bash
cd Vaani_code/vaani-repo/frontend
npx playwright test
```
12 end-to-end flows run in a real browser. Use `PW_WEB_PORT=5174 PW_API_PORT=8001` if the dev servers are already running, `PW_PYTHON` to point at the interpreter that has the backend requirements, `PW_AUDIT_DIR` for screenshots and PDFs (default `../../../audit`), and `PLAYWRIGHT_BROWSERS_PATH` to point at the bundled browsers.

## Honest limitations
- Live AI steps take time: about 4 s for the gap check (Sarvam 105B), 15 s for extraction, 35 s for BRD drafting and 17 s for app generation (measured 2026-10-17). The BRD page pre-drafts in the background while you approve, and results are cached, so a rehearsed run is instant.
- Approval records who approved and when; it is not an electronic signature. Hashes show a recording was not altered; they do not prove who spoke.
- The three non-BRD document types are hidden from the landing page (`?modes=all` shows them) and still use their older fixed app templates.
- Speaker attribution comes from the speaker chosen in the UI, not from voice recognition.

See `CHANGES-2026-10-17.md` for everything that changed on hackathon day 1.
