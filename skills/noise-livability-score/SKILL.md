---
name: noise-livability-score
description: Compute a 0-10 noise-based livability score for a Manhattan NYC zip code from NYC 311 noise complaints — the kind of thing Zillow won't tell you. Use when the user gives a Manhattan zip code and wants to know how quiet/livable it is. Ranks each zip by noise-complaint volume relative to the others and returns JSON {"Zipcode": <zip>, "Score": <int 0-10>, "Rationale": <plain-English explanation>} where 10 = quietest (most livable) and 0 = loudest.
---

# Noise Livability Score

Turns raw NYC 311 noise-complaint counts into a single relative livability score
(0–10) for a Manhattan zip. Higher is better (quieter). Mirrors the
rat-livability-score contract so the swarm's scores are directly comparable.

## When to use
The user gives a Manhattan zip and wants to know how noisy/livable it is. This
skill compares that zip against every other Manhattan zip.

## How the score works
1. **Filter** the data to 2026 Manhattan zips.
2. **Rank** every zip by total noise complaints (more complaints = louder = worse).
3. **Score** by percentile rank → int 0–10: fewest complaints → **10** (quietest),
   most → **0** (loudest). Relative, so it's robust to the data's heavy right-skew.

## How to run
`score.py` (Python 3, stdlib only). Data auto-detected from `synthetic-data/`.
```bash
python skills/noise-livability-score/score.py 10001   # one zip
python skills/noise-livability-score/score.py          # every Manhattan zip (JSON array)
```
Call the tool — do not read the CSV yourself or invent numbers.

## Output contract (the swarm standard — see SCHEMA.md)
Single zip:
```json
{"Zipcode": "10069", "Score": 10, "Rationale": "😴 Blissfully quiet. ZIP 10069 clocked 100 noise complaints in 2026 …"}
```
All zips: JSON array of `{"Zipcode", "Score"}`, quietest first.
Non-Manhattan zip → `{"Zipcode", "Score": null, "Rationale", "error"}`.

Surface the `Rationale` verbatim so the number lands with personality.

## Interpreting the score
- **8–10** — quiet for Manhattan; among the more livable zips.
- **4–7** — middle of the pack.
- **0–3** — loud relative to the rest of Manhattan.
