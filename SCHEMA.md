# Squeal Estate — shared agent output contract

Every specialist emits the **same shape** so the coordinator/UI can merge all
agents by joining on zip. Standardised on the `rat-livability-score` shape.

## The contract

**Single zip:**
```json
{ "Zipcode": "10002", "Score": 7, "Rationale": "one fun, data-grounded sentence" }
```

**All zips** (no zip arg) — a JSON array, best (highest score) first:
```json
[ { "Zipcode": "10069", "Score": 10 }, { "Zipcode": "10032", "Score": 0 } ]
```

**Unknown / non-Manhattan zip:**
```json
{ "Zipcode": "10301", "Score": null, "Rationale": "…", "error": "…" }
```

## Rules (all agents)
- Keys are **capitalised**: `Zipcode` (string), `Score` (int), `Rationale` (string).
- `Score` is an **integer 0–10** where **10 = best / most livable** for *every* metric
  (fewest rats, quietest, fewest problems). Higher is always better — so the UI can
  average scores across agents directly, no per-agent direction flag needed.
- Each agent ships as a skill dir with a stdlib `score.py`/tool + its pre-aggregated
  CSV in `synthetic-data/`; the tool prints the JSON above. Wire via
  `SKILL_TO_SPECIALIST` in `upload_skills.py` + a specialist in the roster.

## Status
| Agent | Skill dir | Conforms? |
|---|---|---|
| Rats (Harry) | `rat-livability-score` | ✅ (this is the standard) |
| Noise (Mike) | `noise-livability-score` | ✅ |
| DOT lights (Liam) | `dot-lights-facts` | ⚠️ needs flip: lowercase→`Zipcode/Score/Rationale`, collapse `problems[]`→one `Score`, invert to **10 = fewest problems (best)** |
