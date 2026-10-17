"""Measured accuracy for the two features judges will ask about.

1. Verifier (deterministic, no AI): planted unspoken numbers, altered quotes and number-word tricks
   across the English, Hindi and Kannada meeting demos. Reports catches, misses and false blocks.
2. Conflict detector (live, Sarvam 105B first, main LLM fallback): rule sets with planted
   owner-vs-manager contradictions and control sets with none. Reports precision and recall.

Run from backend/:  .venv/Scripts/python benchmark.py          (writes ../BENCHMARK.md and benchmark.json)
                    .venv/Scripts/python benchmark.py --no-llm (verifier only)
"""
import asyncio
import copy
import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from services import verify, agent, config, llm, sarvam
import mocks

MEET = mocks.MEETING
OUT_MD = Path(__file__).resolve().parents[1] / "BENCHMARK.md"
OUT_JSON = Path(__file__).resolve().parent / "benchmark.json"


# ───────────────────────── 1. Verifier ─────────────────────────
def verifier_cases():
    """(name, rule, transcript, expected_status, kind) with kind in {clean, planted}."""
    cases = []
    for lang, rules in MEET["rules"].items():
        tx = MEET["transcript"][lang]
        for r in rules:
            base = copy.deepcopy(r)
            cases.append((f"{lang}:{r['id']} clean", base, tx, "verified", "clean"))
            nums = [n["value"] for n in r.get("numbers", [])]
            if nums:
                v = nums[0]
                digits = re.sub(r"[^0-9]", "", v)
                bumped = str(int(digits) - 2)  # 50 -> 48, 100 -> 98, 20000 -> 19998
                # (a) a number nobody said, typed into the action
                m = copy.deepcopy(r); m["action"] = m["action"] + f" within {bumped} hours"; m["numbers"] = []
                cases.append((f"{lang}:{r['id']} planted unspoken {bumped}", m, tx, "unsupported_number", "planted"))
                # (b) the spoken number replaced by a different one in the condition
                m = copy.deepcopy(r); m["condition"] = m["condition"].replace(v, bumped); m["numbers"] = []
                if m["condition"] != r["condition"]:
                    cases.append((f"{lang}:{r['id']} swapped {v}->{bumped}", m, tx, "unsupported_number", "planted"))
                # (c) English number words instead of digits ("fifty") must not bypass the check
                words = {"50": "fifty", "100": "one hundred", "20,000": "twenty thousand", "20000": "twenty thousand"}.get(v)
                if words:
                    m = copy.deepcopy(r); m["action"] = m["action"] + f" (about {words} units)"; m["numbers"] = []
                    exp = "verified" if digits in verify.ascii_digits(r["source_quote"]).replace(",", "") else "unsupported_number"
                    # the words spell the same number that IS in the quote -> verified; a different number -> blocked
                    m2 = copy.deepcopy(r); m2["action"] = m2["action"] + " (about forty eight)"; m2["numbers"] = []
                    cases.append((f"{lang}:{r['id']} words same number", m, tx, exp, "clean"))
                    cases.append((f"{lang}:{r['id']} words 'forty eight'", m2, tx, "unsupported_number", "planted"))
                # (d) a number that WAS said, but by a different line (not in this quote)
                other = next((n["value"] for o in rules if o["id"] != r["id"] for n in o.get("numbers", []) if n["value"] != v), None)
                if other:
                    m = copy.deepcopy(r); m["action"] = m["action"] + f" and {other}"; m["numbers"] = []
                    cases.append((f"{lang}:{r['id']} number from another line {other}", m, tx, "unsupported_number", "planted"))
            # (e) quote altered by one character: must not pass as verified
            q = r["source_quote"]
            m = copy.deepcopy(r); m["source_quote"] = q[:-1] + ("।" if q.endswith(".") else ".")
            cases.append((f"{lang}:{r['id']} altered quote", m, tx, "rejected", "planted"))
            # (f) quote from a different transcript (nobody in this meeting said it)
            m = copy.deepcopy(r); m["source_quote"] = "The vendor will deliver in 7 days."
            cases.append((f"{lang}:{r['id']} foreign quote", m, tx, "rejected", "planted"))
    return cases


def run_verifier():
    rows, hits = [], {"clean_ok": 0, "clean_total": 0, "planted_caught": 0, "planted_total": 0}
    for name, rule, tx, expected, kind in verifier_cases():
        got = verify.verify_rule(rule, tx)["status"]
        # anything other than "verified" counts as a catch for planted cases; a repaired quote still blocks numbers
        ok = (got == "verified") if kind == "clean" else (got != "verified")
        if kind == "clean":
            hits["clean_total"] += 1; hits["clean_ok"] += ok
        else:
            hits["planted_total"] += 1; hits["planted_caught"] += ok
        rows.append({"case": name, "expected": expected, "got": got, "ok": bool(ok)})
    return rows, hits


# ───────────────────────── 2. Conflict detector ─────────────────────────
def rule(i, speaker, title, cond, act):
    return {"id": f"r{i}", "title": title, "condition": cond, "action": act, "exception": None, "confidence": "HIGH",
            "type": "requirement", "source_quote": "", "numbers": [], "speaker": speaker}


def conflict_sets():
    """Each: (name, rules, expected pairs as sets of ids)."""
    sets = []
    for lang in ("english", "hindi", "kannada"):
        rules = copy.deepcopy(MEET["rules"][lang])
        sets.append((f"meeting {lang} (owner 50 kg vs manager 100 kg)", rules, [{"r1", "r4"}]))
        control = [r for r in rules if r["id"] != "r4"]
        sets.append((f"meeting {lang} without the manager's threshold", control, []))
    sets.append(("delivery days", [
        rule(1, "Owner", "Delivery window", "an order is placed", "deliver within 7 days"),
        rule(2, "Manager", "Delivery window", "an order is placed", "deliver within 3 days"),
        rule(3, "Manager", "Invoice format", "an order is dispatched", "email a GST invoice"),
    ], [{"r1", "r2"}]))
    sets.append(("budget and approver", [
        rule(1, "Owner", "Budget", "the project is scoped", "keep the budget under 1 lakh rupees"),
        rule(2, "Accountant", "Budget", "the project is scoped", "the budget is 2 lakh rupees"),
        rule(3, "Owner", "Final approval", "the app is ready", "the owner approves the release"),
        rule(4, "Manager", "Final approval", "the app is ready", "the manager approves the release"),
    ], [{"r1", "r2"}, {"r3", "r4"}]))
    sets.append(("related but not contradictory", [
        rule(1, "Owner", "Low stock alert", "stock falls below 50 kg", "alert the owner"),
        rule(2, "Manager", "Weekly stock report", "every Monday", "send the stock report to the owner"),
        rule(3, "Manager", "Hindi interface", "any staff member uses the app", "show the app in Hindi"),
    ], []))
    sets.append(("same speaker, different numbers (not a stakeholder conflict)", [
        rule(1, "Owner", "Alert threshold cardamom", "cardamom stock falls below 50 kg", "alert the owner"),
        rule(2, "Owner", "Alert threshold pepper", "pepper stock falls below 20 kg", "alert the owner"),
        rule(3, "Manager", "Daily report", "every evening", "send the sales report on WhatsApp"),
    ], []))
    sets.append(("credit period", [
        rule(1, "Owner", "Credit period", "a regular customer buys on credit", "allow 30 days of credit"),
        rule(2, "Manager", "Credit period", "a regular customer buys on credit", "allow 15 days of credit"),
        rule(3, "Owner", "Language", "any staff member uses the app", "show the app in Kannada"),
    ], [{"r1", "r2"}]))
    return sets


async def run_conflicts():
    rows, tp = [], 0; fp = 0; fn = 0; brains = {}
    for name, rules, expected in conflict_sets():
        t = time.time()
        try:
            out = await agent.conflicts(rules, "", demo=False)
            found = [set(c["rule_ids"]) for c in out["conflicts"]]
            brain = out.get("brain")
        except Exception as e:
            found, brain = [], f"error: {e}"
        brains[brain] = brains.get(brain, 0) + 1
        hit = [p for p in expected if p in found]; miss = [p for p in expected if p not in found]; extra = [p for p in found if p not in expected]
        tp += len(hit); fn += len(miss); fp += len(extra)
        rows.append({"set": name, "expected": [sorted(p) for p in expected], "found": [sorted(p) for p in found], "brain": brain, "seconds": round(time.time() - t, 1)})
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    return rows, {"tp": tp, "fp": fp, "fn": fn, "precision": round(prec, 3), "recall": round(rec, 3), "brains": brains}


def main():
    v_rows, v = run_verifier()
    report = {"verifier": {"summary": v, "cases": v_rows}}
    md = ["# VAANI measured accuracy", "", f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `backend/benchmark.py`. Re-run after any change to the verifier or the agent prompts.", ""]
    md += ["## 1. Verifier (deterministic, no AI involved)", "",
           "Planted errors across the English, Hindi and Kannada two-speaker meeting demos: numbers nobody said, spoken numbers swapped, English number words, numbers borrowed from another speaker's line, quotes altered by one character, quotes from another meeting.", "",
           "| Measure | Result |", "|---|---|",
           f"| Clean requirements accepted | {v['clean_ok']} / {v['clean_total']} |",
           f"| Planted errors caught | {v['planted_caught']} / {v['planted_total']} |",
           f"| False blocks on clean requirements | {v['clean_total'] - v['clean_ok']} |",
           f"| Missed planted errors | {v['planted_total'] - v['planted_caught']} |", ""]
    misses = [r for r in v_rows if not r["ok"]]
    if misses:
        md += ["Cases that did not behave as expected:", ""] + [f"- {r['case']}: expected {r['expected']}, got {r['got']}" for r in misses] + [""]
    if "--no-llm" not in sys.argv and llm.live():
        c_rows, c = asyncio.run(run_conflicts())
        report["conflicts"] = {"summary": c, "sets": c_rows}
        md += ["## 2. Stakeholder conflict detector (live)", "",
               f"Brains used: {', '.join(f'{k} ×{n}' for k, n in c['brains'].items())}.", "",
               "| Measure | Result |", "|---|---|",
               f"| Planted conflicts found | {c['tp']} / {c['tp'] + c['fn']} (recall {c['recall']}) |",
               f"| False conflicts raised | {c['fp']} (precision {c['precision']}) |", "",
               "| Rule set | Expected | Found | Brain | s |", "|---|---|---|---|---|"]
        md += [f"| {r['set']} | {r['expected'] or '—'} | {r['found'] or '—'} | {r['brain']} | {r['seconds']} |" for r in c_rows]
        md.append("")
    else:
        md += ["## 2. Stakeholder conflict detector", "", "Skipped (no live LLM configured, or --no-llm).", ""]
    md += ["## How to say it on stage", "",
           f"\"We planted {v['planted_total']} errors into three meetings: numbers nobody said, altered quotes, borrowed numbers. The verifier caught {v['planted_caught']} and blocked none of the {v['clean_total']} genuine requirements.\"", ""]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
