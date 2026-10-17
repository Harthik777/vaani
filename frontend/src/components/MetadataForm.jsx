const FIELDS = {
  awareness: [["speaker", "Speaker name"], ["designation", "Speaker title"], ["event", "Event / address"], ["area", "Area covered"]],
  audit: [["asset", "Asset name / ID"], ["inspector", "Inspector ID"], ["gps", "GPS coordinates"], ["inspected_at", "Inspection date and time"]],
  deals: [["buyer", "Buyer"], ["seller", "Seller"], ["goods", "Itemized goods / grade"], ["value", "Total order value"], ["delivery", "Delivery date / SLA"], ["terms", "Payment, tax and penalty terms"]],
  business: [["owner", "Business / owner"], ["site", "Site / location"]],
};
export default function MetadataForm({ mode, metadata, onChange }) {
  return <details className="card"><summary>Document details and source identity</summary><div className="form-grid">
    {[["title", "Document title"], ...FIELDS[mode], ["effective_at", "Effective date / time"], ["reviewer", "Reviewer name"], ["review_notes", "Unresolved details / sign-off notes"]].map(([key, label]) => <label key={key}>{label}
      <input value={metadata[key] || ""} placeholder="Not provided" onChange={e => onChange({ ...metadata, [key]: e.target.value })} />
    </label>)}
  </div><p className="source-note">Only enter identities and details you can verify. Missing details remain marked as not provided.</p></details>;
}
