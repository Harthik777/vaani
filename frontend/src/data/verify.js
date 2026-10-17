// Grounding verifier. Mirrors backend/services/verify.py — keep the two in sync.
const ZEROS = [0x0966, 0x09E6, 0x0A66, 0x0AE6, 0x0B66, 0x0BE6, 0x0C66, 0x0CE6, 0x0D66];
const DIGIT_MAP = new Map();
for (const zero of ZEROS) for (let i = 0; i < 10; i++) DIGIT_MAP.set(String.fromCharCode(zero + i), String(i));
export const asciiDigits = text => [...(text || "")].map(c => DIGIT_MAP.get(c) ?? c).join("");

const canonical = raw => {
  if (raw.includes(".")) { let [whole, frac] = raw.split("."); frac = frac.replace(/0+$/, ""); raw = whole + (frac ? "." + frac : ""); }
  return raw.replace(/^0+(?=\d)/, "") || "0";
};
const UNITS = Object.fromEntries("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split(" ").map((w, i) => [w, i]));
const TENS = Object.fromEntries("twenty thirty forty fifty sixty seventy eighty ninety".split(" ").map((w, i) => [w, 10 * (i + 2)]));
const SCALES = { hundred: 100, thousand: 1000, lakh: 100000, lakhs: 100000, million: 1000000, crore: 10000000, crores: 10000000 };
const isNum = t => t in UNITS || t in TENS;

export function wordNumbers(text) {
  const tokens = (text || "").toLowerCase().match(/[a-z]+/g) || [];
  const out = []; let run = [];
  const flush = () => {
    if (run.length && !(run.length === 1 && run[0] === "one") && run.some(isNum)) {
      let total = 0, current = 0;
      for (const t of run) {
        if (isNum(t)) current += UNITS[t] ?? TENS[t];
        else if (t === "hundred") current = (current || 1) * 100;
        else { total += (current || 1) * SCALES[t]; current = 0; }
      }
      out.push(String(total + current));
    }
    run = [];
  };
  tokens.forEach((t, i) => {
    if (isNum(t) || (t in SCALES && run.length)) run.push(t);
    else if (t === "and" && run.length && i + 1 < tokens.length && isNum(tokens[i + 1])) return;
    else flush();
  });
  flush();
  return out;
}

export function numbers(text) {
  const out = [];
  for (const m of asciiDigits(text).matchAll(/\d+(?:[.,]\d+)*/g)) {
    const raw = m[0];
    if (/^\d{1,3}(?:,\d{2,3})+(?:\.\d+)?$/.test(raw)) out.push(canonical(raw.replaceAll(",", "")));
    else out.push(...raw.split(",").filter(Boolean).map(canonical));
  }
  return [...out, ...wordNumbers(text)];
}

export function checkNumbers(text, quote, spoken = []) {
  const quoteNumbers = new Set(numbers(quote)), quoteAscii = asciiDigits(quote);
  const claims = {};
  for (const item of spoken || []) for (const v of numbers(String(item?.value ?? ""))) (claims[v] ||= []).push(String(item?.spoken || ""));
  const seen = new Set(), result = [];
  for (const value of numbers(text)) {
    if (seen.has(value)) continue;
    seen.add(value);
    if (quoteNumbers.has(value)) { result.push({ value, status: "exact", spoken: value }); continue; }
    const words = (claims[value] || []).find(w => w.trim() && quoteAscii.includes(asciiDigits(w)));
    result.push(words ? { value, status: "interpreted", spoken: words } : { value, status: "unsupported", spoken: null });
  }
  return result;
}

export function verifyRule(rule, transcript) {
  const quote = (rule.source_quote || "").trim();
  const quoteStatus = !quote ? "missing" : (transcript || "").includes(quote) ? "verified" : "untraceable";
  const text = ["title", "condition", "action", "exception"].map(k => rule[k] || "").join(" ");
  const nums = quoteStatus === "verified" ? checkNumbers(text, quote, rule.numbers) : [];
  const status = quoteStatus !== "verified" ? "rejected" : nums.some(n => n.status === "unsupported") ? "unsupported_number"
    : nums.some(n => n.status === "interpreted") ? "needs_confirmation" : "verified";
  return { quote: quoteStatus, numbers: nums, status };
}

export const STATUS_LABEL = {
  verified: "✅ Verified against speech",
  needs_confirmation: "🔶 Numbers interpreted from spoken words: confirm",
  unsupported_number: "⛔ Contains a number nobody said",
  rejected: "⛔ Quote not found in what was said",
  not_checked: "Not checked",
};
