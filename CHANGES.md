# Vaani change log

## 17 Oct night: merge of both branches (nothing lost, everything measured)

Two trees were developed in parallel on 17 Oct. This merge keeps every feature from both:

**From the real-test fixes (EVVSK):** session isolation (`replaceTranscript`, `groundedTo`, drafts and apps keyed by their exact
input in `appCache` / `trCache`), the next agent question shown at once with the re-check in the background, extraction and
conflicts in one call (`validate_conflicts`, `speaker_of`), the fast Gemini model for short tasks with thinking set to low for
long writing and immediate fallback across models, **Fast approval** (verified requirements approved in one step, flagged ones
and conflicts still reviewed one by one), the BRD and the app built in parallel during sign-off, translations cached per language,
Sarvam key and credit errors explained (`SarvamError`), translation on one shared connection (`translate_many`), an empty
extraction treated as a valid answer, and the live browser benchmark (`frontend/tests-live`).

**From the feature tree (Harthik):** the in-app guide (`/api/help`, `HelpBot`), QR hand-off, vague-term clarifier, Roman-script
conversion (Sarvam transliterate), Bulbul pronunciation dictionary, colloquial Mayura register, first-question audio prepared
server-side, the owner view on Review, server-side PDF with Indic shaping, Excel traceability matrix, email pack, the narrated demo
player, multi-session meeting merging and the talk-time bar, and the light "Ledger" design.

**Decisions:** the interview agent still tries Sarvam's 105B first (it answers in about 5 s with the current key) but gives it
8 s instead of 30 s before the fast Gemini model takes over; recording segments stay at 10 s so words appear sooner.
Verified live after the merge: extraction with conflicts 1.7 s, BRD draft 6 s, app 20 s (built in parallel), gap check 5 s with
instant first-question audio. 86 backend tests, 13 browser flows.


## 17 Oct evening: fixes from the failed real test

A real test (friend messages spoken in Hinglish/Marathi, then other inputs in the same browser tab) showed the BRD and app
switching to spice-wholesale content, and 30-60 s waits. Evidence on disk (`backend/data`: the recordings and the AI response
cache) showed what happened. Nothing below is guessed; every fix is covered by a test.

### Why the context switched
The transcript the AI received did change between sessions, but stale state from earlier sessions also leaked in:
1. **Interview answers survived a new transcript.** The next BRD's AI draft still received them (seen: "receptionist and owner… about 100 patients" in a roommates BRD).
2. **Demo identity survived.** "Use 2-speaker meeting demo" sets the title ("Demo · Spice wholesale…"), owner and domain. Typing or recording new text never cleared them, so they reached the AI prompts, the BRD title and speech-recognition keyterms.
3. **Late results landed in the wrong session.** `draftBrd` built the app from a snapshot of the old request and wrote it into whatever session was open (seen in the cache: a "meet at Starbucks" extraction at 16:25:03, then an app titled "Wayanad Depot Procurement System" at 16:25:06).

**Fix:** when the transcript changes, only answers, recordings and details still present in it are kept, and demo identity is dropped. Every AI result is stored under the exact input it was made for and shown only for that input (`App.jsx`: `replaceTranscript`, `groundedTo`, `draftKey`, `appCache`).

### Why it was slow
- **The interview agent called Sarvam's chat model first.** For the configured key it returns `403 invalid_api_key_error` (speech, voice and translation accept the same key), so every call paid a failed request plus a fallback to the main model with full thinking. The agent now uses the fast Gemini model; `AGENT_LLM=sarvam` re-enables Sarvam chat for a key with chat access.
- **This folder did not have the speed work.** Ported: fast model for short structured tasks (`LLM_FAST_MODEL`), thinking set to low for long writing (`LLM_THINKING`), immediate fallback across models on 429/503, conflicts returned in the extraction call, the next agent question shown at once with the re-check in the background, the BRD and app built in parallel while you approve, "Fast approval" for verified rules, and translation on one shared connection, 10 lines at a time.
- **A personal chat with no requirement** made extraction retry and then fail with 502. An empty result is now a valid answer ("No business or software requirement was found…").
- **Sarvam key and credit problems** now say so ("Sarvam rejected the API key…", "Sarvam credits are used up…") instead of a generic 502.

### Measured (real browser, real Gemini key, response cache off, no demo)
`frontend/tests-live/real-voice.spec.js`: a dental-clinic owner's request (real speech through Sarvam STT in the baseline run, the
same transcript typed after the Sarvam key was revoked), three typed answers, extraction, approval, BRD and app, then a roommates
request in the same tab.

| What you wait for | Before | After |
|---|---|---|
| Agent's first question | 4.0 s | 3.0 s |
| Next question after an answer | ~4 s (blocked on the re-check) | 0.1 s |
| Extraction + conflicts | 8.5 s | 6.1 s |
| BRD + app after the last approval | 19.3 s | 5.9 s |
| Second request in the same tab | 16.7 s, **clinic content leaked** | 4.4 s, no leak |

## 17 Oct: Hack Sprint day 1

All changes keep every existing test green: 58 backend tests (47 old + 11 new) and 11 Playwright browser flows.

### Sarvam: current models, deeper use
| Area | Before | Now | Where |
|---|---|---|---|
| Speech-to-text | `saaras:v3`, plain transcribe | `saaras:v4` in **codemix** mode (English words stay in Latin script inside Hindi/Kannada text) with **keyterms**: names, products and units from the session bias recognition (max 50). v3 is still supported and never receives v4-only fields. | `backend/services/sarvam.py`, `routes/stt.py`, `frontend/src/App.jsx` (`keytermsFor`) |
| Text-to-speech | `bulbul:v3`, one voice (`shubh`) for every language | `bulbul:v4-flash` (launched 13 Oct, recommended, cheaper) with **one persona per language**, Kannada included. Set `SARVAM_TTS_SPEAKER` to force one voice, or `SARVAM_TTS_MODEL=bulbul:v3` to go back. | `sarvam.V4_SPEAKERS`, `sarvam.speaker_for` |
| Chat model | `sarvam-105b`, opt-in, returned empty answers | `sarvam-105b-conversations` (32K, short turns) with `reasoning_effort=low`, `max_tokens=3000`, system prompt and **strict JSON schemas**. The interview agent (gap questions, conflict check) runs on it **by default** and falls back to the main LLM. A circuit breaker pauses it for 10 minutes after two failures, so an outage costs at most two short timeouts. | `sarvam.chat_json`, `services/agent.py` (`COVERAGE_SCHEMA`, `CONFLICT_SCHEMA`), `llm.agent_json` |
| Languages | 6 | 7: **Kannada (kn-IN)** end to end, with demo transcripts for every mode and a Kannada two-speaker meeting demo (spice wholesaler in K.R. Market, Bengaluru). | `shared/*.json`, `models.py`, `app_gen.py`, `client.js` |

The health endpoint (`/api/health`) now reports the STT mode, the v4 speaker map and the agent model, and the "Powered by Sarvam" strip shows the exact model versions in use.

### Stage insurance: response cache
`backend/services/cache.py` stores LLM answers, Bulbul audio and translations on disk under `backend/data/cache`, keyed on a hash of the full request. **Rehearse the demo once; the identical stage run is then instant** (gap check, BRD draft and app generation included). Set `VAANI_CACHE=off` to disable. The cache is never used in place of a missing API key, and the Playwright suite runs with it off.

### Owner-facing Speak screen
The recording step is now one card: speaker chips, a large round microphone button, the live waveform, and the transcript shown as a feed of speaker-attributed lines above the editable transcript box. Document details moved into a collapsed section below. All accessible names used by the browser tests are unchanged.

### Focus
The landing page shows only the BRD flow. The three older document types (public awareness, field audit, B2B deals) remain fully functional behind `?modes=all`.

### Repo hygiene
- `frontend/playwright.config.js` no longer hard-codes a teammate's Windows path. `PW_AUDIT_DIR`, `PW_PYTHON` and `VAANI_DATA_DIR` are environment variables with sane defaults.
- `.env.example` documents the new model defaults.
- `PITCH.md` rewritten for the 18 Oct final (6-minute script, Sarvam-depth slide, Q&A).

### Deck
`VAANI - Hack Sprint 2026.pptx` (next to this repo) is the round-1 deck with every slide rewritten to describe the product that runs: the verifier, conflict detection, voice traceability, 7-language BRD and generated app. Dhandha Twin, ScreenSpec, voice-to-collect and Paytm are gone. Slide 6 now carries a real screenshot of the conflict card instead of a mockup.


### Afternoon additions (17 Oct, 13:00 to 15:00 IST)

#### Recorded meeting with automatic speaker separation
`POST /api/stt/meeting` takes a call recording or WhatsApp voice note (any length up to Sarvam's 2-hour batch limit), runs Sarvam's **batch speech-to-text with diarization** (official `sarvamai` SDK, in a worker thread), keeps the recording as hashed evidence with per-line timestamps, and returns `[Speaker 1] ... / [Speaker 2] ...` lines. On the Speak screen: **Upload a recorded meeting**, then rename "Speaker 1" to "Owner" etc. The existing conflict detector runs unchanged on the result. Verified live: a 30-second two-voice Hindi file came back correctly separated in 7 seconds.

#### Photo or PDF of notes
`POST /api/notes` sends an image or PDF to **Sarvam Doc AI (digitise)**, reads the page blocks in reading order and returns `[Notes] ...` lines that join the transcript. Verified live: a Hindi/English notes image in 2.3 seconds. The problem statement names "notes" as an input; this is the literal match.

#### Instant BRD page
While the reviewer approves rule by rule, the frontend drafts the BRD and generates the app in the background for "all rules approved". The server cache is keyed on request content, so when every rule is approved the real calls return instantly. Skipping a rule simply misses the cache and takes the normal path.

#### Design system v3 ("Ledger": light, editorial)
Two passes. The first (dark slate, teal accent, from Google Stitch's "Luminous Slate") looked like every AI dashboard, so it was replaced. The shipped design is light and document-like, in keeping with a product whose output is a document: white paper, ink text, one deep green accent (#0F6E56) with amber reserved for disagreements, IBM Plex Serif headings, IBM Plex Sans body (with Plex Sans Devanagari and Noto Kannada/Tamil/Telugu/Bengali for Indic text), IBM Plex Mono for IF/THEN/UNLESS logic, hairline rules instead of floating cards, a thin six-step bar in the header, serif pull-quotes for the speaker's exact words. A second Stitch project ("VAANI BRD Review Interface", light "Indian Legal & Statutory Ledger" system) converged on the same direction and is in your Stitch account for reference. Fonts load from Google Fonts with system fallbacks, so the offline standalone build still works. The requirement editor keeps classification, recording and clip fields behind an "advanced" toggle. All accessible names used by the browser tests are unchanged.

#### Tests
64 backend tests (6 new for the meeting and notes routes) and 12 browser flows (1 new: both uploads degrade honestly without Sarvam).

#### Measured accuracy (`backend/benchmark.py` → `BENCHMARK.md`)
A reproducible benchmark for the two features judges ask about. Verifier: 90 cases across the English, Hindi and Kannada meeting demos (numbers nobody said, swapped numbers, English number words, numbers borrowed from another speaker's line, quotes altered by one character, quotes from another meeting): 66/66 planted errors caught, 24/24 genuine requirements accepted. Conflict detector, live on Sarvam 105B: 11 rule sets with 7 planted owner-vs-manager contradictions and 4 controls: 7/7 found, 0 false alarms, about 0.5 s each.

#### Voice sign-off
On the Approve step, *Say haan or nahi to decide* records four seconds, Sarvam transcribes it, and a yes word (हाँ, ಹೌದು, ஆம், అవును, হ্যাঁ, होय, yes…) approves while a no word (नहीं, ಇಲ್ಲ, இல்லை, కాదు, না, नाही, no…) skips. Anything else asks again; the buttons always remain. The BRD records the spoken word: "Approved by Demo reviewer · by voice (हाँ)". Sign-off clips are not added to the meeting's evidence list.

#### Competitive research (17 Oct)
Track 4's statement is Commudle's June 2026 Hack Days Delhi BRD track verbatim; no BRD project placed there, and a Hindi voice BRD agent on Sarvam (REQUIX) lost. On GitHub, the closest thing to the verifier is a zero-star repo that checks quotes by substring and demotes rather than blocks; nobody verifies spoken Indic numbers or attributes conflicts to speakers from diarized audio. Positioning in `PITCH.md` updated accordingly: lead with the verifier and the conflict catch, not with "voice-first BRD".

### Not done (deliberately)
- Realtime streaming speech-to-text (partials while speaking): documented in the plan, not shipped. High risk, needs a beta flag and PCM resampling.
- Real owner recordings and the numbers slide: only the team can do this.


## 16 Oct: BRD agent rebuild

### What changed
1. **The interview agent (new step).** It checks the conversation against an 8-point BRD checklist and shows covered items with their exact quotes. It asks contextual follow-up questions that Sarvam translates and Bulbul speaks. Answers can be spoken (Saaras) or typed. A completeness meter tracks progress, and skipped items become open questions.
2. **A full BRD.** 12 standard sections, functional requirements (FR-01…) with a traceability matrix, acceptance criteria, open questions, a verification report and sign-off. The old "Technical requirements" section, which described Vaani's own stack rather than the client's project, was removed.
3. **The verifier.** It checks quotes, numbers (including Indic digits and English number words), AI suggestions, and repairs near-exact quotes. Python and JavaScript versions give identical results on 16 tricky test cases.
4. **Stakeholder conflict detection.** Requirements carry their speaker. Contradictions between speakers are shown side by side with each person's original audio, plus "keep A / keep B / decide later" choices.
5. **"Hear the source".** Sarvam's chunk timestamps are mapped to each requirement's quote, so the BRD plays the exact clip. Before, the code matched only single-word quotes, so clips almost never worked.
6. **Sarvam voice and translation.** The existing text-to-speech route sent `target_language_code`, but the API expects `language_code`, so it never worked. That is fixed, and Bulbul is now used for agent questions, rule read-back and "Listen to BRD". Sarvam Translate is used for questions and for showing the BRD in 6 languages.
7. **The app is generated from the approved BRD by the LLM.** It runs sandboxed with no network access. The fallback for BRDs is now a requirement simulator built from the actual rules, replacing an iron-scrap template that appeared for every business.
8. **Exports:** PDF (print), Word (.docx), Markdown and Jira CSV.
9. **Flow simplified to 6 steps.** The "scenario walkthrough" (illustrative chart data) and the template preview step were removed.
10. **Robustness.** One retry on LLM errors, malformed rules rejected one at a time, failure reasons logged, and the Gemini key sent in a header instead of the URL.


### Live-testing fixes (16 Oct)
- Gemini wrote "fifty kg" in words, which bypassed the digit check. Fixed: English number words are parsed, and the prompt requires digits.
- The business prompt's category list made Gemini invent its own JSON layout. Fixed: reworded, with exact top-level keys required.
- Gemini dropped a Hindi vowel sign, and used "。" instead of "।", when copying quotes. Fixed: near-exact quote repair that always uses the real transcript text.
- Gemini returned the prompt's own label "AI suggestion, please confirm." as content. Fixed: reworded the prompt and filtered placeholders.
- sarvam-105b returned empty answers (its whole budget went to reasoning), so it is opt-in, not the default.
