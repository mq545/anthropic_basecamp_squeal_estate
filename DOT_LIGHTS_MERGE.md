# DOT Lights sub-agent — merge notes

Drop-in specialist for the NYC "weird ZIP facts" swarm. Reports, per Manhattan
ZIP, a 0-10 hotspot score + a fun rationale for DOT street-light and
traffic-signal 311 complaints.

## Files added

```
create_dot_lights_subagent.py          # provisions the sub-agent, writes .dot_lights_subagent_id
skills/dot-lights-facts/
├── SKILL.md                           # the skill (what upload_skills.py packages)
├── fetch_dot_lights_tool.py           # the agent's one tool (stdlib only)
└── dot_lights_data.csv                # pre-aggregated data the tool serves
```

The tool + data live **inside** the skill directory on purpose: `upload_skills.py`
packages a skill with `files_from_dir(skill_dir)`, so they upload as one
self-contained bundle. `fetch_dot_lights_tool.py` resolves its data file relative
to `__file__`, so it runs correctly wherever the bundle is mounted.

## What the sub-agent returns

Single ZIP (`--zip 10002`):

```json
{
  "zip_code": "10002",
  "problems": [
    { "problem": "Traffic Signal Condition", "score": 10, "rationale": "No ZIP breaks more traffic lights — 415 complaints and endless honking." },
    { "problem": "Street Light Condition",   "score": 7,  "rationale": "271 complaints logged; someone keeps forgetting to change the bulbs." }
  ]
}
```

No `--zip` returns an array of these blobs, one per ZIP.

## Two wiring changes to merge

1. **Attach the skill** — in `upload_skills.py`, add to `SKILL_TO_SPECIALIST`:

   ```python
   "dot-lights-facts": "dot_lights",
   ```

   and make sure the `dot_lights` key exists in `.specialist_ids.json` (step 2).

2. **Register the agent** — run `python create_dot_lights_subagent.py` (writes
   `.dot_lights_subagent_id`), then add that ID to the coordinator's
   `multiagent.agents` roster in `create_coordinator.py`, and fold `dot_lights`
   into `.specialist_ids.json` so `upload_skills.py` can find it.

## Regenerating the data (optional)

`dot_lights_data.csv` is pre-built and committed. To rebuild it from the raw
export, use `build_dot_lights_data.py` from `specialist-swarm/dot_lights_subagent/`
(not copied here — it's a one-off data-prep step, not needed at runtime).
