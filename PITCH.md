# VAANI · the pitch (6 minutes, final round)

> **One sentence:** a spice wholesaler in Indore tells VAANI what he needs, in Hindi; his manager disagrees on one number;
> VAANI catches it with both voices, blocks anything nobody said, and hands the IT vendor a BRD and a first app the owner can
> hear, read in his own language, and approve in one tap.

Judges score the story and the demo, not the repository. One user, one loss, one catch, one number. Nothing else.

## The story (90 seconds, before touching the laptop)

"Rajesh runs a spice wholesale in Indore. Last year he paid a freelancer ₹1.8 lakh for a stock app. The freelancer wrote the
requirements in English from a phone call. The reorder alert was set to 50 kg. Rajesh's manager had said 100 kg, because
in festival season 50 is too late. Nobody caught it. Stock ran out on Diwali week. The app was rebuilt twice.

That is the problem: between an owner who speaks Hindi and a vendor who writes English, requirements change, and nobody can
prove what was actually said. Every requirements tool starts from text someone typed. VAANI starts from the voice, and
never lets a number into the document that the voice did not say."

## The demo (3 minutes, in this order, nothing else)

Before the pitch: backend running with `--host 0.0.0.0`, frontend built, two full rehearsals so every voice line and draft
is in the cache. Language chip on हिंदी: the whole interface is in Hindi, not only the voice.

1. **Speak.** Live: two teammates read the six lines of `docs/RECORD-THESE-LINES.md` as Owner and Manager (tap the chip before
   each). Backup: *Use 2-speaker meeting demo* loads the same lines with Bulbul voices in two personas. Say: "Saaras separates
   the two speakers. Every line is hashed and kept as evidence."
2. **Agent.** *Next.* The agent (Sarvam 105B) shows the eight things a BRD needs, three already covered with exact quotes, and
   asks the first missing one aloud in Hindi. Answer one question. Say: "It only asks what was not said."
3. **The catch.** *Extract.* Point at the red card: "Owner said 50 kg, manager said 100. Both clips are right there. Keep the
   manager's version." Then open *More* and press *Show the verifier catching a lie*: a 48-hour deadline nobody spoke appears in
   red at once. "No AI did that. It is a deterministic check. We planted 66 such errors across three meetings; it caught 66."
4. **Approve.** *Approve 4 verified.* "Verified requirements do not need a human to re-read them. Flagged ones do." The BRD and
   the app were already building while we spoke.
5. **BRD + app.** Scroll once: vendor hand-off table with FR ids, acceptance criteria and a *hear it* button per row; the
   generated app; *Switch BRD + app to हिंदी*. *Publish*: hand the phone QR to a judge. "Same Wi-Fi, opens on your phone,
   with the voices."

Stop there. Do not show exports, email, Excel, the guide or other document types unless asked.

## Numbers (one slide, 30 seconds)

| Claim | Measured |
|---|---|
| Verifier: planted errors caught (3 languages) | 66 / 66, 0 false blocks (`BENCHMARK.md`) |
| Stakeholder conflicts found | 7 / 7, 0 false alarms, Sarvam 105B |
| Next agent question after an answer | 4.0 s → 0.1 s |
| Extraction with conflicts | 8.5 s → 1.7 s |
| BRD + app after approval | 19.3 s → 6 s (built in parallel during review) |
| Tests | 90 backend, 13 browser flows, run in CI |

## Who pays (one slide, 20 seconds)

Freelancers and small IT firms that build for MSMEs, per BRD. They lose the most to rework and they cannot dispute a
requirement the client can hear in his own voice. Sarvam because code-mixed Hindi, Kannada and Tamil speech, pronunciation
and diarization are where English-first models fail, and the client has to trust the quote.

## The three answers every teammate must give in one breath

**"How does the verifier work?"** "It is not AI. Every requirement carries the exact quote and the numbers it uses. The quote
must appear verbatim in the transcript and every number must appear in that quote, with Indic digits and Indian grouping
normalised. If either fails, the requirement is blocked and shown in red. The AI drafts; the verifier decides."

**"Why not ChatGPT?"** "ChatGPT writes a fluent BRD with numbers it invented. We measured it: planted errors sail through.
VAANI blocks 66 of 66. And ChatGPT cannot tell you the manager disagreed with the owner, because it never heard two voices."

**"Who is the user, the owner or the vendor?"** "The vendor pays; the owner speaks. The owner's job is ten minutes of talking
and one approval tap in his language. The vendor gets the English BRD, the acceptance criteria, Jira tickets and the voice
behind every line."

## If something breaks

- Voice fails or Sarvam credits run out: *Play the 2-minute narrated demo* on the landing page runs the whole flow from cache.
- Internet fails: the fixture path takes over automatically; the screen says so honestly.
- A judge asks for Kannada or Tamil: the interface, voices and demo exist for both.
