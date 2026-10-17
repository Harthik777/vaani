import { useRef, useState } from "react";
import { api, playClips, speak } from "../api/client.js";
import { ruleText } from "../data/compiler.js";
import SourceAudio from "./SourceAudio.jsx";
import { VerifyBadge } from "./Verifier.jsx";

// Sign-off card: the reviewer hears the original speaker AND the rule read back in their own language before approving.
export default function RuleCard({ r, check, lang, evidence = [], a11y, sarvamVoice, onSarvamUsed }) {
  const [message, setMessage] = useState(""), [playing, setPlaying] = useState(false);
  const stop = useRef(null);
  const readBack = async () => {
    stop.current?.(); setMessage("");
    if (!sarvamVoice) { speak(ruleText(r), lang); setMessage("Browser voice reading the English rule (Sarvam is not configured)."); return; }
    setPlaying(true);
    try {
      const result = await api.tts({ text: `${r.title}. ${ruleText(r).replace(/^IF /, "If ").replace(" THEN ", ", then ").replace(" UNLESS ", ", unless ")}.`, lang, translate: lang !== "english" });
      onSarvamUsed?.({ tts: true, translate: result.translated });
      setMessage(result.translated ? "Sarvam translation: " + result.text : "");
      stop.current = playClips(result.audios, error => { setPlaying(false); if (error) setMessage(error.message); });
    } catch (e) { setPlaying(false); setMessage(e.message); }
  };
  return <article className="rule"><div className="rh"><h3>{r.title}</h3>{r.speaker && <span className="speaker-chip">{r.speaker}</span>}<span className="badge">{r.type} · {r.confidence}</span></div>
    <p className="logic">{ruleText(r)}</p>
    <VerifyBadge check={check} />
    <blockquote>{r.source_quote}</blockquote>
    <SourceAudio evidence={evidence.find(e => e.id === r.evidence_id)} start={r.start} end={r.end} caption={r.start != null ? `🔊 Original voice · ${r.start}s–${r.end}s` : undefined} />
    {a11y !== "deaf" && <button className="play" disabled={playing} onClick={readBack}>🔊 {playing ? "Reading…" : sarvamVoice ? "Read this rule back in my language (Sarvam)" : "Read rule aloud (browser voice)"}</button>}
    {message && <p className="source-note">{message}</p>}
  </article>;
}
