"""
create_squirrel_subagent.py — create the Squirrel Charm specialist sub-agent.

One specialist in the NYC "weird ZIP facts" swarm. Its single lane is squirrel
delight per Manhattan ZIP, from the 2018 Central Park Squirrel Census. It gets:

- A narrow system prompt (below)
- The agent toolset (file ops + bash, so it can run the fetch tool)
- The `squirrel-charm` skill (uploaded/attached separately)

The parent coordinator, UI, and wrapper are built by teammates — this script
provisions ONLY this sub-agent and records its ID to .squirrel_subagent_id for
the coordinator build to pick up later.

Mirrors the pattern in create_dot_lights_subagent.py / create_specialists.py.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python create_squirrel_subagent.py
"""

import os
from pathlib import Path

from anthropic import Anthropic

# The sub-agent's contract, kept deliberately narrow. The fetch tool and the
# squirrel-charm skill carry the operational detail; this prompt sets the lane.
SQUIRREL_SYSTEM = """\
You are the Squirrel Charm specialist in a swarm that gives NYC residents a fun,
weird view of their ZIP code. You own exactly one dataset: the 2018 Central Park
Squirrel Census, scored into a "Squirrel Charm Score" per Manhattan ZIP.

# Your job

When asked about a ZIP code (or for the whole borough), return a JSON blob keyed
by zip_code, holding the charm score, its sub-scores, and a rationale:

  {
    "zip_code": "10024",
    "score": 6,
    "sub_scores": { "abundance": 8, "friendliness": 7, "playfulness": 3, "rarity": 3 },
    "sightings": 383,
    "rationale": "6/10 — high squirrel abundance, high friendliness, ..."
  }

- zip_code:   5-digit Manhattan ZIP, as a string
- score:      integer 0-10 headline Squirrel Charm Score
- sub_scores: four integer 0-10 signals (abundance, friendliness, playfulness, rarity)
- rationale:  short, data-grounded reason for the score

# How to get the data

Use your fetch tool — never read the raw census yourself, never invent numbers or
rationales:

  python fetch_squirrel_tool.py --zip <ZIP>   # one ZIP -> single blob
  python fetch_squirrel_tool.py               # every ZIP -> array of blobs

Pass the tool's output through unchanged. Every census sighting is inside Central
Park, so only park-adjacent ZIPs are scored; ZIPs marked "no_data": true have no
coverage — report them as "no squirrel data", never as zero charm. Follow the
squirrel-charm skill for the full contract.

# Output

Return ONLY the JSON — no prose, no markdown fences, no commentary. The parent
agent adds the fun phrasing for the UI; your job is clean, trustworthy data.
"""


def main() -> None:
    # The API key comes from the environment, never hardcoded.
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    client = Anthropic(
        api_key=api_key,
        default_headers={"anthropic-beta": "managed-agents-2026-04-01"},
    )

    agent = client.beta.agents.create(
        name="Squirrel Charm Specialist",
        # Haiku is plenty for a narrow fetch-and-format lane, and keeps the swarm cheap.
        model="claude-haiku-4-5-20251001",
        system=SQUIRREL_SYSTEM,
        tools=[{"type": "agent_toolset_20260401"}],
        metadata={
            "hackathon": "partner-basecamp-2026",
            "track": "specialist-swarm",
            "role": "squirrel",
            "app": "nyc-weird-zip-facts",
        },
    )

    Path(".squirrel_subagent_id").write_text(agent.id)
    print(f"Created Squirrel Charm Specialist -> {agent.id}")
    print("Saved ID to .squirrel_subagent_id")
    print("\nNext: attach the `squirrel-charm` skill and register this ID in the")
    print("coordinator's roster (see SQUIRREL_MERGE.md).")


if __name__ == "__main__":
    main()
