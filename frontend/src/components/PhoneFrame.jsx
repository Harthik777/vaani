import { useState } from "react";
import { api } from "../api/client.js";
import SourceAudio from "./SourceAudio.jsx";
import { getBespokeAppHtml } from "../data/microapps.js";

// Generated apps are untrusted (an LLM wrote them from speech). They run in an opaque-origin sandbox
// with a CSP that forbids any network access, both inline and when opened in a new tab.
const CSP = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; form-action 'none'; base-uri 'none'">`;
export const SANDBOX = "allow-scripts allow-modals allow-popups allow-popups-to-escape-sandbox";
export function sandboxedHtml(html) {
  if (!html) return null;
  return /<head[^>]*>/i.test(html) ? html.replace(/<head[^>]*>/i, m => m + CSP) : CSP + html;
}
export function openSandboxed(html) {
  if (!html) return;
  const attr = html.replaceAll("&", "&amp;").replaceAll('"', "&quot;");
  const page = `<!doctype html><html><head><meta charset="utf-8"><title>Vaani generated app</title><style>html,body{margin:0;height:100%;background:#0b1220}iframe{border:0;width:100%;height:100%}</style></head><body><iframe sandbox="${SANDBOX}" srcdoc="${attr}"></iframe></body></html>`;
  window.open(URL.createObjectURL(new Blob([page], { type: "text/html;charset=utf-8" })), "_blank");
}

export function Widget({ c, evidence = [], portal, widgetId, widgets = {}, onWidgets = () => {}, metadata = {}, shareUrl }) {
  const [message, setMessage] = useState(""), [busy, setBusy] = useState(false);
  const value = widgets[widgetId] || {};
  const save = next => onWidgets({ ...widgets, [widgetId]: next });
  const props = c.props || {};
  if (c.type === "statTile" || c.type === "list") return <div className="widget tile"><span>{c.label}</span><b>{props.value}</b></div>;
  if (c.type === "alert") return <div className={"widget severity-" + props.level}><strong>{props.level === "info" ? "" : props.level?.toUpperCase() + " · "}{c.label}</strong><p>{props.detail}</p></div>;
  if (c.type === "checklist") return <fieldset className="widget checklist-w"><legend>{c.label}</legend>{(props.items || []).map((item, i) =>
    <label className="clist-item" key={i}><input type="checkbox" checked={!!value[i]} onChange={e => save({ ...value, [i]: e.target.checked })} /><span style={{ textDecoration: value[i] ? "line-through" : "none" }}>{item}</span></label>
  )}</fieldset>;
  if (c.type === "quotePlayer") return <div className="widget"><blockquote>{c.label}</blockquote><SourceAudio evidence={evidence.find(e => e.id === props.evidenceId)} start={props.start} end={props.end} portal={portal} /></div>;
  if (c.type === "contactCard") return <div className="widget contact-w"><span>{c.label}</span><a href={"tel:" + String(props.number).replace(/[^+0-9]/g, "")}>Call {props.number}</a></div>;
  if (c.type === "mapLink") return <a className="widget map-link" target="_blank" rel="noreferrer" href={"https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent("primary health center " + (metadata.area || "near me"))}>{c.label} ↗</a>;
  if (c.type === "milestones") {
    const steps = ["Advance paid", "Dispatched", "Quality inspection passed", "Balance settled"];
    const completed = value.completed || 0;
    return <fieldset className="widget"><legend>{c.label}</legend><progress max="4" value={completed} aria-label="Reported milestone progress" />
      {steps.map((label, i) => <label className="check" key={label}><input type="checkbox" checked={completed > i}
        disabled={i > completed || (i >= 2 && widgets.quality?.outcome !== "pass")}
        onChange={e => save({ completed: e.target.checked ? i + 1 : i })} />{label}</label>)}
      <p className="source-note">Manually reported progress; payment settlement is not gateway-verified.</p></fieldset>;
  }
  if (c.type === "qualityForm") return <form className="widget" onSubmit={e => {
    e.preventDefault();
    const f = new FormData(e.currentTarget), quality = { inspector: f.get("inspector"), shrinkage: f.get("shrinkage"), notes: f.get("notes"), outcome: f.get("outcome"), saved_at: new Date().toISOString() };
    const next = { ...widgets, quality };
    if (quality.outcome !== "pass") for (const [key, v] of Object.entries(next)) if (v.completed > 2) next[key] = { ...v, completed: 2 };
    onWidgets(next); setMessage("Inspection saved on this device.");
  }}><h3>{c.label}</h3><label>Inspector<input name="inspector" required defaultValue={widgets.quality?.inspector || ""} /></label>
    <label>Measured shrinkage (%)<input name="shrinkage" required type="number" min="0" max="100" step="0.01" defaultValue={widgets.quality?.shrinkage || ""} /></label>
    <label>Findings / agreed penalty<textarea name="notes" defaultValue={widgets.quality?.notes || ""} /></label>
    <label>Outcome<select name="outcome" defaultValue={widgets.quality?.outcome || "pending"}><option value="pending">Pending</option><option value="pass">Pass against agreed terms</option><option value="fail">Fail / hold clearance</option></select></label>
    <button className="btn btn-primary">Save inspection</button><p role="status">{message}</p></form>;
  if (c.type === "button") return <div className="widget">
    <button className="btn btn-primary" disabled={busy} onClick={async () => {
      setMessage(""); setBusy(true);
      try {
        if (props.action === "share") {
          const targetUrl = shareUrl || window.location.href;
          await navigator.clipboard.writeText(targetUrl);
          setMessage("Advisory link copied.");
        } else if (props.action === "pay") setMessage("Payment integration is deferred. No payment is initiated.");
        else if (["dispatch", "order"].includes(props.action)) {
          const ticket = await api.ticket({ kind: props.action === "dispatch" ? "maintenance" : "procurement", asset: metadata.asset || metadata.title || "Reviewed requirements", description: metadata.ticketSummary || c.label });
          save({ ticket }); setMessage("Ticket " + ticket.id + ": " + ticket.status);
        } else setMessage("No workflow configured for this action.");
      } catch (e) { setMessage(e.message); } finally { setBusy(false); }
    }}>{c.label}</button>
    {value.ticket && <p>Ticket {value.ticket.id}: {value.ticket.status}</p>}
    <p role="status">{message}</p>
  </div>;
  return <div className="widget">{c.label}</div>;
}

export default function PhoneFrame({
  screens = [],
  appHtml,
  compact,
  evidence = [],
  portal,
  widgets,
  onWidgets,
  metadata = {},
  shareUrl,
  responsive = false,
  previewOnly = false,
  targetDevice = "desktop",
  appLabel
}) {
  const [viewport, setViewport] = useState(() => {
    if (targetDevice === "mobile") return "mobile";
    if (targetDevice === "desktop") return "desktop";
    return typeof window !== "undefined" && window.innerWidth <= 768 ? "mobile" : "desktop";
  });

  const effectiveAppHtml = sandboxedHtml(appHtml || screens?.appHtml || (metadata?.mode ? getBespokeAppHtml(metadata.mode, metadata, []) : null));
  const openInNewTab = () => openSandboxed(effectiveAppHtml);

  const isDesktop = viewport === "desktop";
  const frameClass = responsive
    ? "portal-widgets"
    : (isDesktop
        ? "laptop-webpage-frame"
        : "phone phone-mobile-frame" + (compact ? " phone-compact" : ""));

  const checklistScreen = screens.find(s => s.components.some(c => c.type === "checklist"));
  const checklistIndex = checklistScreen?.components.findIndex(c => c.type === "checklist");
  const checklistComponent = checklistIndex >= 0 ? checklistScreen.components[checklistIndex] : null;

  return (
    <div className={frameClass}>
      {!responsive && isDesktop && (
        <div className="laptop-top-bar">
          <div className="laptop-header-left">
            <span className="laptop-brand">वाणी · Vaani Webpage</span>
            <span className="laptop-badge">{appLabel || "Desktop Web App"}</span>
          </div>
          <div className="laptop-header-actions">
            <button type="button" className="btn-browser-launch" title="Open synthesized web app in full window" onClick={openInNewTab}>
              Launch Full Webpage ↗
            </button>
          </div>
        </div>
      )}
      {!responsive && !isDesktop && <div className="ph">वाणी · Vaani Mobile</div>}

      {effectiveAppHtml && (
        <div className="generative-app-container">
          <div className="browser-chrome">
            <div className="browser-dots" aria-hidden="true">
              <span className="dot dot-red" />
              <span className="dot dot-yellow" />
              <span className="dot dot-green" />
            </div>
            <div className="browser-url-bar">
              <span className="browser-lock">🔒</span>
              <span className="browser-url">{appLabel || "Generated app"} · sandboxed, no network access</span>
            </div>
            <button type="button" className="btn-browser-launch" title="Open synthesized web app in full window" onClick={openInNewTab}>
              Launch App ↗
            </button>
          </div>
          <div className="viewport-bar">
            <span className="vp-label">⚡ Viewport:</span>
            <div className="vp-buttons" role="group" aria-label="Viewport Switcher">
              <button
                type="button"
                className={"vp-btn" + (viewport === "desktop" ? " active" : "")}
                onClick={() => setViewport("desktop")}
              >
                💻 Laptop / Desktop Webpage
              </button>
              <button
                type="button"
                className={"vp-btn" + (viewport === "mobile" ? " active" : "")}
                onClick={() => setViewport("mobile")}
              >
                📱 Mobile App (380px)
              </button>
            </div>
          </div>
          <div className={"app-iframe-wrapper vp-" + viewport}>
            <iframe
              className="app-iframe"
              title="Interactive synthesized micro-app"
              sandbox={SANDBOX}
              srcDoc={effectiveAppHtml}
            />
          </div>
        </div>
      )}

      {previewOnly ? (
        <div className="preview-app-actions">
          <div className="app-preview-summary-card">
            <div className="preview-indicator">
              <span>⚡ Live Interactive Webpage (Preview)</span>
            </div>
            <p className="app-preview-note">
              Click tabs, buttons and interactive controls directly in the live laptop window above. To experience all full-screen views, open in a dedicated tab.
            </p>
            <button type="button" className="btn btn-app btn-sm" onClick={openInNewTab}>
              🚀 Launch Full Webpage ↗
            </button>
          </div>
          {checklistComponent && (
            <div className="preview-checklist-box">
              <Widget
                widgetId={(checklistScreen?.screenId || "actions") + "-" + checklistIndex}
                c={checklistComponent}
                evidence={evidence}
                portal={portal}
                widgets={widgets}
                onWidgets={onWidgets}
                metadata={metadata}
                shareUrl={shareUrl}
              />
            </div>
          )}
        </div>
      ) : (
        screens.map(s => (
          <section className="scr" key={s.screenId}>
            <h3 className="sl">{s.title}</h3>
            {s.components.map((c, i) => (
              <Widget
                key={s.screenId + i}
                widgetId={s.screenId + "-" + i}
                c={c}
                evidence={evidence}
                portal={portal}
                widgets={widgets}
                onWidgets={onWidgets}
                metadata={metadata}
                shareUrl={shareUrl}
              />
            ))}
          </section>
        ))
      )}
    </div>
  );
}
