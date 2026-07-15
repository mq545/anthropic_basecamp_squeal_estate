---
name: rat-livability-score
description: Compute a 0-10 rat-based livability score for a Manhattan NYC zip code from NYC rodent-inspection data — the kind of thing Zillow won't tell you. Use when the user gives a NYC/Manhattan zip code and wants to know how livable it is with respect to rats. Filters the data to 2026 and Manhattan zips, ranks each zip by inspection count relative to the others, and returns JSON {"Zipcode": <zip>, "Score": <int 0-10>, "Rationale": <plain-English explanation>} where 10 = fewest rats (most livable) and 0 = most rats (least livable).
---

# Rat Livability Score

Turns raw NYC rodent-inspection counts into a single relative livability score
(0–10) for a Manhattan zip code. Higher is better (fewer rats).

## When to use

The user has entered a NYC zip code and wants to know how "livable" it is based
on rat activity. This skill compares that zip against the other Manhattan zips.

## How the score works

1. **Filter** the dataset to the most recent year (`year == 2026`) and Manhattan
   only (`flag_in_manhattan == 1`).
2. **Rank** every Manhattan zip by `number_inspections` (more inspections = more
   rats = worse).
3. **Score** each zip by percentile rank, mapped to an integer 0–10:
   - `score_fraction = (# Manhattan zips with MORE inspections) / (total Manhattan zips − 1)`
   - `score = round(score_fraction × 10)`, clamped to `[0, 10]`
   - Fewest inspections → **10** (most livable). Most inspections → **0** (least livable).
   - Zips with the same inspection count get the same score.

This is a *relative* score: it answers "how does this zip compare to the rest of
Manhattan?", which is robust to the data's heavy right-skew (a few zips have
thousands of inspections while most have under a few hundred).

## How to run

The scoring is done by `score.py` (Python 3, standard library only — no
dependencies). The data file is auto-detected by walking up to a `synthetic-data/`
or `data/` folder.

```bash
# Score one zip -> {"Zipcode": "10001", "Score": 5}
python .claude/skills/rat-livability-score/score.py 10001

# Score every Manhattan zip, most livable first (JSON array)
python .claude/skills/rat-livability-score/score.py

# Point at a specific data file if needed
python .claude/skills/rat-livability-score/score.py 10001 --data synthetic-data/nyc_rodent_inspections.csv
```

## Output contract

On success, the script prints the zip, its 0–10 score, and a fun, rat-themed
`Rationale`. The tone is playful, but every number in it is pulled straight from
the data (the zip's actual inspection count, how many Manhattan zips had it
worse/better, and the Manhattan median):

```json
{
  "Zipcode": "10001",
  "Score": 4,
  "Rationale": "🤷 Solidly middle-of-the-road, ratwise. ZIP 10001 clocked 406 rat inspections in 2026 — 17 Manhattan zips had it worse and 28 had it better (Manhattan median: 249). Final score: 4/10 (10 = fewest rats). Not a nightmare, not a dream — just bring your normal shoes."
}
```

The single-zip output always includes `Rationale` — surface it to the user
verbatim alongside the score so the number lands with some personality, not bare.
The opener and closing quip vary by score band (🏆 rat royalty → 🚨 rat metropolis).

If the zip is not a 2026 Manhattan zip in the dataset (e.g. an outer-borough zip
or an unknown zip), it prints a `null` score plus a (still-fun) `Rationale` and
an `error`, so the agent can tell the user this skill only covers Manhattan:

```json
{"Zipcode": "10301", "Score": null, "Rationale": "🗺️ ZIP 10301 isn't one of the 46 Manhattan zip codes in the 2026 data, so the rats there stay a mystery. This skill only sniffs out Manhattan zips — try a Manhattan one!", "error": "Zip code is not a 2026 Manhattan zip code in the dataset."}
```

The full-ranking mode (`score.py` with no zip) stays lean — `{"Zipcode", "Score"}`
per entry — so the overview table remains scannable.

## Interpreting the score for the user

- **8–10** — relatively few rat inspections for Manhattan; among the more livable zips.
- **4–7** — middle of the pack.
- **0–3** — high rat activity relative to the rest of Manhattan.
