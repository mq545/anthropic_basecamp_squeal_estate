"""
create_dot_lights_subagent.py — create the DOT Lights specialist sub-agent.

This is one specialist in the wider NYC "weird ZIP facts" swarm. Its single lane
is DOT street-light and traffic-signal 311 data for Manhattan. It gets:

- A narrow system prompt (below)
- The agent toolset (file ops + bash, so it can run the fetch tool)
- The `dot-lights-facts` skill (uploaded/attached separately)

The parent coordinator, UI, and wrapper are built by teammates — this script
provisions ONLY this sub-agent and records its ID to .dot_lights_subagent_id
for the coordinator build to pick up later.

Mirrors the pattern in ../create_specialists.py.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python create_dot_lights_subagent.py
"""

import os
from pathlib import Path

from anthropic import Anthropic

# The sub-agent's contract, kept deliberately narrow. The fetch tool and the
# dot-lights-facts skill carry the operational detail; this prompt sets the lane.
DOT_LIGHTS_SYSTEM = """\
You are the DOT Lights specialist in a swarm that gives NYC residents a fun,
weird view of their ZIP code. You own exactly one dataset: NYC 311 complaints
filed against the Department of Transportation for street lights and traffic
signals in Manhattan, 2025.

# Your job

When asked about a ZIP code (or for the whole borough), return a JSON blob keyed
by zip_code, holding one {problem, score, rationale} entry per problem type:

  {
    "zip_code": "10002",
    "problems": [
      { "problem": "Traffic Signal Condition", "score": 10, "rationale": "..." },
      { "problem": "Street Light Condition",   "score": 7,  "rationale": "..." }
    ]
  }

- zip_code:  5-digit Manhattan ZIP, as a string
- problem:   "Traffic Signal Condition" or "Street Light Condition"
- score:     integer 0-10 hotspot score (10 = worst spot in Manhattan for that type)
- rationale: short (<15 word) fun, data-grounded reason for the score

# How to get the data

Use your fetch tool — never read the raw CSV yourself, never invent numbers or
rationales:

  python fetch_dot_lights_tool.py --zip <ZIP>   # one ZIP -> single blob
  python fetch_dot_lights_tool.py               # every ZIP -> array of blobs

Pass the tool's output through unchanged. If a ZIP isn't in the data the tool
returns {}, return that. Follow the dot-lights-facts skill for the full contract.

# Output

Return ONLY the JSON array — no prose, no markdown fences, no commentary. The
parent agent adds the fun phrasing for the UI; your job is clean, trustworthy data.
"""


def main() -> None:
    # CWE-798: the API key comes from the environment, never hardcoded.
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    client = Anthropic(
        api_key=api_key,
        default_headers={"anthropic-beta": "managed-agents-2026-04-01"},
    )

    agent = client.beta.agents.create(
        name="DOT Lights Specialist",
        # Haiku is plenty for a narrow fetch-and-format lane, and keeps the swarm cheap.
        model="claude-haiku-4-5-20251001",
        system=DOT_LIGHTS_SYSTEM,
        tools=[{"type": "agent_toolset_20260401"}],
        metadata={
            "hackathon": "partner-basecamp-2026",
            "track": "specialist-swarm",
            "role": "dot_lights",
            "app": "nyc-weird-zip-facts",
        },
    )

    Path(".dot_lights_subagent_id").write_text(agent.id)
    print(f"Created DOT Lights Specialist -> {agent.id}")
    print("Saved ID to .dot_lights_subagent_id")
    print("\nNext: attach the `dot-lights-facts` skill and register this ID in the")
    print("coordinator's roster (both handled by the coordinator/skill-upload steps).")


if __name__ == "__main__":
    main()
