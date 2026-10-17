import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import { audioStore } from "../api/storage.js";

// Each 25s segment has its own container header; arbitrary MediaRecorder chunks
// are not sent as if they were independently decodable audio files.
export default function useRecorder({ lang, mode, keyterms = [], onEvidence, onTranscript, onError }) {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(0);
  const [requesting, setRequesting] = useState(false);
  const recorder = useRef(null), stream = useRef(null), timer = useRef(null);
  const running = useRef(false), alive = useRef(true), queue = useRef(Promise.resolve());
  const callbacks = useRef({ onEvidence, onTranscript, onError, keyterms });
  callbacks.current = { onEvidence, onTranscript, onError, keyterms };
  const enqueue = (blob, capturedAt, duration, language, intent) => {
    setProcessing(n => n + 1);
    queue.current = queue.current.then(async () => {
      const id = crypto.randomUUID();
      const bytes = await blob.arrayBuffer();
      const sha256 = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(v => v.toString(16).padStart(2, "0")).join("");
      await audioStore("put", id, blob);
      let item = { id, localId: id, captured_at: capturedAt, duration, sha256, local: true };
      if (alive.current) callbacks.current.onEvidence(item);
      try {
        const remote = await api.upload(blob, capturedAt);
        item = { ...item, ...remote, local: false };
        if (alive.current) callbacks.current.onEvidence(item, id);
        const result = await api.transcribe(blob, language, intent, callbacks.current.keyterms || []);
        if (alive.current) callbacks.current.onTranscript(result.transcript, item, result.timestamps);
      } catch (e) { if (alive.current) callbacks.current.onError(e.message); }
    }).catch(e => { if (alive.current) callbacks.current.onError("Could not preserve audio: " + e.message); })
      .finally(() => { if (alive.current) setProcessing(n => n - 1); });
  };
  const segment = (language, intent) => {
    const mimeType = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"].find(t => MediaRecorder.isTypeSupported(t));
    const r = new MediaRecorder(stream.current, mimeType ? { mimeType } : undefined);
    recorder.current = r;
    const chunks = [], began = Date.now(), capturedAt = new Date().toISOString();
    r.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    r.onerror = () => { stop(); callbacks.current.onError("Recording failed. Existing segments are preserved."); };
    r.onstop = () => {
      clearTimeout(timer.current);
      const blob = new Blob(chunks, { type: r.mimeType || "audio/webm" });
      if (blob.size && alive.current) enqueue(blob, capturedAt, (Date.now() - began) / 1000, language, intent);
      if (running.current && alive.current) segment(language, intent);
      else { stream.current?.getTracks().forEach(t => t.stop()); stream.current = null; }
    };
    r.start();
    timer.current = setTimeout(() => { if (r.state === "recording") r.stop(); }, 25000);
  };
  const start = async () => {
    if (running.current || recording) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      callbacks.current.onError("Microphone capture requires a supported browser on HTTPS or localhost. You can type or use the demo."); return;
    }
    running.current = true; setRequesting(true);
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!running.current || !alive.current) { media.getTracks().forEach(t => t.stop()); return; }
      stream.current = media; setRecording(true); segment(lang, mode);
    } catch (e) { running.current = false; setRecording(false); callbacks.current.onError("Microphone unavailable: " + e.message + ". Type your transcript or use the demo."); }
    finally { if (alive.current) setRequesting(false); }
  };
  const stop = () => {
    running.current = false; setRecording(false); clearTimeout(timer.current);
    if (recorder.current?.state === "recording") recorder.current.stop();
    else stream.current?.getTracks().forEach(t => t.stop());
  };
  useEffect(() => { alive.current = true; return () => { alive.current = false; running.current = false; clearTimeout(timer.current); if (recorder.current?.state === "recording") recorder.current.stop(); stream.current?.getTracks().forEach(t => t.stop()); }; }, []);
  return { start, stop, recording, processing, requesting };
}
