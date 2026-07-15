#!/usr/bin/env python3
"""
rat-livability-score

Reads NYC rodent-inspection data, filters to the most recent year (2026) and
Manhattan zip codes (flag_in_manhattan == 1), and assigns each Manhattan zip a
relative "livability" score from 0 to 10 based on how many rat inspections it
had compared to the other Manhattan zips.

Scoring (percentile rank):
    For a given zip:
        score_fraction = (# Manhattan zips with MORE inspections)
                         / (total Manhattan zips - 1)
        score = round(score_fraction * 10), clamped to [0, 10]

    -> The zip with the FEWEST inspections scores 10 (most livable, fewest rats)
    -> The zip with the MOST inspections scores 0  (least livable, most rats)
    -> Zips with equal inspection counts receive the same score.

Only standard library is used (no pandas), so it runs anywhere Python 3 does.

Usage:
    python score.py 10001          # one zip  -> {"Zipcode": "10001", "Score": 5}
    python score.py                # every Manhattan zip, best first (JSON array)
    python score.py 10001 --data path/to/nyc_rodent_inspections.csv
"""

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

TARGET_YEAR = 2026
DATA_FILENAME = "nyc_rodent_inspections.csv"
# Folder(s) the CSV might live in, checked in order. Add names here if the data
# moves to another directory; the --data flag always overrides this.
DATA_DIRS = ("synthetic-data", "data")


def find_data_file(explicit):
    """Locate the CSV: use --data if given, else walk up looking in DATA_DIRS."""
    if explicit:
        p = Path(explicit)
        if not p.is_file():
            raise FileNotFoundError(f"Data file not found: {p}")
        return p
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        for data_dir in DATA_DIRS:
            candidate = parent / data_dir / DATA_FILENAME
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(
        f"Could not locate {DATA_FILENAME} in any of {DATA_DIRS}. "
        "Pass --data explicitly."
    )


def parse_count(raw):
    """Parse an inspection count that may use thousands separators, e.g. '1,484'."""
    return int(str(raw).replace(",", "").strip())


def load_manhattan_zips(data_path):
    """Return {zip_code(str): inspections(int)} for TARGET_YEAR Manhattan zips."""
    zips = {}
    with open(data_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                year = int(row["year"])
                in_manhattan = int(row["flag_in_manhattan"])
            except (KeyError, ValueError, TypeError):
                continue
            if year != TARGET_YEAR or in_manhattan != 1:
                continue
            zip_code = str(row["zip_code"]).strip()
            try:
                zips[zip_code] = parse_count(row["number_inspections"])
            except (KeyError, ValueError, TypeError):
                continue
    return zips


def score_for(inspections, all_counts):
    """Percentile-rank score 0-10; fewer inspections -> higher score."""
    n = len(all_counts)
    if n <= 1:
        return 10
    more = sum(1 for c in all_counts if c > inspections)
    fraction = more / (n - 1)
    score = int(fraction * 10 + 0.5)  # round half up
    return max(0, min(10, score))


def all_scores(zips):
    counts = list(zips.values())
    return {z: score_for(c, counts) for z, c in zips.items()}


def _fmt_num(n):
    """Format a number for prose: '1,484' for whole values, '~117' otherwise."""
    if float(n).is_integer():
        return f"{int(n):,}"
    return f"~{round(n):,}"


def build_rationale(zip_code, inspections, counts, score):
    """A fun, rat-themed explanation of the score — playful in tone, but every
    number in it is pulled straight from the data (no made-up stats)."""
    n = len(counts)
    insp_word = "inspection" if inspections == 1 else "inspections"
    if n <= 1:
        return (
            f"🐀 ZIP {zip_code} is a party of one! It logged {inspections:,} rat {insp_word} "
            f"in {TARGET_YEAR} with zero Manhattan rivals to size it up against, so it waltzes "
            f"off with {score}/10 by default. Lonely at the top."
        )

    more = sum(1 for c in counts if c > inspections)
    fewer = sum(1 for c in counts if c < inspections)
    median = statistics.median(counts)

    if score >= 9:
        vibe = "🏆 Rat royalty! Barely a whisker in sight."
        kicker = "You could (almost) eat off the sidewalk. Please don't, but you could."
    elif score >= 7:
        vibe = "😎 Pretty breezy on the rodent front."
        kicker = "The rats mostly RSVP'd 'no' to this block."
    elif score >= 4:
        vibe = "🤷 Solidly middle-of-the-road, ratwise."
        kicker = "Not a nightmare, not a dream — just bring your normal shoes."
    elif score >= 2:
        vibe = "😬 The rats are getting a little too comfortable here."
        kicker = "Might be time to befriend a local cat."
    else:
        vibe = "🚨 Rat metropolis! The rodents have basically unionized."
        kicker = "A very... lively neighborhood. Consider bringing two cats."

    worse = f"{more} Manhattan zip{'s' if more != 1 else ''} had it worse"
    better = f"{fewer} had it better"
    return (
        f"{vibe} ZIP {zip_code} clocked {inspections:,} rat {insp_word} in {TARGET_YEAR} — "
        f"{worse} and {better} (Manhattan median: {_fmt_num(median)}). "
        f"Final score: {score}/10 (10 = fewest rats). {kicker}"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Rat-based livability score (0-10) for Manhattan NYC zip codes."
    )
    parser.add_argument(
        "zip_code",
        nargs="?",
        help="Zip code to score. Omit to score every Manhattan zip.",
    )
    parser.add_argument(
        "--data",
        help="Path to nyc_rodent_inspections.csv (auto-detected if omitted).",
    )
    args = parser.parse_args(argv)

    # Emojis in the rationale need a UTF-8 stdout (Windows consoles default to
    # cp1252 and would otherwise choke).
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    data_path = find_data_file(args.data)
    zips = load_manhattan_zips(data_path)

    if not zips:
        print(json.dumps({"error": "No 2026 Manhattan zip codes found in the dataset."}))
        return 1

    scores = all_scores(zips)

    if args.zip_code is None:
        # Full ranking, most livable (highest score, then fewest inspections) first.
        result = [
            {"Zipcode": z, "Score": scores[z]}
            for z in sorted(zips, key=lambda z: (-scores[z], zips[z]))
        ]
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    zip_code = args.zip_code.strip()
    if zip_code not in zips:
        print(json.dumps({
            "Zipcode": zip_code,
            "Score": None,
            "Rationale": (
                f"🗺️ ZIP {zip_code} isn't one of the {len(zips)} Manhattan zip codes in the "
                f"{TARGET_YEAR} data, so the rats there stay a mystery. This skill only sniffs "
                "out Manhattan zips — try a Manhattan one!"
            ),
            "error": "Zip code is not a 2026 Manhattan zip code in the dataset.",
        }, ensure_ascii=False))
        return 1

    score = scores[zip_code]
    rationale = build_rationale(zip_code, zips[zip_code], list(zips.values()), score)
    print(json.dumps(
        {"Zipcode": zip_code, "Score": score, "Rationale": rationale},
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
