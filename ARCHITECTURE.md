# Vaani architecture

```
Browser (React + Vite, or the offline single-file build)
  Start → Speak → Agent questions → Review → Approve → BRD + App
  data/verify.js   same grounding checks as the backend, re-run on every edit
  data/compiler.js assembles the BRD from approved rules, answers and verified AI sections
        │ JSON / multipart over HTTP
        ▼
FastAPI backend
  /api/stt              Sarvam Saaras speech-to-text (sync, <30 s segments, chunk timestamps)
  /api/evidence         original audio + SHA-256, capability-key access
  /api/agent/gaps       8-point BRD checklist: covered (with exact quote) / missing → contextual question
                        questions translated with Sarvam Translate
  /api/extract          LLM extraction → per-rule verification; untraceable or malformed rules are rejected visibly
  /api/agent/conflicts  contradictions between requirements from different speakers (ids and speakers validated)
  /api/brd              deterministic BRD assembly (re-verifies any AI sections)
  /api/brd/draft        LLM drafts the 12 BRD sections + acceptance criteria → verifier keeps only grounded content
  /api/brd/docx         Word export (python-docx)
  /api/app/generate     LLM writes a single-file app from the approved BRD; fallback: the rule-driven requirement simulator
  /api/tts              Sarvam Bulbul (optionally Sarvam Translate first)
  /api/translate        Sarvam Translate, batched
  /api/portals, /p/:id  durable published snapshots with access keys and share cards
        │
        ├── Sarvam AI: speech-to-text, text-to-speech, translate (chat optional)
        └── Main LLM: Gemini by default (Anthropic, OpenAI-compatible or Sarvam also supported)
```

## Trust model
| Risk | Control | Where |
|---|---|---|
| AI invents a requirement | Requirement must quote the transcript verbatim; otherwise it is rejected and listed | `services/verify.py`, `routes/extract.py` |
| AI mis-copies a quote | A near-exact (≥97 %) copy of one line is replaced by the real transcript text and labelled | `verify.repair_quote` |
| AI changes or invents a number | Every number must appear in the quote, or be mapped to the exact spoken words (shown for human confirmation). English number words count as numbers. | `verify.check_numbers`, `verify.word_numbers` |
| AI pads the BRD | Drafted items need a verbatim quote; un-quoted suggestions are labelled and may not contain numbers | `verify.verify_item`, `compiler.verified_sections` |
| AI-generated app misbehaves | Runs in an opaque-origin sandbox with a CSP that forbids network access, both inline and when opened in a new tab | `PhoneFrame.jsx` |
| Data injected into the fallback app | JSON embedded with `<` escaped, so it can never close the script | `microapps.requirements_app`, `requirementsApp.js` |
| Silent fallback to fake data | Demo fixtures are used only for the exact sample text, and every unconfigured AI or Sarvam path says so in the UI | `routes/extract.py`, `routes/agent.py` |

## Shared definitions (one source for Python and JavaScript)
- `shared/brd.json`: the 8-point checklist, the 12 BRD sections, and which answers go into which section
- `shared/meeting.json`: the 2-speaker demo (English and Hindi), with rules, coverage, conflict and sample answers
- `shared/requirements_app.html`: the deterministic fallback app
- `shared/demo.json`, `shared/transcripts.json`: the older per-mode samples
