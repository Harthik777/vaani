"""Grounding verifier. Mirrors frontend/src/data/verify.js — keep the two in sync.

A quote is grounded only if it is an exact substring of the source text.
A number is grounded if it appears in the quote ("exact"), or if the model named the
exact words in the quote that state it ("interpreted": a human must confirm, e.g. 3 <- "तीन").
Anything else is "unsupported": the AI wrote a number nobody said.
"""
import re
from difflib import SequenceMatcher

_TRANS = {}
# Devanagari, Bengali, Gurmukhi, Gujarati, Odia, Tamil, Telugu, Kannada, Malayalam digit blocks
for _zero in (0x0966, 0x09E6, 0x0A66, 0x0AE6, 0x0B66, 0x0BE6, 0x0C66, 0x0CE6, 0x0D66):
    for _i in range(10):
        _TRANS[_zero + _i] = str(_i)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_GROUPED = re.compile(r"\d{1,3}(?:,\d{2,3})+(?:\.\d+)?")


def ascii_digits(text):
    return (text or "").translate(_TRANS)


def _canonical(raw):
    if "." in raw:
        whole, frac = raw.split(".", 1)
        frac = frac.rstrip("0")
        raw = whole + ("." + frac if frac else "")
    return re.sub(r"^0+(?=\d)", "", raw)


_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
_SCALES = {"hundred": 100, "thousand": 1000, "lakh": 100000, "lakhs": 100000, "million": 1000000, "crore": 10000000, "crores": 10000000}


def word_numbers(text):
    """English number words, so 'fifty kg' cannot slip past the check: 'twenty thousand' -> '20000'.
    A lone 'one' is ignored (usually a pronoun), and so is a scale word with no number before it."""
    tokens = re.findall(r"[a-z]+", (text or "").lower())
    out, run = [], []

    def flush():
        if run and not (run == ["one"]) and any(t in _UNITS or t in _TENS for t in run):
            total = current = 0
            for t in run:
                if t in _UNITS or t in _TENS:
                    current += _UNITS.get(t, _TENS.get(t, 0))
                elif t == "hundred":
                    current = (current or 1) * 100
                else:
                    total += (current or 1) * _SCALES[t]
                    current = 0
            out.append(str(total + current))
        run.clear()

    for i, t in enumerate(tokens):
        if t in _UNITS or t in _TENS or (t in _SCALES and run):
            run.append(t)
        elif t == "and" and run and i + 1 < len(tokens) and (tokens[i + 1] in _UNITS or tokens[i + 1] in _TENS):
            continue
        else:
            flush()
    flush()
    return out


def numbers(text):
    """Every number in the text, canonicalised: '₹2,400' -> '2400', '०९.५' -> '9.5', 'fifty' -> '50'."""
    out = []
    for m in _NUMBER.finditer(ascii_digits(text)):
        raw = m.group()
        if _GROUPED.fullmatch(raw):
            out.append(_canonical(raw.replace(",", "")))
        else:
            out.extend(_canonical(part) for part in raw.split(",") if part)
    return out + word_numbers(text)


def check_numbers(text, quote, spoken=None):
    quote_numbers = set(numbers(quote))
    quote_ascii = ascii_digits(quote)
    claims = {}
    for item in spoken or []:
        if isinstance(item, dict):
            for value in numbers(str(item.get("value", ""))):
                claims.setdefault(value, []).append(str(item.get("spoken") or ""))
    result, seen = [], set()
    for value in numbers(text):
        if value in seen:
            continue
        seen.add(value)
        if value in quote_numbers:
            result.append({"value": value, "status": "exact", "spoken": value})
            continue
        words = next((w for w in claims.get(value, []) if w.strip() and ascii_digits(w) in quote_ascii), None)
        if words:
            result.append({"value": value, "status": "interpreted", "spoken": words})
        else:
            result.append({"value": value, "status": "unsupported", "spoken": None})
    return result


def summarize(quote_status, number_checks):
    if quote_status != "verified":
        return "rejected"
    if any(n["status"] == "unsupported" for n in number_checks):
        return "unsupported_number"
    if any(n["status"] == "interpreted" for n in number_checks):
        return "needs_confirmation"
    return "verified"


def verify_rule(rule, transcript):
    quote = (rule.get("source_quote") or "").strip()
    if not quote:
        quote_status = "missing"
    elif quote in (transcript or ""):
        quote_status = "verified"
    else:
        quote_status = "untraceable"
    text = " ".join(str(rule.get(k) or "") for k in ("title", "condition", "action", "exception"))
    checks = check_numbers(text, quote, rule.get("numbers")) if quote_status == "verified" else []
    return {"quote": quote_status, "numbers": checks, "status": summarize(quote_status, checks)}


_PLACEHOLDER = re.compile(r"(?i)\W*(ai suggestion|please confirm|to be confirmed|n/?a|none|tbd|\.\.\.)[\W\s,]*(please confirm)?\W*")


def verify_item(item, sources):
    """BRD section items. Spoken items need a verbatim quote; AI suggestions may not contain numbers."""
    text, quote = str(item.get("text") or "").strip(), (item.get("source_quote") or "").strip()
    if not text or _PLACEHOLDER.fullmatch(text):
        return None, "empty"
    note = item.get("quote_note")
    if quote:
        if quote not in sources:
            fixed = repair_quote(quote, sources)
            if not fixed:
                return None, f'quote not found in what was said: "{quote[:120]}"'
            note, quote = f'Quote corrected to the exact words spoken (the AI copied: "{quote[:200]}")', fixed
        checks = check_numbers(text, quote, item.get("numbers"))
        bad = [n["value"] for n in checks if n["status"] == "unsupported"]
        if bad:
            return None, "number(s) " + ", ".join(bad) + " were not spoken"
        clean = {"text": text, "source_quote": quote, "origin": "spoken", "numbers": checks}
        return ({**clean, "quote_note": note} if note else clean), None
    bad = numbers(text)
    if bad:
        return None, "AI suggestion contains number(s) nobody said: " + ", ".join(dict.fromkeys(bad))
    return {"text": text, "source_quote": None, "origin": "suggested", "numbers": []}, None


def repair_quote(quote, transcript, threshold=0.97):
    """If the model mis-copied a quote by a character or two (e.g. a dropped vowel sign), return the
    exact transcript text it was copying. The result is always real transcript text, never the model's."""
    quote = (quote or "").strip()
    if len(quote) < 20 or quote in (transcript or ""):
        return None
    best, best_ratio = None, 0.0
    for line in (transcript or "").split("\n"):
        blocks = [b for b in SequenceMatcher(None, line, quote, autojunk=False).get_matching_blocks() if b.size]
        if not blocks:
            continue
        candidate = line[blocks[0].a: blocks[-1].a + blocks[-1].size].strip()
        if not candidate or abs(len(candidate) - len(quote)) > max(3, len(quote) // 20):
            continue
        ratio = SequenceMatcher(None, candidate, quote, autojunk=False).ratio()
        if ratio > best_ratio:
            best, best_ratio = candidate, ratio
    return best if best_ratio >= threshold and best in transcript else None
