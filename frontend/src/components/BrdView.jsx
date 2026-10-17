import { useRef, useState } from "react";
import { api, playClips } from "../api/client.js";
import { toJiraCsv, toMarkdown, download, fileName } from "../data/export.js";
import PhoneFrame, { openSandboxed } from "./PhoneFrame.jsx";
import SourceAudio from "./SourceAudio.jsx";
import { VerifyBadge } from "./Verifier.jsx";

const ORIGIN = { spoken: ["🗣️", "Spoken"], suggested: ["💡", "AI suggestion: confirm"] };
const Tr = ({ text, translations }) => translations?.[text] ? <span className="tr" lang="mul">{translations[text]}</span> : null;

export function Document({ brd, evidence = [], portal, translations }) {
  let n = 0;
  return <article className="brd-doc">
    <header className="doc-head"><div className="eyebrow">{brd.document_type}</div><h2>{brd.project_name}</h2><p className="source-note">{brd.status}</p>
      {brd.demo && <p className="demo-banner">DEMONSTRATION: sample content, not a client's signed requirements.</p>}</header>
    {Object.entries(brd.metadata || {}).some(([k, v]) => v && !["ticketSummary", "review_notes"].includes(k)) && <dl className="metadata">
      {Object.entries(brd.metadata).filter(([k, v]) => v && !["ticketSummary", "review_notes"].includes(k)).map(([k, v]) => <div key={k}><dt>{k.replaceAll("_", " ")}</dt><dd>{v}</dd></div>)}
    </dl>}

    {Object.entries(brd.sections || {}).map(([key, items]) => <section className="brd-sec" key={key}>
      <h3>{++n}. {brd.section_titles?.[key] || key}</h3>
      {items.length ? <ul className="doc-items">{items.map((item, i) => <li key={i} className={"origin-" + item.origin}>
        <span>{item.text}</span> <span className="origin-tag" title={item.origin === "suggested" ? "Not said by anyone. The AI suggests it; confirm or remove." : "Backed by the exact words below."}>{ORIGIN[item.origin]?.[0]} {ORIGIN[item.origin]?.[1] || item.origin}</span>
        <Tr text={item.text} translations={translations} />
        {item.source_quote && item.source_quote !== item.text.replace(/^[^:]+: /, "") && <q className="item-quote">{item.source_quote}</q>}
      </li>)}</ul> : <p className="empty">Not captured yet.</p>}
    </section>)}

    <section className="brd-sec">
      <h3>{++n}. Functional requirements and traceability</h3>
      <p className="source-note">Each requirement links to the exact words and the original audio of the person who said it.</p>
      {brd.business_rules.length ? brd.business_rules.map(r => <article className="document-rule" key={r.id}>
        <div className="fr-head"><span className="fr-id">{r.req_id}</span><h4>{r.title}</h4>{r.speaker && <span className="speaker-chip">{r.speaker}</span>}</div>
        <p className="logic">{r.rule}</p><Tr text={r.rule} translations={translations} />
        <VerifyBadge check={r.verification} />
        {!!r.acceptance?.length && <div className="acceptance"><b>Acceptance criteria</b><ul>{r.acceptance.map((a, i) => <li key={i}>{a}</li>)}</ul></div>}
        <blockquote>{r.source_quote || "No source quote"}</blockquote>
        <SourceAudio evidence={evidence.find(e => e.id === r.evidence_id)} start={r.start} end={r.end} portal={portal}
          caption={r.start != null ? `🔊 Hear ${r.speaker || "the speaker"} say it · ${r.start}s–${r.end}s` : undefined} />
        <p className="source-note">Approved by {r.approved_by || "pending"}{r.approved_at ? " · " + new Date(r.approved_at).toLocaleString() : ""}</p>
      </article>) : <p className="empty">No approved requirements.</p>}
    </section>

    <section className="brd-sec"><h3>{++n}. Open questions</h3>
      {brd.open_questions?.length ? <ul>{brd.open_questions.map((q, i) => <li key={i}>{q}<Tr text={q} translations={translations} /></li>)}</ul> : <p>None.</p>}</section>

    {!!brd.rejected?.length && <section className="brd-sec verification-report"><h3>{++n}. Verification report: blocked AI content</h3>
      <p className="source-note">The AI drafted these, but the verifier blocked them because they could not be traced to what was said.</p>
      <ul className="rejected-list">{brd.rejected.map((r, i) => <li key={i}><s>{r.text}</s> <span className="reason">{r.reason}</span></li>)}</ul></section>}

    <section className="brd-sec"><h3>{++n}. Evidence register</h3>{evidence.length ? evidence.map(e => <div className="evidence-row" key={e.id}>
      <p>Recording {e.id}{e.speaker ? " · " + e.speaker : ""} · Captured {e.captured_at}</p><p>SHA-256: <code>{e.sha256}</code></p>
    </div>) : <p>Text-only input. No original voice recording is attached.</p>}
      <p className="source-note">Hashes show the recording was not altered. They do not prove speaker identity or replace signatures.</p></section>
    <section className="brd-sec"><h3>{++n}. Sign-off</h3><p>{brd.authorization}</p></section>
  </article>;
}

function summaryText(brd) {
  const items = key => (brd.sections?.[key] || []).map(i => i.text);
  return [brd.project_name + ".", ...items("executive_summary"), ...items("objectives"),
    `This document has ${brd.business_rules.length} requirements.`, ...brd.business_rules.map(r => `${r.title}: ${r.rule.replace(/^IF /, "If ").replace(" THEN ", ", then ").replace(" UNLESS ", ", unless ")}.`),
    brd.open_questions?.length ? `${brd.open_questions.length} questions are still open.` : ""].filter(Boolean).join(" ");
}

export default function BrdView({ brd, appHtml, appLabel, appNote, evidence, langs, lang, reset, widgets, onWidgets, metadata, share, shareUrl, targetDevice,
  ai, onRedraft, onRegenerateApp, serverBody, sarvamVoice, onSarvamUsed, completeness, a11y, docLang, translations, onLanguage }) {
  const [listenLang, setListenLang] = useState(lang);
  const [status, setStatus] = useState(""), [busy, setBusy] = useState("");
  const stop = useRef(null);
  const listenLabel = langs.find(([c]) => c === listenLang)?.[1];

  const listen = async () => {
    stop.current?.(); setBusy("listen"); setStatus("");
    try {
      const result = await api.tts({ text: summaryText(brd), lang: listenLang, translate: listenLang !== "english" });
      onSarvamUsed({ tts: true, translate: result.translated });
      setStatus(`Playing in ${listenLabel} (Sarvam Bulbul${result.translated ? " + Sarvam Translate" : ""}).`);
      stop.current = playClips(result.audios, error => { setBusy(""); if (error) setStatus(error.message); });
    } catch (e) { setBusy(""); setStatus(e.message); }
  };
  const docLabel = langs.find(([c]) => c === docLang)?.[1] || "English";
  // One switch for both: the BRD gets Sarvam translations under each English line, and the app is rebuilt in that language.
  const switchLanguage = async () => {
    if (listenLang === "english") { onLanguage("english", null); setStatus("BRD and app switched back to English."); return; }
    setBusy("translate"); setStatus("");
    const texts = [...new Set([...Object.values(brd.sections || {}).flat().map(i => i.text), ...brd.business_rules.map(r => r.rule), ...(brd.open_questions || [])])];
    try {
      const map = {};
      for (let i = 0; i < texts.length; i += 40) {
        const batch = texts.slice(i, i + 40);
        const { translations: out } = await api.translate({ texts: batch, target: listenLang });
        batch.forEach((t, j) => { map[t] = out[j]; });
      }
      onLanguage(listenLang, map); onSarvamUsed({ translate: true });
      setStatus(`BRD shown in ${listenLabel} (${texts.length} lines, Sarvam Translate; English stays the reference). The app is being rebuilt in ${listenLabel}.`);
    } catch (e) { setStatus(e.message); } finally { setBusy(""); }
  };
  const word = async () => {
    setBusy("docx"); setStatus("");
    try { download(fileName(brd) + ".docx", await api.docx(serverBody)); } catch (e) { setStatus(e.message); } finally { setBusy(""); }
  };

  return <div className="brd-final">
    <header className="brd-header"><div><div className="eyebrow">Business Requirements Document + generated web app</div><h1>{brd.project_name}</h1>
      <p>{brd.business_rules.length} approved requirements · BRD completeness {completeness ?? "n/a"}%{brd.ai_brain ? " · drafted by " + brd.ai_brain : ""}</p></div>
      <button className="btn btn-ghost" onClick={reset}>Start over</button></header>

    <section className="download-bar card" aria-label="Download BRD">
      <div><h2>⬇ Download BRD</h2><p className="source-note">{docLang === "english" ? "English." : `English with the ${docLabel} translation under each line (PDF, Word, Markdown).`} Jira CSV is always English, for the vendor.</p></div>
      <div className="brd-actions">
        <button className="btn btn-pdf" onClick={() => window.print()}>PDF</button>
        <button className="btn btn-primary" disabled={busy === "docx"} onClick={word}>{busy === "docx" ? "Preparing…" : "Word (.docx)"}</button>
        <button className="btn btn-ghost" onClick={() => download(fileName(brd) + (docLang === "english" ? "" : "-" + docLang) + ".md", toMarkdown(brd, translations), "text/markdown;charset=utf-8")}>Markdown</button>
        <button className="btn btn-ghost" onClick={() => download(fileName(brd) + "-jira.csv", "\ufeff" + toJiraCsv(brd), "text/csv;charset=utf-8")}>Jira CSV</button>
      </div>
    </section>

    <div className={"ai-bar" + (ai.error ? " ai-error" : "")} role="status">
      {ai.busy === "draft" && <span>🧠 The agent is drafting the remaining BRD sections. The verifier will check every line…</span>}
      {ai.busy === "app" && <span>🛠️ Generating the web app from the approved BRD…</span>}
      {!ai.busy && ai.stats && <span>🧠 AI drafted {ai.stats.kept} items · 🚫 {ai.stats.rejected} blocked by the verifier · {ai.stats.acceptance} acceptance criteria</span>}
      {!ai.busy && ai.error && <span>{ai.error}</span>}
      {!ai.busy && <button className="btn-link" onClick={onRedraft}>{ai.stats ? "Redraft" : "Draft sections with AI"}</button>}
    </div>

    <div className="listen-bar card">
      <label>Language<select value={listenLang} onChange={e => setListenLang(e.target.value)}>{langs.map(([c, label]) => <option key={c} value={c}>{label}</option>)}</select></label>
      <button className="btn btn-primary" disabled={(!sarvamVoice && listenLang !== "english") || listenLang === docLang || busy === "translate" || !!ai.busy} onClick={switchLanguage}>
        🌐 {busy === "translate" ? "Translating…" : listenLang === docLang ? `BRD + app in ${docLabel}` : `Switch BRD + app to ${listenLabel}`}</button>
      {a11y !== "deaf" && <button className="btn btn-ghost" disabled={!sarvamVoice || busy === "listen"} onClick={listen}>🔊 {busy === "listen" ? "Playing…" : "Listen to BRD summary"}</button>}
      {busy === "listen" && <button className="btn btn-ghost" onClick={() => { stop.current?.(); setBusy(""); }}>Stop</button>}
      {!sarvamVoice && <span className="source-note">Sarvam is not configured, so voice and translation are unavailable.</span>}
      {status && <span className="source-note">{status}</span>}
    </div>

    <div className="brd-dual">
      <div className="brd-doc-column"><Document brd={brd} evidence={evidence} translations={translations} /></div>
      <aside className="brd-app-col">
        <div className="brd-app-header-row"><h2>💻 Web app generated from this BRD</h2>
          <button className="btn-app-tab" onClick={() => openSandboxed(appHtml)}>Open full page ↗</button></div>
        {appNote && <p className="notice">{appNote}</p>}
        <button className="btn-link" disabled={!!ai.busy} onClick={onRegenerateApp}>↻ Regenerate app</button>
        <PhoneFrame screens={[]} appHtml={appHtml} appLabel={appLabel} evidence={evidence} widgets={widgets} onWidgets={onWidgets} metadata={{ ...metadata, mode: brd.mode }} shareUrl={shareUrl} previewOnly={true} targetDevice={targetDevice} />
        {share}
      </aside>
    </div>
  </div>;
}
