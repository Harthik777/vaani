import { useEffect, useRef, useState } from "react";
import { api } from "./api/client.js";
import { audioStore } from "./api/storage.js";
import { LANGS, INTENT_MODES, MODE_DOMAIN } from "./data/mock.js";
import { MEETING, clipFor, speakerLine, speakerOf } from "./data/brd.js";
import { compileDocument, compileScreens } from "./data/compiler.js";
import { verifyRule } from "./data/verify.js";
import { requirementsApp } from "./data/requirementsApp.js";
import Wave from "./components/Wave.jsx";
import RuleCard from "./components/RuleCard.jsx";
import RuleEditor from "./components/RuleEditor.jsx";
import MetadataForm from "./components/MetadataForm.jsx";
import BrdView from "./components/BrdView.jsx";
import SourceAudio from "./components/SourceAudio.jsx";
import SharePanel from "./components/SharePanel.jsx";
import Portal from "./components/Portal.jsx";
import Interview from "./components/Interview.jsx";
import { ConflictCard, VerifierSummary } from "./components/Verifier.jsx";
import useRecorder from "./components/useRecorder.js";

const PHASES = ["landing", "record", "interview", "extract", "signoff", "brd"];
const PHASE_LABEL = { landing: "Start", record: "Speak", interview: "Agent questions", extract: "Review", signoff: "Approve", brd: "BRD + App" };
const STORAGE_KEY = "vaani_session";
// The landing page shows only the BRD flow. The three older document types stay reachable with ?modes=all.
const SHOW_ALL_MODES = typeof location !== "undefined" && new URLSearchParams(location.search).get("modes") === "all";
const YES_WORDS = ["हाँ", "हां", "हा ", "ठीक", "सही", "मंज़ूर", "मंजूर", "ಹೌದು", "ಸರಿ", "ಒಪ್ಪಿಗೆ", "ஆம்", "சரி", "అవును", "సరే", "হ্যাঁ", "ঠিক", "होय", "haan", "han ", "yes", "okay", "ok", "approve", "theek", "sahi", "howdu", "sari"];
const NO_WORDS = ["नहीं", "नही", "ना ", "गलत", "ಇಲ್ಲ", "ಬೇಡ", "இல்லை", "కాదు", "না", "নয়", "नाही", "नको", "nahi", "nahin", "illa", "no ", "no.", "skip", "reject", "wrong", "galat"];
const spokenDecision = text => {
  const t = " " + (text || "").toLowerCase().replace(/[।.,!?]/g, " ") + " ";
  const no = NO_WORDS.some(w => t.includes(w.toLowerCase())), yes = YES_WORDS.some(w => t.includes(w.toLowerCase()));
  return no ? "no" : yes ? "yes" : null;
};
const DEMO_OWNER = { kannada: "Spice wholesaler, K.R. Market, Bengaluru", hindi: "Spice wholesaler, Indore" };
const lineParts = line => { const m = line.match(/^\[([^\]]{1,60})\]\s*([\s\S]*)$/); return m ? { speaker: m[1], text: m[2] } : { speaker: null, text: line }; };
// Saaras v4 keyterms: names, products and units already known in this session bias speech recognition.
function keytermsFor(s) {
  const out = new Set();
  const add = v => { const t = String(v || "").trim(); if (t.length >= 2 && t.length <= 64) out.add(t); };
  ["title", "owner", "site"].forEach(k => { add(s.metadata[k]); String(s.metadata[k] || "").split(/[\s,/]+/).forEach(w => w.length >= 4 && add(w)); });
  add(s.domain); String(s.domain || "").split(/[\s,/]+/).forEach(w => w.length >= 4 && add(w));
  s.speakers.forEach(add);
  return [...out].slice(0, 50);
}
const fresh = (mode = "business", lang = "hindi", a11y = "standard", targetDevice = typeof window !== "undefined" && window.innerWidth <= 768 ? "mobile" : "desktop") => ({
  version: 3, phase: "landing", mode, lang, a11y, targetDevice, tx: "", rules: [], approved: [], soIdx: 0,
  evidence: [], metadata: {}, widgets: {}, demo: false, reviewNotes: [], published: null, domain: MODE_DOMAIN[mode],
  speakers: ["Owner"], speaker: "Owner", answers: [], skipped: [], gaps: null, draftAnswer: "", conflicts: [], rejected: [],
  extractBrain: null, ai: null, aiError: "", app: null, sarvamUsed: {}, docLang: "english", translations: null, voiceHeard: null,
});
function restore() {
  try {
    const value = JSON.parse(sessionStorage.getItem(STORAGE_KEY));
    if (value?.version !== 3 || !PHASES.includes(value.phase) || !MODE_DOMAIN[value.mode] || !LANGS.some(([c]) => c === value.lang)) return fresh();
    if (!Array.isArray(value.rules) || !Array.isArray(value.approved) || !Array.isArray(value.evidence) || typeof value.tx !== "string") return fresh();
    if (value.rules.some(r => !r || typeof r.id !== "string" || typeof r.action !== "string")) return fresh();
    const state = { ...fresh(), ...value };
    state.soIdx = Math.min(Math.max(0, state.soIdx || 0), Math.max(0, state.rules.length - 1));
    if (state.phase === "signoff" && !state.rules.length) state.phase = "extract";
    return state;
  } catch { return fresh(); }
}
export default function App() {
  const id = new URLSearchParams(location.search).get("portal");
  if (id) return <Portal id={id} accessKey={new URLSearchParams(location.hash.slice(1)).get("key") || ""} />;
  return <Workspace />;
}

function SarvamStrip({ health, used }) {
  const on = !!health?.live_stt;
  const sv = health?.sarvam || {};
  const ver = id => (id || "").replace(/^[a-z-]+:/, "");
  const chip = (key, label) => <span className={"sv-chip" + (used[key] ? " sv-used" : "")} title={used[key] ? "Used in this session" : on ? "Available" : "Not configured"}>{used[key] ? "●" : "○"} {label}</span>;
  return <div className="sarvam-strip" aria-label="Sarvam APIs">
    <span className="sv-brand">Powered by Sarvam</span>
    {chip("stt", "Saaras " + (on ? ver(sv.stt) + (sv.stt_mode ? " · " + sv.stt_mode : "") : "speech-to-text"))}
    {chip("translate", "Sarvam Translate")}
    {chip("tts", "Bulbul " + (on ? ver(sv.tts) : "voice"))}
    {on && sv.diarization && chip("diarization", "Speaker diarization (batch)")}
    {on && sv.doc_ai && chip("doc_ai", "Doc AI notes")}
    {on && sv.agent_llm && <span className="sv-chip sv-used">● Interview agent: {sv.agent_llm}</span>}
    {health && !on && <span className="sv-off">Sarvam key not configured</span>}
    {health?.live_llm && <span className="sv-brain">Drafting: {health.llm_model}</span>}
  </div>;
}

function Workspace() {
  const [s, set] = useState(restore), [error, setError] = useState(""), [busy, setBusy] = useState(false), [storageError, setStorageError] = useState("");
  const [health, setHealth] = useState(null), [aiBusy, setAiBusy] = useState(""), [uploading, setUploading] = useState("");
  const prefetched = useRef("");
  const heading = useRef(null), requestVersion = useRef(0), active = useRef(true), drafting = useRef(false);
  const patch = value => set(p => ({ ...p, ...value }));
  const invalidate = value => set(p => ({ ...p, ...value, approved: [], soIdx: 0, published: null, widgets: {}, ai: null, aiError: "", app: null, docLang: "english", translations: null }));
  const markUsed = flags => set(p => ({ ...p, sarvamUsed: { ...p.sarvamUsed, ...Object.fromEntries(Object.entries(flags).filter(([, v]) => v)) } }));
  const recorder = useRecorder({
    lang: s.lang, mode: s.mode, keyterms: keytermsFor(s),
    onEvidence: (item, oldId) => set(p => p.phase === "signoff" ? p : ({ ...p, demo: p.phase === "interview" ? p.demo : false, approved: [], published: null,
      evidence: oldId ? p.evidence.map(e => e.id === oldId ? { ...item, speaker: e.speaker } : e) : [...p.evidence, { ...item, speaker: p.speaker }] })),
    onTranscript: (text, item, timestamps) => set(p => p.phase === "signoff" ? { ...p, voiceHeard: { text, evidenceId: item.id, at: Date.now() }, sarvamUsed: { ...p.sarvamUsed, stt: true } } : ({
      ...p, tx: [p.tx, speakerLine(p.speaker, text)].filter(Boolean).join("\n"), demo: p.phase === "interview" ? p.demo : false,
      draftAnswer: p.phase === "interview" ? [p.draftAnswer, text].filter(Boolean).join(" ") : p.draftAnswer,
      evidence: p.evidence.map(e => e.id === item.id ? { ...e, transcript: text, timestamps } : e), sarvamUsed: { ...p.sarvamUsed, stt: true } })),
    onError: setError,
  });
  const locked = busy || recorder.requesting || recorder.recording || recorder.processing > 0;
  useEffect(() => { active.current = true; api.health().then(h => active.current && setHealth(h)).catch(() => setHealth(null)); return () => { active.current = false; requestVersion.current++; }; }, []);
  useEffect(() => {
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(s)); setStorageError(""); }
    catch { setStorageError("Session storage is unavailable or full. Keep this page open to preserve your progress."); }
  }, [s]);
  useEffect(() => {
    document.body.classList.remove("a11y-standard", "a11y-lowVision", "a11y-deaf");
    document.body.classList.add("a11y-" + s.a11y);
  }, [s.a11y]);
  useEffect(() => { heading.current?.focus(); }, [s.phase]);
  useEffect(() => {
    if (!locked) return;
    const handler = event => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [locked]);

  const langLabel = LANGS.find(([c]) => c === s.lang)?.[1];
  const index = PHASES.indexOf(s.phase);
  const approved = s.approved;
  const sarvamVoice = !!health?.live_stt;
  const currentRules = s.phase === "brd" ? approved : s.rules;
  const docInput = { rules: currentRules, mode: s.mode, metadata: { ...s.metadata, language: langLabel }, domain: s.domain, demo: s.demo,
    transcript: s.tx, answers: s.answers, ai: s.ai, coverage: s.gaps?.items || [], conflicts: s.conflicts };
  const brd = compileDocument(docInput);
  // Without the AI app: BRDs get the rule-driven requirement simulator, other modes their templates.
  const templateApp = s.mode === "business"
    ? requirementsApp(brd.project_name, brd.business_rules.map((r, i) => ({ ...currentRules[i], ...r })), brd.open_questions)
    : compileScreens(docInput).appHtml;
  const serverBody = { rules: approved, mode: s.mode, metadata: docInput.metadata, domain: s.domain, demo: s.demo, transcript: s.tx, answers: s.answers,
    sections: s.ai?.sections || null, acceptance: s.ai?.acceptance || [], coverage: s.gaps?.items || [], conflicts: s.conflicts,
    app_language: s.docLang, translations: s.translations || {} };
  const checks = s.rules.map(r => ({ ...verifyRule(r, s.tx), quote_note: r.quote_note || null }));
  const metadata = { ...s.metadata, mode: s.mode, ticketSummary: currentRules.map(r => r.action).join("\n") };

  // ── Agent: what does the BRD still need? ──
  const runGaps = async (tx, answered) => {
    setBusy(true); setError("");
    const version = ++requestVersion.current;
    try {
      const gaps = await api.gaps({ transcript: tx, mode: s.mode, lang: s.lang, answered, demo: s.demo });
      if (active.current && version === requestVersion.current) set(p => ({ ...p, gaps, sarvamUsed: { ...p.sarvamUsed, ...(gaps.translated_with_sarvam ? { translate: true } : {}) } }));
    } catch (e) { if (active.current && version === requestVersion.current) setError(e.message); }
    finally { if (active.current && version === requestVersion.current) setBusy(false); }
  };
  const startInterview = () => { setError(""); patch({ phase: "interview" }); runGaps(s.tx, s.answers.map(a => a.key)); };
  const saveAnswer = (question, text) => {
    const tx = s.tx.includes(text) ? s.tx : [s.tx, speakerLine(s.speaker, text)].filter(Boolean).join("\n");
    const answers = [...s.answers.filter(a => a.key !== question.key), { key: question.key, question: question.question, answer: text, speaker: s.speaker }];
    patch({ tx, answers, draftAnswer: "", skipped: s.skipped.filter(k => k !== question.key), ai: null, app: null, published: null });
    runGaps(tx, answers.map(a => a.key));
  };

  // ── Recorded meeting (Sarvam batch diarization) and notes photo (Sarvam Doc AI) as input ──
  const importMeeting = async file => {
    if (!file) return;
    setError(""); setUploading("Sarvam is transcribing the recording and separating speakers (about 10 seconds per minute of audio)…");
    try {
      const out = await api.meeting(file, s.lang, 2, keytermsFor(s));
      const evidence = { ...out.evidence, local: false, duration: out.lines.reduce((m, l) => Math.max(m, l.end || 0), 0) || undefined, speaker: null };
      invalidate({ tx: out.transcript, demo: false, rules: [], answers: [], skipped: [], gaps: null, conflicts: [], rejected: [],
        evidence: [evidence], speakers: out.speakers, speaker: out.speakers[0], sarvamUsed: { ...s.sarvamUsed, stt: true, diarization: true } });
    } catch (e) { setError(e.message); }
    finally { setUploading(""); }
  };
  const importNotes = async file => {
    if (!file) return;
    setError(""); setUploading("Sarvam Doc AI is reading the notes…");
    try {
      const out = await api.notes(file, s.lang);
      const speakers = s.speakers.includes("Notes") ? s.speakers : [...s.speakers, "Notes"];
      invalidate({ tx: [s.tx, out.transcript].filter(Boolean).join("\n"), demo: false, rules: [], gaps: null, speakers, sarvamUsed: { ...s.sarvamUsed, doc_ai: true } });
    } catch (e) { setError(e.message); }
    finally { setUploading(""); }
  };
  const renameSpeaker = (from, to) => {
    const name = to.trim().slice(0, 40);
    if (!name || name === from || s.speakers.includes(name)) return;
    const prefix = new RegExp("^\\[" + from.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\] ", "gm");
    invalidate({ tx: s.tx.replace(prefix, "[" + name + "] "), speakers: s.speakers.map(x => x === from ? name : x), speaker: s.speaker === from ? name : s.speaker,
      evidence: s.evidence.map(e => e.speaker === from ? { ...e, speaker: name } : e), rules: [], gaps: null });
  };

  // ── Extraction, verification, conflicts ──
  const extract = async () => {
    setError(""); setBusy(true); invalidate({ phase: "extract", rules: [], reviewNotes: [], rejected: [], conflicts: [] });
    const version = ++requestVersion.current;
    try {
      const result = await api.extract(s.tx, s.domain, s.mode, s.demo);
      if (!active.current || version !== requestVersion.current) return;
      const rules = result.rules.map(r => {
        const e = r.source_quote ? s.evidence.find(e => e.transcript?.includes(r.source_quote)) : null;
        return { ...r, quote_note: r.verification?.quote_note || null, speaker: r.speaker || speakerOf(r.source_quote, s.tx) || (e?.speaker ?? null), evidence_id: e?.id || null, ...clipFor(r.source_quote, e) };
      });
      patch({ rules, reviewNotes: result.review_notes || [], rejected: result.rejected || [], demo: result.demo, extractBrain: result.brain });
      if (new Set(rules.map(r => r.speaker).filter(Boolean)).size >= 2) {
        const found = await api.conflicts({ rules, transcript: s.tx, demo: result.demo }).catch(e => ({ conflicts: [], note: e.message }));
        if (active.current && version === requestVersion.current) patch({ conflicts: found.conflicts || [] });
      }
    } catch (e) { if (active.current && version === requestVersion.current) setError(e.message); }
    finally { if (active.current && version === requestVersion.current) setBusy(false); }
  };
  const updateRules = rules => invalidate({ rules });
  const validateRules = () => {
    const invalid = s.rules.find(r => !r.title.trim() || !r.condition.trim() || !r.action.trim() ||
      (r.source_quote && !s.tx.includes(r.source_quote)) ||
      ((r.start == null) !== (r.end == null)) || (r.start != null && (r.end <= r.start || r.start < 0)) ||
      (r.start != null && (!r.evidence_id || r.end > (s.evidence.find(e => e.id === r.evidence_id)?.duration || Infinity))));
    if (invalid) { setError(`Fix “${invalid.title || "untitled"}”: complete each field, copy the source text exactly, and use a valid clip range.`); return false; }
    return s.rules.length > 0;
  };
  const decide = (approve, spoken = null) => {
    if (!s.metadata.reviewer?.trim()) { setError("Enter the reviewer's name before recording a decision."); return; }
    setError("");
    const r = s.rules[s.soIdx];
    const next = approved.filter(a => a.id !== r.id);
    if (approve) next.push({ ...r, approved_at: new Date().toISOString(), approved_by: spoken ? `${s.metadata.reviewer} · by voice ("${spoken}")` : s.metadata.reviewer });
    patch({ approved: next, published: null, ai: null, app: null, aiError: "", docLang: "english", translations: null, voiceHeard: null, voiceNote: spoken ? `Heard "${spoken}" → ${approve ? "approved" : "skipped"}` : "", ...(s.soIdx + 1 >= s.rules.length ? { phase: "brd" } : { soIdx: s.soIdx + 1 }) });
  };
  // Spoken sign-off: "haan / ಹೌದು / yes" approves, "nahi / ಇಲ್ಲ / no" skips. Anything else asks again. Buttons always remain.
  const voiceTimer = useRef(null);
  const listenForDecision = () => {
    setError(""); patch({ voiceHeard: null, voiceNote: "" });
    recorder.start();
    clearTimeout(voiceTimer.current);
    voiceTimer.current = setTimeout(() => recorder.stop(), 4000);
  };
  useEffect(() => {
    if (s.phase !== "signoff" || !s.voiceHeard) return;
    const heard = s.voiceHeard.text.trim();
    const verdict = spokenDecision(heard);
    if (verdict === "yes") decide(true, heard);
    else if (verdict === "no") decide(false, heard);
    else patch({ voiceHeard: null, voiceNote: `Heard "${heard}". Say haan or nahi, or use the buttons.` });
  }, [s.voiceHeard]);

  // ── Final BRD: AI drafts the remaining sections (verified), then the app is generated from that BRD ──
  const generateApp = async (body = serverBody) => {
    setAiBusy("app");
    try { const app = await api.generateApp(body); if (active.current) patch({ app }); }
    catch (e) { if (active.current) patch({ app: { html: null, generator: "template", note: e.message } }); }
    finally { if (active.current) setAiBusy(""); }
  };
  const draftBrd = async () => {
    if (!approved.length || drafting.current) return;  // StrictMode/reloads must not start two drafts
    drafting.current = true;
    setAiBusy("draft"); patch({ aiError: "" });
    let ai = null;
    try { ai = await api.draftBrd(serverBody); if (active.current) patch({ ai }); }
    catch (e) { if (active.current) patch({ aiError: e.message }); }
    try { await generateApp({ ...serverBody, sections: ai?.sections || null, acceptance: ai?.acceptance || [] }); }
    finally { drafting.current = false; }
  };
  useEffect(() => {
    if (s.phase === "brd" && approved.length && !s.ai && !s.aiError && !s.app && !aiBusy) draftBrd();
  }, [s.phase, approved.length, !!s.ai, !!s.app, s.aiError]);
  // While the reviewer approves rule by rule, draft the BRD and the app for "all rules approved" in the background.
  // The server caches by request content, so if every rule is approved the real calls return instantly.
  useEffect(() => {
    if (s.phase !== "signoff" || !health?.live_llm || !s.rules.length) return;
    const key = s.rules.map(r => r.id + ":" + r.title + ":" + r.condition + ":" + r.action).join("|") + "|" + s.tx.length;
    if (prefetched.current === key) return;
    prefetched.current = key;
    const body = { ...serverBody, rules: s.rules.map(r => ({ ...r, approved_at: r.approved_at || new Date().toISOString(), approved_by: r.approved_by || s.metadata.reviewer || "Reviewer" })) };
    (async () => {
      try { const ai = await api.draftBrd(body); await api.generateApp({ ...body, sections: ai?.sections || null, acceptance: ai?.acceptance || [] }); }
      catch { /* best effort: the real request will simply not hit the cache */ }
    })();
  }, [s.phase, health?.live_llm]);

  const publish = async key => {
    setBusy(true); setError("");
    try {
      if (!approved.length) throw new Error("Approve at least one requirement before publishing.");
      const mapping = {}, evidence = [];
      for (const e of s.evidence) {
        if (!e.local) { evidence.push(e); continue; }
        const blob = await audioStore("get", e.localId || e.id);
        if (!blob) throw new Error("A source recording is missing. Return to review and remove its reference or re-record.");
        const remote = await api.upload(blob, e.captured_at);
        mapping[e.id] = remote.id;
        evidence.push({ ...e, ...remote, local: false });
      }
      const remap = r => ({ ...r, evidence_id: mapping[r.evidence_id] || r.evidence_id || null });
      const rules = approved.map(remap);
      patch({ evidence, rules: s.rules.map(remap), approved: rules });
      const published = await api.publish({ ...serverBody, rules, evidence, language: s.lang, app_html: s.app?.html || null, app_generator: s.app?.generator || "template" }, key);
      patch({ published });
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const reset = () => { requestVersion.current++; set(fresh(s.mode, s.lang, s.a11y, s.targetDevice)); setError(""); };
  const useMeetingDemo = () => {
    setError("");
    invalidate({ tx: MEETING.transcript[s.lang], demo: true, rules: [], evidence: [], answers: [], skipped: [], gaps: null, conflicts: [], rejected: [],
      speakers: [...MEETING.speakers], speaker: MEETING.speakers[0], domain: MEETING.domain,
      metadata: { title: "Demo · " + MEETING.title, owner: DEMO_OWNER[s.lang] || "Spice wholesaler, Indore", reviewer: "Demo reviewer" } });
  };
  const addSpeaker = name => { const v = name.trim().slice(0, 40); if (v && !s.speakers.includes(v)) patch({ speakers: [...s.speakers, v], speaker: v }); };
  const appLanguage = LANGS.find(([c]) => c === (s.app?.language || "english"))?.[1];
  const appLabel = (s.app?.generator?.startsWith("ai:") ? "AI-generated from your BRD" : s.mode === "business" ? "Requirement simulator (built from the BRD, no AI)" : "Template filled with your requirements") + " · " + appLanguage;
  const visibleConflicts = s.conflicts.filter(c => !c.deferred && c.rule_ids.every(id => s.rules.some(r => r.id === id)));
  const transcriptLines = s.tx.split("\n").filter(l => l.trim()).map(lineParts);

  return <main className="wrap">
    <header className="topbar">
      <div className="brand"><span className="logo">Vaani</span><span className="dev" lang="hi">वाणी</span><span className="tagline">Voice-first BRD agent</span></div>
      <nav aria-label="Workflow"><ol className="phase-list">{PHASES.map((p, i) => <li key={p} aria-current={s.phase === p ? "step" : undefined} className={i < index ? "done" : ""}><span className="step-n">{i + 1}</span><span className="step-l">{PHASE_LABEL[p]}</span></li>)}</ol></nav>
      <span className="lang-pill" title="Language">{langLabel}</span>
    </header>
    <SarvamStrip health={health} used={s.sarvamUsed} />
    {index > 0 && <button className="btn-back" disabled={locked} onClick={() => { setError(""); patch({ phase: PHASES[index - 1] }); }}>← Back</button>}
    <div ref={heading} tabIndex="-1" className="phase-focus" aria-label={"Step " + (index + 1)} />
    {error && <div className="notice error" role="alert">{error}</div>}
    {storageError && <div className="notice" role="status">{storageError}</div>}
    {busy && s.phase !== "interview" && <p role="status">Working…</p>}

    {s.phase === "landing" && <>
      <section className="hero">
        <div className="eyebrow">Voice-first BRD agent · built on Sarvam</div>
        <h1 className="big">Speak your requirements.<br /><span className="accent">Get a verified BRD</span> and a working app.</h1>
        <p className="lead">Explain what you need in your own language. Vaani's agent asks what you forgot, writes a Business Requirements Document where every requirement plays back in the speaker's own voice, and builds a first version of the app.</p>
        <ul className="hero-points">
          <li><b>Verbatim</b> Every requirement quotes the speaker exactly.</li>
          <li><b>Verified</b> A number nobody said is blocked, visibly.</li>
          <li><b>Voices</b> Owner and manager disagreements are caught, with both clips.</li>
        </ul>
      </section>
      {SHOW_ALL_MODES
        ? <fieldset className="choice-group"><legend>What are you capturing?</legend><div className="intent-grid">{INTENT_MODES.map(m => <button key={m.id} aria-pressed={s.mode === m.id} className={"intent-card" + (s.mode === m.id ? " on" : "")} onClick={() => { if (m.id !== s.mode) set(fresh(m.id, s.lang, s.a11y, s.targetDevice)); }}><span className="intent-icon">{m.icon}</span><span><strong>{m.title}</strong><span className="intent-desc">{m.desc}</span></span></button>)}</div></fieldset>
        : <p className="landing-mode"><span>Capturing: <b>{INTENT_MODES[0].title}</b></span><a href="?modes=all">Other document types</a></p>}
      <fieldset className="choice-group"><legend>Language</legend><div className="chips">{LANGS.map(([c, label]) => <button aria-pressed={s.lang === c} key={c} className={"chip" + (s.lang === c ? " on" : "")} onClick={() => { if (c !== s.lang) set(fresh(s.mode, c, s.a11y, s.targetDevice)); }}>{label}</button>)}</div></fieldset>
      <fieldset className="choice-group"><legend>Device / Output experience</legend><div className="modes">{[["desktop", "💻 Laptop / Desktop Webpage"], ["mobile", "📱 Mobile App"]].map(([c, label]) => <button aria-pressed={s.targetDevice === c} className={"mode" + (s.targetDevice === c ? " on" : "")} key={c} onClick={() => patch({ targetDevice: c })}>{label}</button>)}</div></fieldset>
      <fieldset className="choice-group"><legend>Accessibility</legend><div className="modes">{[["standard", "Standard"], ["lowVision", "Low vision"], ["deaf", "Deaf / HoH · type input"]].map(([c, label]) => <button aria-pressed={s.a11y === c} className={"mode" + (s.a11y === c ? " on" : "")} key={c} onClick={() => patch({ a11y: c })}>{label}</button>)}</div></fieldset>
      <button className="btn btn-primary btn-full" onClick={() => patch({ phase: "record" })}>Start capturing →</button>
    </>}

    {s.phase === "record" && <>
      <h1>Speak in {langLabel}</h1>
      <p className="lead">Describe the app or process you need, in your own words. If several people talk, pick who is speaking first, so every requirement carries a name and a voice.</p>
      <section className="card speak-stage" aria-label="Recording">
        <fieldset className="choice-group speakers"><legend>Who is speaking?</legend><div className="chips">
          {s.speakers.map(name => <button key={name} aria-pressed={s.speaker === name} className={"chip" + (s.speaker === name ? " on" : "")} disabled={recorder.recording} onClick={() => patch({ speaker: name })}>{name}</button>)}
          <form className="add-speaker" onSubmit={e => { e.preventDefault(); addSpeaker(e.currentTarget.speaker.value); e.currentTarget.reset(); }}><input name="speaker" aria-label="Add speaker" placeholder="Add speaker (e.g. Manager)" /><button className="btn btn-ghost">Add</button></form>
        </div></fieldset>
        <div className="import-row">
          <label className={"btn btn-ghost import-btn" + (locked || uploading ? " disabled" : "")}>📼 Upload a recorded meeting
            <input type="file" accept="audio/*,video/mp4,.m4a,.mp3,.wav,.ogg,.webm" disabled={locked || !!uploading} onChange={e => { importMeeting(e.target.files?.[0]); e.target.value = ""; }} /></label>
          <label className={"btn btn-ghost import-btn" + (locked || uploading ? " disabled" : "")}>📝 Photo or PDF of notes
            <input type="file" accept="image/*,application/pdf" disabled={locked || !!uploading} onChange={e => { importNotes(e.target.files?.[0]); e.target.value = ""; }} /></label>
          <span className="import-hint">Sarvam separates the speakers in a recording and reads handwritten notes.</span>
        </div>
        {uploading && <p role="status" className="agent-thinking">⏳ {uploading}</p>}
        {s.evidence.some(e => e.speaker === null) && s.speakers.some(n => /^Speaker \d+$/.test(n)) && <div className="rename-row">
          <span>Name the speakers:</span>
          {s.speakers.filter(n => /^Speaker \d+$/.test(n)).map(n => <form key={n} className="add-speaker" onSubmit={e => { e.preventDefault(); renameSpeaker(n, e.currentTarget.name_input.value); }}>
            <input name="name_input" aria-label={"Rename " + n} placeholder={n + " → e.g. Owner"} /><button className="btn btn-ghost">Rename</button></form>)}
        </div>}
        {s.a11y !== "deaf" && <div className="mic-row">
          <button className={"mic-btn" + (recorder.recording ? " on" : "")} aria-label={recorder.recording ? "Stop recording" : "Record microphone"}
            disabled={busy || (!recorder.recording && recorder.processing > 0)}
            onClick={recorder.recording ? recorder.stop : () => { invalidate({ rules: [], demo: false }); setError(""); recorder.start(); }}>
            <span aria-hidden="true">{recorder.recording ? "■" : "🎙"}</span></button>
          <div className="mic-status"><Wave active={recorder.recording} />
            <p role="status">{recorder.recording ? `Listening to ${s.speaker}… tap the button to stop` : recorder.processing ? "" : `Tap the microphone and speak as ${s.speaker}`}{recorder.processing ? "Sarvam Saaras is transcribing " + recorder.processing + " segment(s)…" : ""}</p>
            <p className="mic-hint">Numbers, names and exceptions are kept exactly as spoken. Every segment is hashed and kept as evidence.</p></div>
        </div>}
        {transcriptLines.length > 0 && <ol className="feed" aria-label="What was said">{transcriptLines.map((l, i) => <li key={i} className={"feed-line" + (l.speaker ? " spk-" + (Math.max(0, s.speakers.indexOf(l.speaker)) % 4) : "")}>
          {l.speaker && <span className="speaker-chip">{l.speaker}</span>}<span lang={s.lang === "english" ? "en" : undefined}>{l.text}</span></li>)}</ol>}
        <label htmlFor="transcript-input">Transcript</label><textarea id="transcript-input" className="transcript" value={s.tx} disabled={recorder.requesting || recorder.recording || recorder.processing > 0 || !!uploading} placeholder="Type or paste the speaker's words, or paste a WhatsApp chat export. Start a line with [Name] to mark who said it." onChange={e => invalidate({ tx: e.target.value, rules: [], demo: false, gaps: null })} />
      </section>
      <MetadataForm mode={s.mode} metadata={s.metadata} onChange={metadata => invalidate({ metadata })} />
      <div className="actions">
        {s.mode === "business" && MEETING.transcript[s.lang] && <button className="btn btn-ghost" disabled={locked} onClick={useMeetingDemo}>Use 2-speaker meeting demo</button>}
        <button className="btn btn-ghost" disabled={locked} onClick={() => { setError(""); invalidate({ tx: api.demoTranscript(s.lang, s.mode), demo: true, rules: [], evidence: [], answers: [], gaps: null, domain: MODE_DOMAIN[s.mode], metadata: { title: "Demo · " + INTENT_MODES.find(m => m.id === s.mode).title, reviewer: "Demo reviewer" } }); }}>Use demo</button>
        <button className="btn btn-primary" disabled={!s.tx.trim() || locked} onClick={startInterview}>Next: agent checks for gaps →</button>
        <button className="btn btn-ghost" disabled={!s.tx.trim() || locked} onClick={() => patch({ phase: "extract" })}>Enter rules manually</button></div>
      {s.demo && <p className="demo-banner">Sample transcript selected. No original speaker audio is supplied.</p>}
      {s.evidence.map(e => <SourceAudio key={e.id} evidence={e} caption={(e.speaker ? e.speaker + " · " : "") + "Original recording · full segment"} />)}
    </>}

    {s.phase === "interview" && <>
      <h1>The agent's questions</h1><p>A complete BRD needs 8 things. The agent shows what was already said (with the exact words) and asks only for what is missing.</p>
      <Interview gaps={s.gaps} busy={busy} lang={s.lang} langLabel={langLabel} a11y={s.a11y} sarvamVoice={sarvamVoice} recorder={recorder} demo={s.demo}
        draft={s.draftAnswer} onDraft={draftAnswer => patch({ draftAnswer })} skipped={s.skipped} onSave={saveAnswer}
        onSkip={key => patch({ skipped: [...new Set([...s.skipped, key])], draftAnswer: "" })} onRetry={() => runGaps(s.tx, s.answers.map(a => a.key))}
        onContinue={extract} onVoiceUsed={translated => markUsed({ tts: true, translate: translated })} />
    </>}

    {s.phase === "extract" && <>
      <h1>Review extracted requirements</h1><p>Each requirement must quote the speaker exactly. Fix or remove anything the verifier flags.</p>
      {visibleConflicts.map(c => <ConflictCard key={c.rule_ids.join("-")} conflict={c} rules={s.rules} evidence={s.evidence}
        onKeep={(keep, drop) => updateRules(s.rules.filter(r => r.id !== drop))}
        onLater={() => patch({ conflicts: s.conflicts.map(x => x === c ? { ...x, deferred: true } : x) })} />)}
      <VerifierSummary rules={s.rules} checks={checks} rejected={s.rejected} brain={s.extractBrain} />
      {!!s.reviewNotes.length && <aside className="notice"><h2>Review notes</h2><ul>{s.reviewNotes.map((n, i) => <li key={i}>{n}</li>)}</ul></aside>}
      {s.rules.map((r, i) => <RuleEditor key={r.id} rule={r} check={checks[i]} evidence={s.evidence} onChange={next => updateRules(s.rules.map(v => v.id === r.id ? next : v))} onDelete={() => updateRules(s.rules.filter(v => v.id !== r.id))} />)}
      <div className="actions"><button className="btn btn-ghost" disabled={busy} onClick={() => updateRules([...s.rules, { id: crypto.randomUUID(), title: "", condition: "", action: "", exception: null, confidence: "MEDIUM", type: "requirement", source_quote: "", numbers: [], speaker: s.speaker, evidence_id: null, start: null, end: null }])}>Add requirement</button>
        <button className="btn btn-primary" disabled={busy || !s.rules.length} onClick={() => { if (validateRules()) { setError(""); patch({ phase: "signoff" }); } }}>Review and approve →</button></div>
    </>}

    {s.phase === "signoff" && s.rules[s.soIdx] && <><h1>Source-backed sign-off</h1><p>Requirement {s.soIdx + 1} of {s.rules.length}. Listen to the original voice, hear it read back in your language, then decide.</p><progress aria-label="Review progress" max={s.rules.length} value={s.soIdx} />
      <label>Reviewer name<input value={s.metadata.reviewer || ""} onChange={e => patch({ metadata: { ...s.metadata, reviewer: e.target.value }, published: null })} /></label>
      <RuleCard r={s.rules[s.soIdx]} check={checks[s.soIdx]} lang={s.lang} evidence={s.evidence} a11y={s.a11y} sarvamVoice={sarvamVoice} onSarvamUsed={markUsed} />
      <p className="source-note">Approval records your review decision and time. It is not an electronic signature or proof of speaker identity. After the last requirement you get the full BRD, with PDF, Word, Markdown and Jira downloads.</p>
      <div className="actions"><button className="btn btn-ok" onClick={() => decide(true)}>{["needs_confirmation", "unsupported_number"].includes(checks[s.soIdx]?.status) ? "Approve: I confirm the numbers" : "Approve requirement"}</button><button className="btn btn-ghost" onClick={() => decide(false)}>Skip requirement</button>
        {s.a11y !== "deaf" && <button className={"btn " + (recorder.recording ? "btn-rec" : "btn-ghost")} disabled={!recorder.recording && recorder.processing > 0} onClick={recorder.recording ? recorder.stop : listenForDecision}>
          🎙 {recorder.recording ? "Listening… say haan or nahi" : recorder.processing ? "Sarvam is listening…" : "Say haan or nahi to decide"}</button>}
        {s.voiceNote && <span role="status" className="source-note">{s.voiceNote}</span>}</div></>}

    {s.phase === "brd" && <BrdView brd={brd} appHtml={s.app?.html || templateApp} appLabel={s.app ? appLabel : "Template preview (AI app not generated yet)"} appNote={s.app?.note}
      evidence={s.evidence} langs={LANGS} lang={s.lang} reset={reset} widgets={s.widgets} onWidgets={widgets => patch({ widgets })} metadata={metadata}
      ai={{ busy: aiBusy, error: s.aiError, stats: s.ai?.stats }} onRedraft={() => { patch({ ai: null, aiError: "", app: null, docLang: "english", translations: null }); }} onRegenerateApp={() => generateApp()}
      docLang={s.docLang} translations={s.translations} onLanguage={(docLang, translations) => { patch({ docLang, translations }); generateApp({ ...serverBody, app_language: docLang, translations: translations || {} }); }}
      serverBody={serverBody} sarvamVoice={sarvamVoice} onSarvamUsed={markUsed} completeness={s.gaps?.completeness} a11y={s.a11y}
      shareUrl={s.published?.preview_url || s.published?.url} share={<SharePanel published={s.published} onPublish={publish} busy={busy} mode={s.mode} />} targetDevice={s.targetDevice} />}
  </main>;
}
