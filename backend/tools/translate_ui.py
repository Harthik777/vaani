"""Translate the interface strings once with Sarvam Translate and write shared/ui-strings.json.

Every `t("...")` call in frontend/src is a key (the English text). Run after adding or changing interface text:
    cd backend && python tools/translate_ui.py            # all languages
    cd backend && python tools/translate_ui.py hindi      # one language
Existing translations are kept; only new keys are sent. Delete a key from the JSON to re-translate it.
"""
import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from services import config, sarvam  # noqa: E402

OUT = ROOT / "shared" / "ui-strings.json"
LANGS = ["hindi", "kannada", "tamil", "telugu", "marathi", "bengali"]
KEY = re.compile(r'\bt\("((?:[^"\\]|\\.)+)"\)')
# Product names and codes stay as they are inside a translated sentence.
# Labels that reach t() through variables (step bar, checklist, statuses, timing badges).
EXTRA = ["Start", "Speak", "Agent questions", "Review", "Approve", "BRD + App", "Goal / problem", "Users and stakeholders", "Key features", "Timeline",
         "Budget", "Success measure", "Constraints", "Sign-off owner", "missing", "answered", "skipped", "already said", "agent", "extraction", "BRD draft",
         "app", "review", "flagged", "left", "Help", "Back"]
KEEP = ["VAANI", "Vaani", "Sarvam", "Saaras", "Bulbul", "BRD", "Jira", "PDF", "Word", "Excel", "WhatsApp", "QR", "Wi-Fi", "[Name]"]


def keys():
    found = []
    for path in sorted((ROOT / "frontend" / "src").rglob("*.jsx")):
        for m in KEY.finditer(path.read_text(encoding="utf-8")):
            k = m.group(1).replace('\\"', '"').replace("\\'", "'")
            if k not in found:
                found.append(k)
    return found + [k for k in EXTRA if k not in found]


def tidy(src, out):
    """Keep arrows and trailing punctuation shape, and the product names, as in the source."""
    out = (out or "").strip()
    if not out:
        return src
    if src.endswith(" →") and not out.endswith("→"):
        out = out.rstrip(" →") + " →"
    if src.endswith(":") and not out.endswith(":"):
        out = out.rstrip(" :") + ":"
    return out


async def translate_slowly(texts, lang, parallel=3):
    """A few at a time with back-off: Sarvam's translate endpoint rate-limits bursts (429)."""
    sem = asyncio.Semaphore(parallel)
    out = {}

    async def one(text):
        async with sem:
            for attempt in range(6):
                try:
                    out[text] = await sarvam.translate(text, lang)
                    return
                except sarvam.SarvamError as exc:
                    if exc.status != 429:
                        raise
                    await asyncio.sleep(1.5 * (attempt + 1))
            print("  gave up on:", text[:60])
    await asyncio.gather(*(one(t) for t in texts))
    return out


async def main(only=None):
    if not sarvam.enabled():
        raise SystemExit("Set SARVAM_API_KEY in backend/.env first")
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    all_keys = keys()
    print(f"{len(all_keys)} interface strings")
    for lang in (only or LANGS):
        done = data.setdefault(lang, {})
        todo = [k for k in all_keys if k not in done]
        if not todo:
            print(f"{lang}: up to date")
            continue
        translated = await translate_slowly(todo, lang)
        n = 0
        for k in todo:
            v = tidy(k, translated.get(k))
            if v and v != k:
                done[k] = v
                n += 1
        print(f"{lang}: {n} new")
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or None))
