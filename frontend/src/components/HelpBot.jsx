import { useEffect, useRef, useState } from "react";
import { api, playClips } from "../api/client.js";

// The in-app guide: a small panel that answers "what do I do now?" for the current step, in the user's language.
// Deterministic answers come from the server even without AI; with AI configured, Sarvam 105B answers the question.
export default function HelpBot({ phase, lang, langLabel, counts, sarvamVoice, a11y, onSarvamUsed }) {
  const [open, setOpen] = useState(false), [messages, setMessages] = useState([]), [input, setInput] = useState("");
  const [busy, setBusy] = useState(false), [suggestions, setSuggestions] = useState([]), [speaking, setSpeaking] = useState(false);
  const stop = useRef(null), list = useRef(null);
  const ask = async question => {
    const q = (question || "").trim();
    if (!q || busy) return;
    setBusy(true); setInput("");
    setMessages(m => [...m, { role: "you", text: q }]);
    try {
      const out = await api.help({ question: q, phase, lang, counts });
      setMessages(m => [...m, { role: "guide", text: out.answer, brain: out.brain }]);
      setSuggestions(out.suggestions || []);
    } catch (e) { setMessages(m => [...m, { role: "guide", text: e.message }]); }
    finally { setBusy(false); }
  };
  // Opening the panel on a new step shows that step's orientation without a question.
  useEffect(() => {
    if (!open) return;
    let active = true;
    api.help({ question: "", phase, lang, counts }).then(out => { if (active) { setSuggestions(out.suggestions || []); setMessages(m => m.length ? m : [{ role: "guide", text: out.answer, brain: out.brain }]); } }).catch(() => {});
    return () => { active = false; };
  }, [open, phase]);
  useEffect(() => { list.current?.scrollTo(0, list.current.scrollHeight); }, [messages.length, busy]);
  const speakLast = async () => {
    const last = [...messages].reverse().find(m => m.role === "guide");
    if (!last || !sarvamVoice) return;
    stop.current?.(); setSpeaking(true);
    try {
      const result = await api.tts({ text: last.text, lang, translate: false });
      onSarvamUsed?.({ tts: true });
      stop.current = playClips(result.audios, () => setSpeaking(false));
    } catch { setSpeaking(false); }
  };
  return <div className={"helpbot" + (open ? " open" : "")}>
    {!open && <button className="help-fab" onClick={() => setOpen(true)} aria-label="Open the guide">? Help</button>}
    {open && <section className="help-panel" aria-label="Guide">
      <header><strong>Guide</strong><span className="source-note">answers in {langLabel}</span><button className="btn-link" onClick={() => { stop.current?.(); setOpen(false); }} aria-label="Close the guide">Close</button></header>
      <div className="help-list" ref={list}>
        {messages.map((m, i) => <p key={i} className={"help-msg help-" + m.role}>{m.text}{m.brain && m.brain !== "guide" && <small> · {m.brain}</small>}</p>)}
        {busy && <p className="help-msg help-guide">…</p>}
      </div>
      <div className="help-suggest">{suggestions.map(s => <button key={s} className="chip" disabled={busy} onClick={() => ask(s)}>{s}</button>)}</div>
      <form className="help-form" onSubmit={e => { e.preventDefault(); ask(input); }}>
        <input id="help-input" value={input} placeholder="Ask anything about this step…" aria-label="Ask the guide" onChange={e => setInput(e.target.value)} disabled={busy} />
        <button className="btn btn-primary" disabled={busy || !input.trim()}>Ask</button>
        {a11y !== "deaf" && sarvamVoice && <button type="button" className="btn btn-ghost" disabled={speaking || !messages.some(m => m.role === "guide")} onClick={speakLast}>🔊</button>}
      </form>
    </section>}
  </div>;
}
