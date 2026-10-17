import { STATUS_LABEL } from "../data/verify.js";
import SourceAudio from "./SourceAudio.jsx";

const NUMBER_ICON = { exact: "✅", interpreted: "🔶", unsupported: "⛔" };

export function VerifyBadge({ check }) {
  if (!check) return null;
  return <div className={"verify verify-" + check.status}>
    <span className="verify-status">{STATUS_LABEL[check.status] || check.status}</span>
    {!!check.numbers?.length && <span className="num-chips">{check.numbers.map(n =>
      <span key={n.value} className={"num num-" + n.status} title={n.status === "interpreted" ? "The AI read this number from the spoken words. Please confirm." : n.status === "unsupported" ? "Nobody said this number." : "This number appears in the speech."}>
        {NUMBER_ICON[n.status]} {n.value}{n.status === "interpreted" ? <> ← <q>{n.spoken}</q></> : n.status === "unsupported" ? " (not spoken)" : ""}
      </span>)}</span>}
    {!!check.vague?.length && <span className="num-chips">{check.vague.map(v => <span key={v.term} className="num num-vague" title={v.question}>🔎 “{v.term}” · {v.question}</span>)}</span>}
    {check.quote_note && <span className="quote-note">🔧 {check.quote_note}</span>}
  </div>;
}

export function VerifierSummary({ rules, checks, rejected = [], brain }) {
  const count = status => checks.filter(c => c.status === status).length;
  return <aside className="card verifier" aria-label="Verifier">
    <div className="verifier-head"><h2>🛡️ Verifier</h2><span className="source-note">Every requirement must quote the speaker exactly, and every number must have been said.{brain ? ` Drafted by ${brain}.` : ""}</span></div>
    <div className="verifier-counts">
      <span className="vc vc-ok">✅ {count("verified")} verified</span>
      <span className="vc vc-warn">🔶 {count("needs_confirmation")} numbers to confirm</span>
      <span className="vc vc-bad">⛔ {count("unsupported_number") + count("rejected")} problem{count("unsupported_number") + count("rejected") === 1 ? "" : "s"}</span>
      <span className="vc vc-bad">🚫 {rejected.length} AI claim{rejected.length === 1 ? "" : "s"} blocked</span>
      <span className="vc vc-warn">🔎 {checks.reduce((n, c) => n + (c.vague?.length || 0), 0)} vague term{checks.reduce((n, c) => n + (c.vague?.length || 0), 0) === 1 ? "" : "s"} to clarify</span>
    </div>
    {!!rejected.length && <ul className="rejected-list">{rejected.map((r, i) => <li key={i}><s>{r.title ? r.title + ": " : ""}{r.text}</s> <span className="reason">{r.reason}{r.source_quote ? ` · claimed quote: “${r.source_quote}”` : ""}</span></li>)}</ul>}
    {!rules.length && <p>No requirements yet.</p>}
  </aside>;
}

export function ConflictCard({ conflict, rules, evidence, onKeep, onLater }) {
  const pair = conflict.rule_ids.map(id => rules.find(r => r.id === id)).filter(Boolean);
  if (pair.length !== 2) return null;
  return <article className="card conflict-card" role="alert">
    <h2>⚠️ Stakeholders disagree: {conflict.topic}</h2>
    <p>{conflict.explanation}</p>
    <div className="conflict-pair">{pair.map(r => <div key={r.id} className="conflict-side">
      <span className="speaker-chip">{r.speaker || "Unknown speaker"}</span>
      <h3>{r.title}</h3><p className="logic">IF {r.condition} THEN {r.action}</p><blockquote>{r.source_quote}</blockquote>
      <SourceAudio evidence={evidence.find(e => e.id === r.evidence_id)} start={r.start} end={r.end} />
      <button className="btn btn-ok" onClick={() => onKeep(r.id, pair.find(o => o.id !== r.id).id)}>Keep {r.speaker ? r.speaker + "'s" : "this"} version</button>
    </div>)}</div>
    <button className="btn btn-ghost" onClick={onLater}>Decide later (keep both, list as open question)</button>
  </article>;
}
