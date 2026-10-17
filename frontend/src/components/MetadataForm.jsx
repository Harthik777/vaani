const FIELDS = {
  awareness: [["speaker", "Speaker name"], ["designation", "Speaker title"], ["event", "Event / address"], ["area", "Area covered"]],
  audit: [["asset", "Asset name / ID"], ["inspector", "Inspector ID"], ["gps", "GPS coordinates"], ["inspected_at", "Inspection date and time"]],
  deals: [["buyer", "Buyer"], ["seller", "Seller"], ["goods", "Itemized goods / grade"], ["value", "Total order value"], ["delivery", "Delivery date / SLA"], ["terms", "Payment, tax and penalty terms"]],
  business: [["owner", "Business / owner"], ["site", "Site / location"]],
};
export default function MetadataForm({ mode, metadata, onChange, t = s => s }) {
  const primary = mode === "business" ? ["owner", t("Business name (and owner)")] : FIELDS[mode][0];
  const rest = [["title", "Document title"], ...FIELDS[mode].filter(([k]) => k !== primary[0]), ["effective_at", "Effective date / time"], ["reviewer", "Reviewer name"], ["review_notes", "Unresolved details / sign-off notes"]];
  return <div className="meta">
    <label className="meta-primary">{primary[1]}<input value={metadata[primary[0]] || ""} placeholder={mode === "business" ? "e.g. Sri Lakshmi Agencies, Lakshmi" : "Not provided"} onChange={e => onChange({ ...metadata, [primary[0]]: e.target.value })} /></label>
    <details className="meta-more"><summary>{t("More details for the document")}</summary><div className="form-grid">
      {rest.map(([key, label]) => <label key={key}>{label}
        <input value={metadata[key] || ""} placeholder="Not provided" onChange={e => onChange({ ...metadata, [key]: e.target.value })} />
      </label>)}
    </div><p className="source-note">Only enter identities and details you can verify. Missing details remain marked as not provided.</p></details>
  </div>;
}
