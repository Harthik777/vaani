// Client-side exports of the compiled BRD: Markdown (for GitHub/Notion) and a Jira-importable CSV of user stories.
const ORIGIN = { spoken: "spoken", suggested: "AI suggestion: confirm" };
const numberNote = v => (v?.numbers || []).filter(n => n.status !== "exact").map(n => `${n.value} ← "${n.spoken || "not spoken"}" (${n.status})`).join("; ");

export function toMarkdown(brd, translations = null) {
  const tr = text => translations?.[text] ? `\n  🌐 ${translations[text]}` : "";
  const lines = [`# ${brd.project_name}`, "", `*${brd.document_type}. ${brd.status}*`, ""];
  if (brd.demo) lines.push("> DEMONSTRATION: sample content.", "");
  const meta = Object.entries(brd.metadata || {}).filter(([k, v]) => v && !["ticketSummary", "review_notes"].includes(k));
  if (meta.length) lines.push("| Field | Value |", "|---|---|", ...meta.map(([k, v]) => `| ${k.replaceAll("_", " ")} | ${String(v).replaceAll("|", "\\|")} |`), "");
  let n = 0;
  for (const [key, items] of Object.entries(brd.sections || {})) {
    lines.push(`## ${++n}. ${brd.section_titles?.[key] || key}`, "");
    if (!items.length) lines.push("_Not captured yet._");
    for (const i of items) lines.push(`- ${i.text} _(${ORIGIN[i.origin] || i.origin})_` + tr(i.text) + (i.source_quote ? `\n  > ${i.source_quote}` : ""));
    lines.push("");
  }
  lines.push(`## ${++n}. Functional requirements and traceability`, "", "| ID | Requirement | Spoken by | Source quote | Verification | Approved |", "|---|---|---|---|---|---|");
  for (const r of brd.business_rules) {
    const cell = s => String(s ?? "").replaceAll("|", "\\|").replaceAll("\n", " ");
    lines.push(`| ${r.req_id} | **${cell(r.title)}**<br>${cell(r.rule)}${translations?.[r.rule] ? "<br>🌐 " + cell(translations[r.rule]) : ""}${r.acceptance?.length ? "<br>" + r.acceptance.map(a => "• " + cell(a)).join("<br>") : ""} | ${cell(r.speaker || "")} | "${cell(r.source_quote)}"${r.start != null ? ` (${r.start}s–${r.end}s)` : ""} | ${cell(r.verification?.status?.replaceAll("_", " "))}${numberNote(r.verification) ? "<br>" + cell(numberNote(r.verification)) : ""} | ${cell(r.approved_by || "Pending")} |`);
  }
  lines.push("", `## ${++n}. Open questions`, "", ...(brd.open_questions?.length ? brd.open_questions.map(q => "- " + q + tr(q)) : ["- None."]), "");
  if (brd.rejected?.length) lines.push(`## ${++n}. Verification report: blocked AI content`, "", ...brd.rejected.map(r => `- ~~${r.text}~~ (${r.reason})`), "");
  lines.push(`## ${++n}. Sign-off`, "", brd.authorization, "");
  return lines.join("\n");
}

const csvCell = v => `"${String(v ?? "").replaceAll('"', '""')}"`;
export function toJiraCsv(brd) {
  const header = ["Summary", "Issue Type", "Priority", "Labels", "Description"];
  const rows = brd.business_rules.map(r => [
    `${r.req_id} ${r.title}`, "Story", "Medium", ["vaani", (r.type || "requirement").replace(/\s+/g, "-")].join(" "),
    [`Requirement: ${r.rule}`, r.speaker ? `Spoken by: ${r.speaker}` : "", `Source quote: "${r.source_quote}"`,
      `Verification: ${r.verification?.status || "not checked"}${numberNote(r.verification) ? " (" + numberNote(r.verification) + ")" : ""}`,
      r.acceptance?.length ? "Acceptance criteria:\n" + r.acceptance.map(a => "* " + a).join("\n") : "",
      `Approved by ${r.approved_by || "pending"} at ${r.approved_at || "-"}`].filter(Boolean).join("\n"),
  ]);
  return [header, ...rows].map(row => row.map(csvCell).join(",")).join("\r\n");
}

export function download(name, content, type) {
  const url = URL.createObjectURL(content instanceof Blob ? content : new Blob([content], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const fileName = brd => (brd.project_name || "BRD").replace(/[^A-Za-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "BRD";
