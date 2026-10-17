import { FALLBACK_RULES, DEMO_TRANSCRIPT } from "../data/mock.js";
import { CHECKLIST, MEETING, meetingLanguage } from "../data/brd.js";
import { verifyRule } from "../data/verify.js";
export const BASE = import.meta.env?.VITE_API_BASE || "http://localhost:8000";
const OFFLINE = "Backend unavailable. Start the API to use recording transcription, publishing or tickets.";

async function request(path, { body, key, method = "GET", binary = false, timeout = 65000 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const headers = {};
    if (key) headers.Authorization = "Bearer " + key;
    const form = body instanceof FormData;
    if (body && !form) headers["Content-Type"] = "application/json";
    const r = await fetch(BASE + path, { method, headers, body: body ? (form ? body : JSON.stringify(body)) : undefined, signal: controller.signal });
    if (!r.ok) {
      const problem = await r.json().catch(() => ({}));
      const error = new Error(typeof problem.detail === "string" ? problem.detail : "Request failed (" + r.status + ")");
      error.status = r.status;
      throw error;
    }
    return binary ? r.blob() : r.json();
  } catch (e) {
    if (e.name === "AbortError") throw new Error("Request timed out. Your work is preserved; retry.");
    if (e instanceof TypeError) { const error = new Error(OFFLINE); error.offline = true; throw error; }
    throw e;
  } finally { clearTimeout(timer); }
}
const post = (path, body, options = {}) => request(path, { ...options, method: "POST", body });

// Demo fixtures, used only when the backend is not running (mirrors backend/routes/extract.py and services/agent.py).
function localDemoRules(transcript, mode) {
  const meeting = meetingLanguage(transcript);
  if (meeting && mode === "business") return { rules: structuredClone(MEETING.rules[meeting]), review_notes: [...MEETING.review_notes] };
  const base = Object.values(DEMO_TRANSCRIPT[mode]).find(t => transcript === t || transcript.startsWith(t + "\n"));
  if (!base) return null;
  const result = structuredClone(FALLBACK_RULES[mode]);
  return { ...result, rules: result.rules.map(r => ({ ...r, source_quote: base })) };
}
function localDemoGaps(transcript, answered) {
  const meeting = meetingLanguage(transcript), covered = meeting ? MEETING.coverage[meeting] : {};
  const items = CHECKLIST.map(c => ({ key: c.key, label: c.label, status: answered.includes(c.key) ? "answered" : covered[c.key] ? "covered" : "missing", source_quote: answered.includes(c.key) ? null : covered[c.key] || null }));
  const done = items.filter(i => i.status !== "missing").length;
  return { items, questions: CHECKLIST.filter(c => items.find(i => i.key === c.key).status === "missing").map(c => ({ key: c.key, label: c.label, question: c.question, question_local: null })),
    completeness: Math.round(100 * done / CHECKLIST.length), brain: meeting ? "demo fixture (offline)" : "checklist only (offline)", ai_checked: !!meeting,
    translated_with_sarvam: false, sample_answers: meeting ? MEETING.sample_answers[meeting] : {} };
}

export const api = {
  health: () => request("/api/health", { timeout: 5000 }),
  async extract(transcript, domain, mode, demo) {
    try {
      return await post("/api/extract", { transcript, domain, mode, demo });
    } catch (e) {
      const local = demo && e.offline ? localDemoRules(transcript, mode) : null;
      if (!local) throw e;
      return { ...local, rules: local.rules.map(r => ({ ...r, evidence_id: null, verification: verifyRule(r, transcript) })), rejected: [], demo: true, brain: "demo fixture (offline)" };
    }
  },
  async gaps(body) {
    try { return await post("/api/agent/gaps", body, { timeout: 90000 }); }
    catch (e) { if (e.offline) return localDemoGaps(body.transcript, body.answered); throw e; }
  },
  async conflicts(body) {
    try { return await post("/api/agent/conflicts", body, { timeout: 90000 }); }
    catch (e) {
      if (e.offline && body.demo && meetingLanguage(body.transcript)) {
        const ids = new Set(body.rules.map(r => r.id));
        return { conflicts: MEETING.conflicts.filter(c => c.rule_ids.every(id => ids.has(id))), brain: "demo fixture (offline)" };
      }
      throw e;
    }
  },
  draftBrd: body => post("/api/brd/draft", body, { timeout: 150000 }),
  generateApp: body => post("/api/app/generate", body, { timeout: 150000 }),
  docx: body => request("/api/brd/docx", { method: "POST", body, binary: true }),
  tts: body => post("/api/tts", body, { timeout: 60000 }),
  translate: body => post("/api/translate", body, { timeout: 120000 }),
  async transcribe(blob, lang, mode, keyterms = []) {
    const body = new FormData();
    body.append("audio", blob, blob.type.includes("mp4") ? "recording.mp4" : "recording.webm");
    body.append("lang", lang); body.append("mode", mode);
    // Saaras v4 keyterms: product names, units and brands from this session bias recognition (max 50).
    if (keyterms.length) body.append("keyterms", JSON.stringify(keyterms.slice(0, 50)));
    return post("/api/stt", body);
  },
  // Recorded meeting (call recording, WhatsApp voice note) -> Sarvam batch STT with speaker diarization.
  async meeting(file, lang, numSpeakers = 2, keyterms = []) {
    const body = new FormData();
    body.append("audio", file, file.name || "meeting.wav");
    body.append("lang", lang); body.append("num_speakers", String(numSpeakers)); body.append("captured_at", new Date().toISOString());
    if (keyterms.length) body.append("keyterms", JSON.stringify(keyterms.slice(0, 50)));
    return post("/api/stt/meeting", body, { timeout: 620000 });
  },
  // Photo or PDF of notes -> Sarvam Doc AI -> "[Notes] ..." lines.
  async notes(file, lang) {
    const body = new FormData();
    body.append("file", file, file.name || "notes.png"); body.append("lang", lang);
    return post("/api/notes", body, { timeout: 200000 });
  },
  async upload(blob, capturedAt) {
    const body = new FormData();
    body.append("audio", blob, "recording"); body.append("captured_at", capturedAt);
    return post("/api/evidence", body, { timeout: 15000 });
  },
  audio(evidence, portal) {
    return portal ? request("/api/portals/" + portal.id + "/audio/" + evidence.id, { key: portal.key, binary: true })
      : request("/api/evidence/" + evidence.id, { key: evidence.key, binary: true });
  },
  publish: (body, key) => post("/api/portals", body, { key }),
  transliterate: body => post("/api/transliterate", body, { timeout: 60000 }),
  qrUrl: (data, size = 6) => BASE + "/api/qr.png?size=" + size + "&data=" + encodeURIComponent(data),
  portal: (id, key) => request("/api/portals/" + id, { key }),
  ticket: body => post("/api/tickets", body),
  upiLink: body => post("/api/upi/link", body),
  demoTranscript: (lang, mode) => DEMO_TRANSCRIPT[mode][lang],
};

// Plays Sarvam Bulbul clips (base64 WAV) one after another. Returns a stop function.
export function playClips(audios, onEnd) {
  let index = 0, stopped = false, current = null;
  const next = () => {
    if (stopped || index >= audios.length) { if (!stopped) onEnd?.(); return; }
    current = new Audio("data:audio/wav;base64," + audios[index++]);
    current.onended = next;
    current.onerror = next;
    current.play().catch(() => { stopped = true; onEnd?.(new Error("Playback was blocked by the browser. Click again.")); });
  };
  next();
  return () => { stopped = true; current?.pause(); };
}

// Browser voice, used only when Sarvam is not configured. Labelled as such in the UI.
export function speak(text, lang) {
  if (!("speechSynthesis" in window)) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = { hindi:"hi-IN", marathi:"mr-IN", tamil:"ta-IN", telugu:"te-IN", bengali:"bn-IN", kannada:"kn-IN", english:"en-IN" }[lang] || "en-IN";
  speechSynthesis.cancel(); speechSynthesis.speak(u);
}
