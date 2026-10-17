# Vaani pitch guide (Hack Sprint, MIT Bengaluru, 18 Oct 2026 · Track 4 Applied AI · PS41)

Every claim below is something the code does today. If a judge asks "show me", you can.

## One line
> **Vaani interviews business owners in their own language, blocks anything nobody said, catches the owner and the manager disagreeing, and hands the IT vendor an English BRD where every requirement plays back in the speaker's own voice.**

## Why this matters
- Owners explain needs in Kannada, Hindi or Tamil. Vendors need precise English BRDs.
- What gets lost: missing budgets and deadlines, numbers changed in translation, and stakeholders who contradict each other.
- Vaani's answer: an **agent** that finds the gaps, a **verifier** that blocks anything nobody said, **conflict detection** between speakers, and **voice traceability** for every requirement.

## Positioning (read this before you write a single slide)
This exact problem statement ran at Commudle's Hack Days Delhi in June 2026. No BRD project placed. A Hindi voice-to-BRD agent on Sarvam (REQUIX) was submitted and lost to a live mock-interviewer and a health app. "Speak in Hindi, get a BRD" is table stakes in this room, and the other PS41 team (Awaaz) uses the same words: evidence-backed, Kannada/Hindi, human review.
Lead with the two things nobody else has shipped, in this order:
1. **The verifier catches a number nobody said, live.** Measured: 66 of 66 planted errors caught, 0 false blocks on 24 genuine requirements (`BENCHMARK.md`).
2. **Owner vs manager disagreement from a recorded call, separated by Sarvam diarization.** Measured: 7 of 7 planted conflicts found, 0 false alarms, on Sarvam 105B in about half a second each.
Then voice sign-off, then the BRD and app. Say "voice-first BRD" last, not first.

## The 6-minute script (cut from the end if the slot is shorter)

**[0:00–0:20] Hook with a real person.**
"[First name], who runs the [shop] outside the Yelahanka gate, told us in Kannada what app she needs. Her vendor needs it in English. Here is what usually gets lost, and what we did about it." (Use the owner you recorded today. If you could not record anyone, use the Indore spice wholesaler story.)

**[0:20–3:40] Live demo.** Click path: *हिंदी* or *ಕನ್ನಡ* → *Start capturing*. Then choose one setup:
- **Recommended: live voice.** Two teammates read the six lines of `shared/meeting.json` aloud (Hindi or Kannada). Select *Owner* or *Manager* (add "Manager" with *Add speaker*) before each person speaks. The transcript appears line by line with a speaker chip. This is the only setup with "hear the source" clips.
- **Backup:** *Use 2-speaker meeting demo*. Same transcript, no audio, instant.

1. *Next: agent checks for gaps.* "It found the goal, features and constraints, with the exact words. It is missing users, timeline, budget, success measure and sign-off." Let it **ask aloud** (Sarvam Translate + Bulbul). Record or *Use sample answer*, save. "The meter climbs."
2. *Extract requirements.* **"Watch this:"** "The owner said 50 kg; the manager said 100 kg. Vaani caught the contradiction, with both voices." Keep the manager's version.
3. **The verifier, live.** Type `48` into a rule: "⛔ 48 (not spoken). The AI can't sneak a number in, and neither can we." Undo it. Point at a 🔎 chip: "And it won't let 'jaldi' into a contract either; it asks how many hours."
4. **Approve by voice.** Play the original clip, let Bulbul read the rule back in the owner's language, then press *Say haan or nahi to decide* and say "हाँ" (or "ಹೌದು"). The requirement is approved with the spoken word recorded against it; the BRD shows "by voice (हाँ)". Do this once; use the buttons for the rest.
5. **BRD + App:** "12 sections, FR-IDs, acceptance criteria, open questions." Show the **verification report**: "Anything the AI wrote that nobody said is blocked here." Switch BRD + app to हिंदी / ಕನ್ನಡ in one click. *Listen to BRD summary*. **⬇ Download**: Word (bilingual), **Jira CSV** ("the vendor gets tickets"). Click around the generated app, or the requirement simulator (move the slider below 100 kg, the alert fires).
6. *Publish* → two **QR codes** appear: "Scan this and the BRD with the voice clips opens on your phone." Hand the laptop to a judge for the scan, or tap the **WhatsApp** link to forward it.

**[3:40–4:30] Why it is different (one slide).**
"ChatPRD, Jira Rovo and Notion take typed English from product managers and never verify. Lovable and Bolt take typed English prompts. Paytm Soundbox and Khatabook answer questions; they don't build software. Nobody interviews, verifies spoken numbers, or detects two stakeholders disagreeing." Do not name other teams in the room.

**[4:30–5:10] Sarvam depth (one slide, plain words).**
- **Saaras v4** hears every speaker, code-mixed ("मुझे stock alert चाहिए"), with the session's product names as keyterms and chunk timestamps for the voice clips.
- **Bulbul v4-flash** asks the questions and reads rules back, one persona per language, Kannada included.
- **Sarvam Translate** puts the questions and the whole BRD in any of 7 languages.
- **Sarvam 105B** phrases the interview questions and checks for conflicts (strict JSON schema); Gemini drafts the long BRD and the app. Say that plainly if asked.

**[5:10–5:45] Numbers (one slide).** Verifier: 66/66 planted errors caught, 0 false blocks (3 languages). Conflict detector: 7/7 found, 0 false alarms, 0.5 s each on Sarvam 105B. Diarized meeting: 30 s two-voice file separated correctly in 7 s. 64 backend tests, 12 browser flows. A full session costs under ₹5 in Sarvam credits. **Who pays:** IT services firms and freelancers building for MSMEs: fewer rework cycles, requirements the client cannot dispute.

**[5:45–6:00] Close.** "Owners speak. Vendors build. Nothing gets lost in between. **Vaani: your words, verified.**"

## Live-demo safety
- **Rehearse the exact demo once before the pitch with the backend running.** LLM drafts, Bulbul audio and translations are cached on disk (`backend/data/cache`), so the identical stage run is instant. Only live microphone speech is truly live.
- Backup: the meeting demo also runs with **no backend** (sample data, labelled DEMONSTRATION), and so does `vaani-prototype.html`.
- Use Chrome, allow the microphone before the demo, volume up for Bulbul. Phone hotspot ready.
- If Sarvam's chat model is slow or down, the agent falls back to Gemini automatically and the strip shows which brain answered.

## Judge Q&A (honest answers)
**"Other teams also do voice-to-BRD on Sarvam. What is different?"** "Transcribing and drafting is the easy half; every team here does it. We planted 66 errors into three meetings and the verifier caught all 66. We planted 7 stakeholder conflicts and it found all 7 with no false alarms. Nobody else can show you that number because nobody else has the verifier." Then show BENCHMARK.md if asked.

**"Isn't this just a Gemini wrapper?"** The model drafts; the verifier decides. Quotes must be verbatim, numbers must be spoken, suggestions can't carry numbers, and contradictions must name real requirements from different speakers. Rejections are shown, not hidden. The same checks run in the browser on every edit.

**"Where exactly does Sarvam do the work?"** Saaras v4 for every recording and answer (codemix mode, keyterms, timestamps). Translate for questions and the BRD in 7 languages. Bulbul v4-flash for spoken questions, read-back and the BRD summary. Sarvam 105B (conversations model) for the interview questions and the conflict check. Gemini for the long BRD draft and the app, because those are 20–35 second generations and 105B's reasoning budget made them unreliable in our tests.

**"How do you stop hallucinated numbers?"** Every number must appear in its quote. Sarvam writes Hindi numbers as words, so the model must point to the exact spoken words ("50 ← पचास") and a human confirms. English number words are parsed too, so "fifty" can't bypass it.

**"How do you know who spoke?"** Speakers are selected before each recording. Sarvam's diarization is batch-only (recorded files), so automatic speaker detection for uploaded meetings is the next step; the conflict detector already works per speaker.

**"What about my language?"** Seven in the UI today, Kannada included. Sarvam Translate and Saaras v4 cover all 22 scheduled languages, so adding one is a config line.

**"Is the approval a legal signature?"** No. It records who approved what and when. The audio hash shows the recording wasn't altered; it doesn't prove identity. We say so in the product.

**"What breaks?"** Clips under 3 seconds with auto language detection; very long meetings on the live-mic path (30-second segments). Name it before they do.

**"What was the Paytm / Dhandha Twin slide in round 1?"** An earlier concept. We narrowed to the requirements problem because that is where the loss happens; payments are a vendor's feature, not Vaani's.

## Don't say
"world's first", "zero hallucinations", "100% accurate" (say "66 of 66 in our benchmark"), "legally binding", "works offline" (only the demo does), "word-level timestamps" (they are phrase-level), "automatic speaker detection" (manual today).
