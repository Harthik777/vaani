# Vaani implementation report (2026-10-16)

This replaces the earlier report. Several of that report's claims did not match the code: an LLM-generated app that was never called, "word-level timestamps", "offline compiler". See README.md for the current, verified description.

## What changed
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

## Live verification with real keys (2026-10-16, Hindi meeting with numbers spoken as words)
| Step | Time | Result |
|---|---|---|
| Gap check (Gemini + Sarvam Translate) | ~17 s | Contextual questions, natural Hindi translations |
| Extraction | ~7–15 s | 6 rules, speakers attributed; numbers shown as 50 ← "पचास" for confirmation |
| Conflict check | ~9 s | Found Owner 50 kg vs Manager 100 kg |
| BRD drafting | ~35 s | 16 grounded items kept; "Zero missed orders" blocked (nobody said zero) |
| App generation | ~17 s | 12–19 KB single-file app, no network calls |
| Translate + Bulbul (Tamil) | ~2 s | Works |
| Sarvam Saaras STT | ~1.3 s / 5 s clip | Hindi numbers transcribed as words; timestamps are phrase chunks |

## Issues found during live testing, and the fixes
- Gemini wrote "fifty kg" in words, which bypassed the digit check. Fixed: English number words are parsed, and the prompt requires digits.
- The business prompt's category list made Gemini invent its own JSON layout. Fixed: reworded, with exact top-level keys required.
- Gemini dropped a Hindi vowel sign, and used "。" instead of "।", when copying quotes. Fixed: near-exact quote repair that always uses the real transcript text.
- Gemini returned the prompt's own label "AI suggestion, please confirm." as content. Fixed: reworded the prompt and filtered placeholders.
- sarvam-105b returned empty answers (its whole budget went to reasoning), so it is opt-in, not the default.

## Tests
- Backend: `python -m unittest tests/test_workflows.py tests/test_brd_agent.py`, 43 tests, all passing.
- Browser: `npx playwright test`, 11 flows, all passing, including the full meeting demo: interview → conflict → verifier → BRD → Markdown, Jira and Word downloads, and the simulator slider.
