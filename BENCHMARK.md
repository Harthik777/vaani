# VAANI measured accuracy

Generated 2026-10-17 14:13 by `backend/benchmark.py`. Re-run after any change to the verifier or the agent prompts.

## 1. Verifier (deterministic, no AI involved)

Planted errors across the English, Hindi and Kannada two-speaker meeting demos: numbers nobody said, spoken numbers swapped, English number words, numbers borrowed from another speaker's line, quotes altered by one character, quotes from another meeting.

| Measure | Result |
|---|---|
| Clean requirements accepted | 24 / 24 |
| Planted errors caught | 66 / 66 |
| False blocks on clean requirements | 0 |
| Missed planted errors | 0 |

## 2. Stakeholder conflict detector (live)

Brains used: sarvam:sarvam-105b-conversations ×11.

| Measure | Result |
|---|---|
| Planted conflicts found | 7 / 7 (recall 1.0) |
| False conflicts raised | 0 (precision 1.0) |

| Rule set | Expected | Found | Brain | s |
|---|---|---|---|---|
| meeting english (owner 50 kg vs manager 100 kg) | [['r1', 'r4']] | [['r1', 'r4']] | sarvam:sarvam-105b-conversations | 0.6 |
| meeting english without the manager's threshold | — | — | sarvam:sarvam-105b-conversations | 0.5 |
| meeting hindi (owner 50 kg vs manager 100 kg) | [['r1', 'r4']] | [['r1', 'r4']] | sarvam:sarvam-105b-conversations | 0.6 |
| meeting hindi without the manager's threshold | — | — | sarvam:sarvam-105b-conversations | 0.4 |
| meeting kannada (owner 50 kg vs manager 100 kg) | [['r1', 'r4']] | [['r1', 'r4']] | sarvam:sarvam-105b-conversations | 0.6 |
| meeting kannada without the manager's threshold | — | — | sarvam:sarvam-105b-conversations | 0.4 |
| delivery days | [['r1', 'r2']] | [['r1', 'r2']] | sarvam:sarvam-105b-conversations | 0.5 |
| budget and approver | [['r1', 'r2'], ['r3', 'r4']] | [['r1', 'r2'], ['r3', 'r4']] | sarvam:sarvam-105b-conversations | 0.6 |
| related but not contradictory | — | — | sarvam:sarvam-105b-conversations | 0.4 |
| same speaker, different numbers (not a stakeholder conflict) | — | — | sarvam:sarvam-105b-conversations | 0.4 |
| credit period | [['r1', 'r2']] | [['r1', 'r2']] | sarvam:sarvam-105b-conversations | 0.5 |

## How to say it on stage

"We planted 66 errors into three meetings: numbers nobody said, altered quotes, borrowed numbers. The verifier caught 66 and blocked none of the 24 genuine requirements."
