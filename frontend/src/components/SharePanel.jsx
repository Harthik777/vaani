import { useState } from "react";
export default function SharePanel({ published, onPublish, busy, mode }) {
  const [message, setMessage] = useState("");
  const url = published?.preview_url || published?.url;
  return <section className="card share-panel"><h3>Shareable Web Portal</h3>
    <p>{mode === "awareness" ? "Publish a public web portal with your approved rules and recordings for community distribution." : "Publish a private web portal accessible to authorized parties with this session's access key."}</p>
    <button className="btn btn-primary" disabled={busy || !!published} onClick={() => onPublish("")}>{published ? "✓ Version published" : "Publish reviewed version"}</button>
    {published && <><label>Shareable URL<input readOnly value={url} onFocus={e => e.target.select()} /></label>
      <a className="portal-direct-link" href={published.url} target="_blank" rel="noreferrer">Open responsive portal ↗</a>
      <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
        <button className="btn btn-ghost" style={{ flex: 1 }} onClick={async () => { try { await navigator.clipboard.writeText(url); setMessage("Link copied to clipboard."); } catch { setMessage("Select and copy the URL above."); } }}>Copy link</button>
        <a className="btn btn-ghost" style={{ flex: 1, textDecoration: "none", textAlign: "center" }} target="_blank" rel="noreferrer" href={"https://wa.me/?text=" + encodeURIComponent("Vaani Portal: " + url)}>WhatsApp</a>
      </div>
      <p className="source-note" style={{ marginTop: "10px" }}>Published portals are preserved as permanent snapshots.</p></>}
    <p role="status">{message}</p>
  </section>;
}
