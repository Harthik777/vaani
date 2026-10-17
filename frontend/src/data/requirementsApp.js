// Same deterministic app as backend/services/microapps.py requirements_app(): one shared template.
import TEMPLATE from "../../../shared/requirements_app.html?raw";

export function requirementsApp(title, rules = [], openQuestions = []) {
  const items = rules.map((r, i) => ({ req_id: r.req_id || "FR-" + String(i + 1).padStart(2, "0"), title: r.title || "", condition: r.condition || "",
    action: r.action || "", exception: r.exception || null, speaker: r.speaker || null, acceptance: r.acceptance || [] }));
  // "<" -> < inside the JSON literal, so data can never close the <script> element.
  const data = JSON.stringify({ title: title || "Requirements", rules: items, open_questions: openQuestions }).replaceAll("<", "\u003c");
  return TEMPLATE.replace("/*__VAANI_DATA__*/null", () => data);
}
