"""
fetch_dot_lights_tool.py — the data-fetch tool for the DOT Lights sub-agent.

This is the single tool the sub-agent calls. It reads the pre-aggregated summary
produced by build_dot_lights_data.py and returns a small JSON blob per ZIP,
shaped exactly as the wider app expects:

    {
      "zip_code": "10002",
      "problems": [
        { "problem": "Traffic Signal Condition", "score": 10, "rationale": "..." },
        { "problem": "Street Light Condition",   "score": 7,  "rationale": "..." }
      ]
    }

So every ZIP carries its `zip_code` plus one {problem, score, rationale} entry
per problem type. `score` is a 0-10 integer hotspot score (10 = worst spot in
Manhattan for that problem); `rationale` is a short, fun, data-grounded reason.

Design notes
------------
* Reads the compact summary (dot_lights_data.csv), not the ~15k-row raw export,
  so a lookup is effectively instant.
* Stdlib only (csv, json, argparse, pathlib, re) — no third-party dependencies,
  so there is no supply-chain surface here.
* Usable two ways:
    - as a CLI:      python fetch_dot_lights_tool.py --zip 10002
    - as an import:  from fetch_dot_lights_tool import fetch_dot_lights

Usage:
    python fetch_dot_lights_tool.py --zip 10002    # one ZIP -> single blob
    python fetch_dot_lights_tool.py                # every ZIP -> array of blobs
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

# The summary lives next to this tool. Resolved once, at import time.
DATA_FILE = Path(__file__).resolve().parent / "dot_lights_data.csv"

# A NYC ZIP is exactly five digits. Anchoring the whole string means a value like
# "10002; rm -rf" or "../secrets" can never match — the filter input is validated,
# not just used (defence against injection / path-style abuse via the filter arg).
ZIP_PATTERN = re.compile(r"^\d{5}$")


def _validate_zip(zip_code: str) -> str:
    """Validate a user-supplied ZIP filter at the boundary; fail fast if invalid."""
    zip_code = zip_code.strip()
    if not ZIP_PATTERN.match(zip_code):
        raise ValueError(
            f"Invalid ZIP code '{zip_code}'. "
            f"Expected exactly five digits, e.g. '10002'."
        )
    return zip_code


def fetch_dot_lights(
    zip_code: str | None = None,
    data_file: Path = DATA_FILE,
) -> list[dict]:
    """Return DOT lights facts grouped by ZIP.

    Args:
        zip_code:  Optional 5-digit ZIP to filter to a single area.
        data_file: Path to the summary CSV (defaults to the bundled file).

    Returns:
        A list of per-ZIP blobs, each:
            {"zip_code": str, "problems": [{"problem", "score", "rationale"}, ...]}
        ZIPs are ordered ascending; each ZIP's problems are ordered by score desc.
    """
    # Early validation before any I/O.
    if zip_code is not None:
        zip_code = _validate_zip(zip_code)

    # CWE-22 (Path Traversal): the data file is fixed at import time and resolved
    # to an absolute path, so no user input ever reaches a filesystem path here.
    if not data_file.is_file():
        raise FileNotFoundError(
            f"Data file not found: '{data_file}'. "
            f"Run build_dot_lights_data.py first to generate the summary."
        )

    # Group rows by ZIP while preserving first-seen ZIP order (CSV is ZIP-sorted).
    grouped: dict[str, list[dict]] = {}
    with data_file.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if zip_code is not None and row["zip_code"] != zip_code:
                continue
            grouped.setdefault(row["zip_code"], []).append(
                {
                    "problem": row["problem"],
                    "score": int(row["score"]),
                    "rationale": row["rationale"],
                }
            )

    blobs: list[dict] = []
    for zip_value, problems in grouped.items():
        # Most notable problem (highest score) leads.
        problems.sort(key=lambda p: p["score"], reverse=True)
        blobs.append({"zip_code": zip_value, "problems": problems})

    return blobs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", dest="zip_code", default=None,
                        help="Filter to a single 5-digit ZIP code, e.g. 10002.")
    args = parser.parse_args()

    try:
        results = fetch_dot_lights(zip_code=args.zip_code)
    except (ValueError, FileNotFoundError) as exc:
        # Graceful, actionable failure — no stack trace leaked to the caller.
        raise SystemExit(f"error: {exc}")

    # Contract: a single blob when one ZIP was requested (empty object if the ZIP
    # isn't in the data), otherwise the full array of per-ZIP blobs. The sub-agent
    # parses this JSON directly off stdout.
    if args.zip_code is not None:
        output = results[0] if results else {}
    else:
        output = results

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
