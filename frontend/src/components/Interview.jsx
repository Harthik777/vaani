import { useEffect, useRef, useState } from "react";
import { api, playClips, speak } from "../api/client.js";

const ICON = { covered: "✅", answered: "🗣️", missing: "⬜", skipped: "⏭️" };

// The BRD agent: shows what is already covered (with the exact words), asks for what is missing, by voice.
export default function Interview({ gaps, busy, lang, langLabel, a11y, sarvamVoice, recorder, draft, onDraft, skipped, onSave, onSkip, onRetry, onContinue, onVoiceUsed, demo, keyterms = [] }) {
  const [voiceMessage, setVoiceMessage] = useState("");
  const [speaking, setSpeaking] = useState(false);
  const [autoAsk, setAutoAsk] = useState(a11y !== "deaf");
  const stop = useRef(null);
  const questions = (gaps?.questions || []).filter(q => !skipped.includes(q.key));
  const current = questions[0];
  const recording = recorder.recording || recorder.processing > 0;

  const ask = async q => {
    if (!q || a11y === "deaf") return;
    stop.current?.(); setVoiceMessage(""); setSpeaking(true);
    const text = q.question_local || q.question;
    try {
      if (!sarvamVoice) { speak(text, q.question_local ? lang : "english"); setVoiceMessage("Browser voice (Sarvam voice is not configured)."); setSpeaking(false); return; }
      // The gap check already prepared Bulbul audio for the first question: no second round trip.
      if (gaps?.first_audio?.length && gaps.questions?.[0]?.key === q.key) {
        onVoiceUsed?.(!!q.question_local);
        stop.current = playClips(gaps.first_audio, error => { setSpeaking(false); if (error) setVoiceMessage(error.message); });
        return;
      }
      // A translated question is spoken as-is; otherwise Sarvam translates the English question first.
      const result = await api.tts({ text, lang, translate: !q.question_local && lang !== "english", keyterms });
      onVoiceUsed?.(result.translated);
      stop.current = playClips(result.audios, error => { setSpeaking(false); if (error) setVoiceMessage(error.message); });
    } catch (e) { setSpeaking(false); setVoiceMessage(e.message); }
  };
  useEffect(() => { if (autoAsk && current && !busy) ask(current); return () => stop.current?.(); }, [current?.key, current?.question_local, busy]);

  const [elapsed, setElapsed] = useState(0);
  useEffect(() => { if (!busy) { setElapsed(0); return; } const t0 = Date.now(); const iv = setInterval(() => setElapsed(Math.round((Date.now() - t0) / 1000)), 1000); return () => clearInterval(iv); }, [busy]);
  const items = (gaps?.items || []).map(i => i.status === "missing" && skipped.includes(i.key) ? { ...i, status: "skipped" } : i);
  const pct = gaps?.completeness ?? 0;
  return <section className="interview">
    <div className="meter-card card">
      <div className="meter-head"><div><div className="eyebrow">BRD completeness</div><strong className="meter-pct">{gaps ? pct + "%" : "…"}</strong></div>
        <p className="source-note">Checked by: {gaps?.brain || "…"}{gaps?.translated_with_sarvam ? " · questions translated with Sarvam Translate" : ""}</p></div>
      <div className="meter" role="progressbar" aria-label="BRD completeness" aria-valuenow={pct} aria-valuemin="0" aria-valuemax="100"><span style={{ width: pct + "%" }} /></div>
      {gaps?.warning && <p className="notice">{gaps.warning}</p>}
      <ul className="checklist-grid">{items.map(i => <li key={i.key} className={"ck ck-" + i.status}>
        <span aria-hidden="true">{ICON[i.status]}</span><span><b>{i.label}</b> <small>{i.status === "covered" ? "already said" : i.status}</small>
          {i.source_quote && <q>{i.source_quote}</q>}</span></li>)}</ul>
    </div>

    {busy && <p role="status" className="agent-thinking">🧠 The agent is reading everything said so far… {elapsed > 2 ? `${elapsed}s · ` : ""}{elapsed < 4 ? "checking the 8 things a BRD needs" : elapsed < 9 ? "writing follow-up questions in your language" : "almost there"}</p>}
    {!busy && !gaps && <div className="card"><p>The agent has not checked this transcript yet.</p><button className="btn btn-primary" onClick={onRetry}>Check what is missing</button></div>}

    {!busy && current && <article className="card question-card" aria-live="polite">
      <div className="eyebrow">Agent question · {current.label} · {questions.length} left</div>
      {current.question_local && <h2 className="q-local" lang={lang}>{current.question_local}</h2>}
      <p className={current.question_local ? "q-en" : "q-main"}>{current.question}</p>
      {a11y !== "deaf" && <div className="actions">
        <button className="btn btn-ghost" disabled={speaking} onClick={() => ask(current)}>🔊 {speaking ? "Asking…" : `Ask aloud${sarvamVoice ? " (Sarvam Bulbul)" : ""}`}</button>
        <label className="toggle"><input type="checkbox" checked={autoAsk} onChange={e => setAutoAsk(e.target.checked)} /> Ask each question automatically</label>
      </div>}
      {voiceMessage && <p className="source-note">{voiceMessage}</p>}
      <label htmlFor="answer">Answer in {langLabel} (speak or type)</label>
      <textarea id="answer" className="transcript answer-box" value={draft} disabled={recording} placeholder="Your answer…" onChange={e => onDraft(e.target.value)} />
      <div className="actions">
        {a11y !== "deaf" && <button className={"btn " + (recorder.recording ? "btn-rec" : "btn-primary")} disabled={!recorder.recording && recorder.processing > 0}
          onClick={recorder.recording ? recorder.stop : () => { stop.current?.(); recorder.start(); }}>{recorder.recording ? "⏹ Stop answer" : "🎙 Record answer"}</button>}
        {recorder.processing > 0 && <span role="status">Transcribing with Sarvam…</span>}
        {demo && gaps?.sample_answers?.[current.key] && <button className="btn btn-ghost" disabled={recording} onClick={() => onDraft(gaps.sample_answers[current.key])}>Use sample answer</button>}
        <button className="btn btn-ok" disabled={!draft.trim() || recording} onClick={() => onSave(current, draft.trim())}>Save answer →</button>
        <button className="btn btn-ghost" disabled={recording} onClick={() => onSkip(current.key)}>Skip (add to open questions)</button>
      </div>
    </article>}

    {!busy && gaps && !current && <div className="card done-card"><h2>{pct === 100 ? "🎉 Everything a BRD needs is captured." : "All questions answered or skipped."}</h2>
      <p>Skipped items will appear as open questions in the BRD.</p></div>}
    <div className="actions"><button className="btn btn-primary btn-full" disabled={busy || recording} onClick={onContinue}>Extract requirements →</button></div>
  </section>;
}
