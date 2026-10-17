import { useState } from "react";
import { api } from "../api/client.js";
export default function SharePanel({ published, onPublish, busy, mode, title, t = s => s }) {
  const [message, setMessage] = useState("");
  const url = published?.preview_url || published?.url;
  return <section className="card share-panel"><h3>{t("Share on a phone")}</h3>
    <p>{mode === "awareness" ? t("Publish a public web portal with your approved rules and recordings for community distribution.") : t("Publish a private page with the BRD, the app and the voice clips, protected by this session's access key.")}</p>
    <button className="btn btn-primary" disabled={busy || !!published} onClick={() => onPublish("")}>{published ? "✓ " + t("Version published") : t("Publish reviewed version")}</button>
    {published && <><label>{t("Shareable URL")}<input readOnly value={url} onFocus={e => e.target.select()} aria-label="Shareable URL" /></label>
      <a className="portal-direct-link" href={published.url} target="_blank" rel="noreferrer">{t("Open responsive portal ↗")}</a>
      {published.reach === "lan" && <p className="source-note">Opens on any phone on the same Wi-Fi (the backend must run with --host 0.0.0.0). For a link that works anywhere, set PUBLIC_URL to a Cloudflare quick tunnel.</p>}
      {published.reach === "local" && <p className="source-note">This link only opens on this laptop. Run `npx vite build` and restart the backend with --host 0.0.0.0 for a same-Wi-Fi link, or set PUBLIC_URL.</p>}
      {published.reach === "public" && <p className="source-note">Public link: opens anywhere.</p>}
      <div className="qr-row">
        <figure><img src={api.qrUrl(url)} alt="QR code for the portal link" width="168" height="168" onError={e => { e.currentTarget.closest("figure").hidden = true; }} /><figcaption>{t("Scan to open the BRD and voice clips")}</figcaption></figure>
        <figure><img src={api.qrUrl("https://wa.me/?text=" + encodeURIComponent((title ? title + " · " : "") + "Vaani BRD: " + url))} alt="QR code that opens WhatsApp with the link" width="168" height="168" onError={e => { e.currentTarget.closest("figure").hidden = true; }} /><figcaption>{t("Scan to forward on WhatsApp")}</figcaption></figure>
      </div>
      <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
        <button className="btn btn-ghost" style={{ flex: 1 }} onClick={async () => { try { await navigator.clipboard.writeText(url); setMessage("Link copied to clipboard."); } catch { setMessage("Select and copy the URL above."); } }}>{t("Copy link")}</button>
        <a className="btn btn-ghost" style={{ flex: 1, textDecoration: "none", textAlign: "center" }} target="_blank" rel="noreferrer" href={"https://wa.me/?text=" + encodeURIComponent("Vaani Portal: " + url)}>WhatsApp</a>
      </div>
      <p className="source-note" style={{ marginTop: "10px" }}>Published portals are preserved as permanent snapshots.</p></>}
    <p role="status">{message}</p>
  </section>;
}
