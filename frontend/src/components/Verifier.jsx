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

export function VerifierSummary({ rules, checks, rejected = [], brain, t = s => s }) {
  const count = status => checks.filter(c => c.status === status).length;
  return <aside className="card verifier" aria-label="Verifier">
    <div className="verifier-head"><h2>🛡️ {t("Verifier")}</h2><span className="source-note">{t("Every requirement must quote the speaker exactly, and every number must have been said.")}{brain ? ` ${t("Drafted by")} ${brain}.` : ""}</span></div>
    <div className="verifier-counts">
      <span className="vc vc-ok">✅ {count("verified")} {t("verified")}</span>
      <span className="vc vc-warn">🔶 {count("needs_confirmation")} {t("numbers to confirm")}</span>
      <span className="vc vc-bad">⛔ {count("unsupported_number") + count("rejected")} {t("problems")}</span>
      <span className="vc vc-bad">🚫 {rejected.length} {t("AI claims blocked")}</span>
      <span className="vc vc-warn">🔎 {checks.reduce((n, c) => n + (c.vague?.length || 0), 0)} {t("vague terms to clarify")}</span>
    </div>
    {!!rejected.length && <ul className="rejected-list">{rejected.map((r, i) => <li key={i}><s>{r.title ? r.title + ": " : ""}{r.text}</s> <span className="reason">{r.reason}{r.source_quote ? ` · claimed quote: “${r.source_quote}”` : ""}</span></li>)}</ul>}
    {!rules.length && <p>No requirements yet.</p>}
  </aside>;
}

export function ConflictCard({ conflict, rules, evidence, onKeep, onLater, onResolve, onAccept, t = s => s }) {
  const pair = conflict.rule_ids.map(id => rules.find(r => r.id === id)).filter(Boolean);
  if (pair.length !== 2) return null;
  const p = conflict.proposal;
  return <article className="card conflict-card" role="alert">
    <h2>⚠️ {t("Stakeholders disagree")}: {conflict.topic}</h2>
    <p>{conflict.explanation}</p>
    {onResolve && !p && <div className="actions"><button className="btn btn-primary" disabled={conflict.resolving} onClick={() => onResolve(conflict)}>🤝 {conflict.resolving ? t("The agent is reconciling…") : t("Ask the agent to reconcile both")}</button>
      {conflict.resolveError && <span className="source-note">{conflict.resolveError}</span>}</div>}
    {p && <div className="proposal">
      <div className="eyebrow">{t("The agent proposes one rule for both")}</div>
      <h3>{p.title}</h3>
      <p className="logic">{[p.condition && "IF " + p.condition, p.action && "THEN " + p.action, p.exception && "UNLESS " + p.exception].filter(Boolean).join(" ")}</p>
      <VerifyBadge check={p.verification} />
      <blockquote>{p.source_quote}</blockquote>
      {conflict.why && <p className="source-note">{conflict.why}</p>}
      {conflict.question && <p className="proposal-q"><b>{t("Ask the owner")}:</b> {conflict.question}</p>}
      <div className="actions"><button className="btn btn-ok" onClick={() => onAccept(conflict, p)}>✓ {t("Use the reconciled rule")}</button></div>
    </div>}
    <div className="conflict-pair">{pair.map(r => <div key={r.id} className="conflict-side">
      <span className="speaker-chip">{r.speaker || "Unknown speaker"}</span>
      <h3>{r.title}</h3><p className="logic">IF {r.condition} THEN {r.action}</p><blockquote>{r.source_quote}</blockquote>
      <SourceAudio evidence={evidence.find(e => e.id === r.evidence_id)} start={r.start} end={r.end} />
      <button className="btn btn-ok" onClick={() => onKeep(r.id, pair.find(o => o.id !== r.id).id)}>Keep {r.speaker ? r.speaker + "'s" : "this"} version</button>
    </div>)}</div>
    <button className="btn btn-ghost" onClick={onLater}>Decide later (keep both, list as open question)</button>
  </article>;
}
