// Mirrors backend/services/compiler.py: only approved rules and verified content reach the document.
import { DOCUMENT_TYPES } from "./mock.js";
import { getBespokeAppHtml } from "./microapps.js";
import { CHECKLIST, SECTIONS, ANSWER_SECTIONS } from "./brd.js";
import { checkNumbers, numbers, verifyRule } from "./verify.js";

export const ruleText = r => `IF ${r.condition} THEN ${r.action}${r.exception ? ` UNLESS ${r.exception}` : ""}`;
export const requirementId = i => "FR-" + String(i + 1).padStart(2, "0");
const PROFILE_FIELDS = { awareness: ["speaker", "designation", "event", "area"], audit: ["asset", "gps", "inspected_at", "inspector"], deals: ["buyer", "seller", "goods", "value", "delivery", "terms"], business: ["owner", "site"] };
const emptySections = () => Object.fromEntries(SECTIONS.map(s => [s.key, []]));

function answerSections(answers = [], transcript = "") {
  const sections = emptySections();
  const labels = Object.fromEntries(CHECKLIST.map(c => [c.key, c.label]));
  for (const a of answers) {
    const target = ANSWER_SECTIONS[a.key], text = (a.answer || "").trim();
    if (target && text && transcript.includes(text))
      sections[target].push({ text: `${labels[a.key] || a.key}: ${text}`, source_quote: text, origin: "spoken", numbers: checkNumbers(text, text) });
  }
  return sections;
}

// AI sections were verified by the server; check again here so later transcript edits cannot leave stale claims.
function verifiedSections(raw = {}, transcript = "") {
  const sections = emptySections(), rejected = [];
  for (const [key, items] of Object.entries(raw || {})) {
    if (!(key in sections) || !Array.isArray(items)) continue;
    for (const item of items) {
      const text = (item?.text || "").trim(), quote = (item?.source_quote || "").trim();
      if (!text) continue;
      if (quote) {
        if (!transcript.includes(quote)) { rejected.push({ section: key, text, reason: "quote no longer in transcript" }); continue; }
        const nums = checkNumbers(text, quote, item.numbers);
        const bad = nums.filter(n => n.status === "unsupported").map(n => n.value);
        if (bad.length) { rejected.push({ section: key, text, reason: "number(s) " + bad.join(", ") + " were not spoken" }); continue; }
        sections[key].push({ text, source_quote: quote, origin: "spoken", numbers: nums });
      } else if (numbers(text).length) rejected.push({ section: key, text, reason: "AI suggestion contains number(s) nobody said" });
      else sections[key].push({ text, source_quote: null, origin: "suggested", numbers: [] });
    }
  }
  return { sections, rejected };
}

function merge(base, extra) {
  for (const [key, items] of Object.entries(extra)) {
    const seen = new Set((base[key] || []).map(i => i.text));
    base[key] = [...(base[key] || []), ...items.filter(i => !seen.has(i.text))];
  }
  return base;
}

export function compileDocument({ rules, mode, metadata = {}, domain = "", demo = false, transcript = "", answers = [], ai = null, coverage = [], conflicts = [] }) {
  const { sections: aiSections, rejected: staleRejected } = verifiedSections(ai?.sections, transcript);
  const sections = merge(answerSections(answers, transcript), aiSections);
  const acceptance = ai?.acceptance || [];
  const ids = new Set(rules.map(r => r.id));
  const answered = new Set(answers.map(a => a.key)), covered = new Set(coverage.filter(c => c.status === "covered").map(c => c.key));
  const openQuestions = coverage.length || answers.length ? CHECKLIST.filter(c => !answered.has(c.key) && !covered.has(c.key)).map(c => `${c.label}: ${c.question}`) : [];
  for (const c of conflicts) if (c.rule_ids.every(id => ids.has(id))) openQuestions.push("Conflict to resolve: " + c.explanation);
  if (metadata.review_notes) openQuestions.push(metadata.review_notes);
  return {
    project_name: metadata.title || DOCUMENT_TYPES[mode], document_type: DOCUMENT_TYPES[mode], mode, demo, metadata, problem_statement: domain,
    sections, section_titles: Object.fromEntries(SECTIONS.map(s => [s.key, s.title])),
    scope: rules.map(r => r.title),
    business_rules: rules.map((r, i) => ({
      req_id: requirementId(i), id: r.id, title: r.title, rule: ruleText(r), type: r.type, priority: "Reviewed requirement",
      source_quote: r.source_quote || "", speaker: r.speaker || null, evidence_id: r.evidence_id || null, start: r.start ?? null, end: r.end ?? null,
      approved_at: r.approved_at || null, approved_by: r.approved_by || null,
      verification: transcript ? verifyRule(r, transcript) : { quote: "not checked", numbers: [], status: "not_checked" },
      acceptance: acceptance.filter(a => a.rule_id === r.id).map(a => a.text),
    })),
    open_questions: openQuestions,
    rejected: [...(ai?.rejected || []), ...staleRejected],
    ai_brain: ai?.brain || null,
    status: "Draft for sign-off. Generated from recorded speech and reviewed rule by rule.",
    authorization: "Business owner: ____________________   IT / vendor lead: ____________________   Date: __________",
  };
}

export function compileScreens({ rules, mode, metadata = {}, domain = "", demo = false }) {
  const cards = PROFILE_FIELDS[mode].map(key => ({ type: "statTile", label: key.replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase()), props: { value: metadata[key] || "Not provided" } }));
  cards.push(...rules.flatMap(r => [
    { type: "alert", label: r.title, props: { level: ["critical", "moderate", "compliant"].includes(r.type) ? r.type : "info", detail: ruleText(r) } },
    { type: "quotePlayer", label: r.source_quote || "Source recording", props: { ruleId: r.id, evidenceId: r.evidence_id || null, start: r.start ?? null, end: r.end ?? null } },
  ]));
  const actions = [{ type: "checklist", label: "Reviewed actions", props: { items: rules.map(r => r.action) } }];
  if (mode === "awareness") actions.push(
    { type: "contactCard", label: "Health helpline", props: { number: "104" } },
    { type: "contactCard", label: "Ambulance", props: { number: "108" } },
    { type: "mapLink", label: "Find primary health centers", props: {} },
    { type: "button", label: "Copy advisory link", props: { action: "share" } },
  );
  else if (mode === "audit") actions.push({ type: "button", label: "Create maintenance ticket", props: { action: "dispatch" } });
  else if (mode === "deals") actions.push(
    { type: "milestones", label: "Order progress", props: {} },
    { type: "qualityForm", label: "Warehouse inspection", props: {} },
    { type: "button", label: "Prepare milestone payment", props: { action: "pay" } },
  );
  else actions.push({ type: "button", label: "Create procurement ticket", props: { action: "order" } });
  const appHtml = getBespokeAppHtml(mode, metadata, rules, domain);
  return { screens: [{ screenId: "requirements", title: DOCUMENT_TYPES[mode], components: cards }, { screenId: "actions", title: "Actions", components: actions }], appHtml, demo };
}
