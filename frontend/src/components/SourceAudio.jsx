import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import { audioStore } from "../api/storage.js";

export default function SourceAudio({ evidence, start, end, portal, caption }) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const player = useRef();
  useEffect(() => {
    let active = true, objectURL;
    setUrl(""); setError("");
    if (!evidence) return;
    (async () => {
      try {
        let blob;
        if (!portal) blob = await audioStore("get", evidence.localId || evidence.id).catch(() => null);
        if (!blob && (portal || evidence.key)) blob = await api.audio(evidence, portal);
        if (!blob) throw new Error("Original recording unavailable on this device.");
        if (active) { objectURL = URL.createObjectURL(blob); setUrl(objectURL); }
      } catch (e) { if (active) setError(e.message); }
    })();
    return () => { active = false; if (objectURL) URL.revokeObjectURL(objectURL); };
  }, [evidence?.id, evidence?.key, portal?.id, portal?.key]);
  if (!evidence) return <p className="source-note">Text source only — no original audio attached.</p>;
  return <div className="source-audio">
    <p>{caption || (start != null && end != null ? `Original clip · ${start}s–${end}s` : "Original recording · full segment")}{evidence.synthetic && <small className="synthetic-note"> · demo voice synthesised by Sarvam Bulbul, not a real person</small>}</p>
    {url && <audio ref={player} controls preload="metadata" src={url}
      onLoadedMetadata={() => { if (start != null) player.current.currentTime = start; }}
      onPlay={() => { const p = player.current; if (start != null && (p.currentTime < start || (end != null && p.currentTime >= end))) p.currentTime = start; }}
      onTimeUpdate={() => { if (end != null && player.current.currentTime >= end) player.current.pause(); }} />}
    {error && <p role="status">{error}</p>}
  </div>;
}
