# Squirrel Charm sub-agent — merge notes

Drop-in specialist for the NYC "weird ZIP facts" swarm. Reports, per Manhattan
ZIP, a 0-10 **Squirrel Charm Score** + four sub-scores + a fun rationale, from
the 2018 Central Park Squirrel Census.

## Files added

```
squirrel_metric.py                     # build tool: census CSV -> per-ZIP scores (one-off data-prep)
data/manhattan_zips.geojson            # cached Manhattan MODZCTA boundaries (for the build)
synthetic-data/2018_Central_Park_Squirrel_Census.csv   # the source dataset
outputs/squirrel_metric.json           # the built artifact
create_squirrel_subagent.py            # provisions the sub-agent, writes .squirrel_subagent_id
skills/squirrel-charm/
├── SKILL.md                           # the skill (what upload_skills.py packages)
├── fetch_squirrel_tool.py             # the agent's one runtime tool (stdlib only)
└── squirrel_metric.json               # pre-aggregated scores the tool serves
```

The tool + data live **inside** the skill directory on purpose: `upload_skills.py`
packages a skill with `files_from_dir(skill_dir)`, so they upload as one
self-contained bundle. `fetch_squirrel_tool.py` resolves its data file relative
to `__file__`, so it runs correctly wherever the bundle is mounted.

## What the sub-agent returns

Single ZIP (`--zip 10024`):

```json
{
  "zip_code": "10024",
  "score": 6,
  "sub_scores": { "abundance": 8, "friendliness": 7, "playfulness": 3, "rarity": 3 },
  "sightings": 383,
  "rationale": "6/10 — high squirrel abundance, high friendliness, modest play activity, and 7 rare black-squirrel sightings."
}
```

No `--zip` returns an array of these blobs, one per Manhattan ZIP. ZIPs outside
Central Park's reach are flagged `"no_data": true` (score 0) — show them as "no
data", not "zero charm".

## The score

Headline `score` = weighted blend (default 0.40/0.30/0.20/0.10) of four integer
0-10 sub-scores:

- **abundance** — how many squirrels (sighting density)
- **friendliness** — approaches vs. runs-from rate
- **playfulness** — running / chasing / climbing rate
- **rarity** — black-squirrel rate

Tune the blend in `WEIGHTS` at the top of `squirrel_metric.py`.

## Two wiring changes to merge

1. **Attach the skill** — in `upload_skills.py`, add to `SKILL_TO_SPECIALIST`:

   ```python
   "squirrel-charm": "squirrel",
   ```

   and make sure the `squirrel` key exists in `.specialist_ids.json` (fold in the
   ID from `.squirrel_subagent_id`).

2. **Register the agent** — run `python create_squirrel_subagent.py` (writes
   `.squirrel_subagent_id`), then add that ID to the coordinator's
   `multiagent.agents` roster in `create_coordinator.py`.

## Coverage caveat (important)

Every census sighting is inside Central Park, which is a population "hole" in ZIP
boundaries. `squirrel_metric.py` snaps park-interior sightings to the nearest
bordering ZIP, so the metric only lights up the ~11 ZIPs around the park (10023,
10024, 10025, 10019, 10065, 10021, 10075, 10026, 10028, 10029, 10128). Read the
score as *proximity to Central Park squirrel life*, not a park-independent trait.

## Regenerating the data (optional)

`outputs/squirrel_metric.json` (and the bundled copy) are pre-built and committed.
To rebuild from the raw census after tuning weights:

```bash
python squirrel_metric.py
```

Pure stdlib — no extra dependencies, no API key needed.
