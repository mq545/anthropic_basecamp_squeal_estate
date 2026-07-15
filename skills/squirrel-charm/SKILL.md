---
name: squirrel-charm
description: Squirrel Charm Score for Manhattan by ZIP code — a "what Zillow won't tell you" nature/wildlife metric built from the 2018 Central Park Squirrel Census. Use whenever a question touches how nice, green, or lively an area is for park wildlife, squirrel activity, or Central Park proximity for a given Manhattan ZIP. Trigger on any request about squirrels, park life, nature charm, or the squirrel_charm_score for a neighborhood or ZIP.
---

# Squirrel Charm Score

A fun, hyperlocal metric answering: **"how delightful is the squirrel life near this apartment?"** — scored per Manhattan ZIP on a **0–10 integer** scale.

## How to answer questions

Use the bundled **`fetch_squirrel_tool.py`** to get the numbers — never recount the raw census yourself, never invent scores or rationales:

```bash
python fetch_squirrel_tool.py --zip 10024   # one ZIP  -> single blob (or {} if absent)
python fetch_squirrel_tool.py               # all ZIPs -> array of blobs
```

Pass the tool's output through unchanged. Each ZIP record has a headline `score`, the four `sub_scores` that feed it, the `sightings` count, and a plain-English `rationale`. When asked "why?", quote the `sub_scores` and `rationale`. (The tool reads the precomputed, authoritative `squirrel_metric.json` bundled alongside it.)

To regenerate the scores from source (e.g. after tuning weights), run the build tool at the repo root — a one-off data-prep step, not needed at runtime:

```bash
python squirrel_metric.py   # rewrites outputs/squirrel_metric.json + refreshes this bundle's copy
```

## The score (0–10) and its four sub-scores (each 0–10)

The headline `score` is a weighted blend of four sub-scores, each min-max normalized across the scored ZIPs:

| Sub-score | What it measures | Source signal |
| --- | --- | --- |
| **abundance** | how many squirrels you'll encounter | sighting count per ZIP |
| **friendliness** | squirrels that approach vs. flee humans | `Approaches` − `Runs from` rate |
| **playfulness** | running / chasing / climbing antics | share of playful behaviors |
| **rarity** | rare black-squirrel bragging rights | black-fur sighting rate |

Default weights (tunable in `WEIGHTS` at the top of `squirrel_metric.py`): abundance 0.40, friendliness 0.30, playfulness 0.20, rarity 0.10.

## Output contract (shared across the swarm)

```json
{
  "metric": "squirrel_charm_score",
  "unit": "0-10",
  "source": "2018 Central Park Squirrel Census",
  "data": [
    {
      "zip_code": "10023",
      "score": 8,
      "sub_scores": { "abundance": 10, "friendliness": 8, "playfulness": 6, "rarity": 2 },
      "sightings": 502,
      "rationale": "8/10 — exceptional squirrel abundance, high friendliness ..."
    },
    { "zip_code": "10001", "score": 0, "sub_scores": {"abundance":0,...},
      "sightings": 0, "no_data": true, "rationale": "No squirrel census data (outside Central Park)." }
  ]
}
```

All scores and sub-scores are **integers 0–10**.

## Important coverage caveat (state this when relevant)

Every census sighting is inside **Central Park**, which is a population "hole" in ZIP-code boundaries. Sightings are therefore **snapped to the nearest bordering ZIP** — so the metric only lights up the ~11 ZIPs around the park (e.g. 10023, 10024, 10025, 10019, 10065, 10028, 10021). All other Manhattan ZIPs are flagged `"no_data": true` with `score: 0` and should be shown as "no data," **not** as "zero charm." Interpret the score as *proximity to Central Park squirrel life*, not a park-independent property of the ZIP.
