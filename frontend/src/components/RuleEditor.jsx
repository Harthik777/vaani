import SourceAudio from "./SourceAudio.jsx";
import { VerifyBadge } from "./Verifier.jsx";
export default function RuleEditor({ rule, check, onChange, onDelete, evidence }) {
  const set = (key, value) => onChange({ ...rule, [key]: value, approved_at: null, ...(key === "source_quote" ? { quote_note: null } : {}) });
  return <fieldset className={"card rule-editor rule-" + (check?.status || "none")}><legend>{rule.title || "New requirement"}</legend>
    <VerifyBadge check={check} />
    <div className="form-grid">{[["title", "Title"], ["condition", "If / context"], ["action", "Then / action"], ["exception", "Unless / exception"]].map(([key, label]) =>
      <label key={key}>{label}<input value={rule[key] || ""} required={key !== "exception"} onChange={e => set(key, e.target.value)} /></label>)}
      <label>Spoken by<input value={rule.speaker || ""} placeholder="Speaker" onChange={e => set("speaker", e.target.value || null)} /></label>
    </div>
    <details className="advanced"><summary>Classification, source recording and clip range</summary><div className="form-grid">
      <label>Classification<select value={rule.type} onChange={e => set("type", e.target.value)}>
        {[...new Set([rule.type, "requirement", "critical", "moderate", "compliant", "commercial", "payment", "quality"])].map(t => <option key={t}>{t}</option>)}
      </select></label>
      <label>Source recording<select value={rule.evidence_id || ""} onChange={e => set("evidence_id", e.target.value || null)}>
        <option value="">Text source only</option>{evidence.map((a, i) => <option key={a.id} value={a.id}>Recording {i + 1}{a.speaker ? " · " + a.speaker : ""} · {a.captured_at}</option>)}
      </select></label>
      <label>Clip start (seconds)<input type="number" min="0" step="0.1" value={rule.start ?? ""} onChange={e => set("start", e.target.value === "" ? null : Number(e.target.value))} /></label>
      <label>Clip end (seconds)<input type="number" min="0" step="0.1" value={rule.end ?? ""} onChange={e => set("end", e.target.value === "" ? null : Number(e.target.value))} /></label>
    </div></details>
    <label>Exact source text<textarea value={rule.source_quote || ""} onChange={e => set("source_quote", e.target.value)} /></label>
    <SourceAudio evidence={evidence.find(a => a.id === rule.evidence_id)} start={rule.start} end={rule.end} />
    <button className="btn btn-ghost" onClick={onDelete}>Remove requirement</button>
  </fieldset>;
}
