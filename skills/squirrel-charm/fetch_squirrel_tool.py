"""
fetch_squirrel_tool.py — the Squirrel Charm specialist's one runtime tool.

Serves the precomputed Squirrel Charm Score for Manhattan ZIPs. The agent calls
this instead of ever reading the raw census — the numbers are already computed
(deterministically) by ../../squirrel_metric.py and saved next to this file.

Stdlib only. Resolves its data file relative to __file__, so it runs wherever the
skill bundle is mounted.

Usage:
    python fetch_squirrel_tool.py --zip 10024   # one ZIP  -> single blob (or {} if absent)
    python fetch_squirrel_tool.py               # all ZIPs -> array of blobs
"""

import argparse
import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "squirrel_metric.json"


def load_records() -> list:
    return json.loads(DATA_PATH.read_text())["data"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Squirrel Charm Scores by ZIP.")
    parser.add_argument("--zip", dest="zip_code", help="5-digit Manhattan ZIP")
    args = parser.parse_args()

    records = load_records()
    if args.zip_code:
        match = next((r for r in records if r["zip_code"] == args.zip_code), {})
        print(json.dumps(match, indent=2))
    else:
        print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
