#!/usr/bin/env python3
"""
noise-livability-score

Reads pre-aggregated NYC 311 noise-complaint counts, filters to 2026 Manhattan
zips, and assigns each a relative 0-10 livability score (10 = quietest / most
livable, 0 = loudest). Same shape as rat-livability-score. Stdlib only.

Usage:
    python score.py 10001     # {"Zipcode": "10001", "Score": 6, "Rationale": "..."}
    python score.py           # every Manhattan zip, quietest first (JSON array)
"""
import argparse, csv, json, statistics, sys
from pathlib import Path

TARGET_YEAR = 2026
DATA_FILENAME = "nyc_noise_complaints.csv"
DATA_DIRS = ("synthetic-data", "data")


def find_data_file(explicit):
    if explicit:
        p = Path(explicit)
        if not p.is_file():
            raise FileNotFoundError(f"Data file not found: {p}")
        return p
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        for d in DATA_DIRS:
            c = parent / d / DATA_FILENAME
            if c.is_file():
                return c
    raise FileNotFoundError(f"Could not locate {DATA_FILENAME} in {DATA_DIRS}. Pass --data.")


def load(data_path):
    """Return counts {zip:int} and subtypes {zip:str} for 2026 Manhattan zips."""
    counts, subtypes = {}, {}
    with open(data_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                if int(row["year"]) != TARGET_YEAR or int(row["flag_in_manhattan"]) != 1:
                    continue
                z = str(row["zip_code"]).strip()
                counts[z] = int(str(row["number_complaints"]).replace(",", "").strip())
                subtypes[z] = (row.get("dominant_subtype") or "general").strip()
            except (KeyError, ValueError, TypeError):
                continue
    return counts, subtypes


def score_for(count, all_counts):
    """Percentile rank 0-10; fewer complaints -> higher score (quieter = better)."""
    n = len(all_counts)
    if n <= 1:
        return 10
    louder = sum(1 for c in all_counts if c > count)
    return max(0, min(10, int(louder / (n - 1) * 10 + 0.5)))


def build_rationale(zip_code, count, counts, subtype, score):
    n = len(counts)
    if n <= 1:
        return f"🔇 ZIP {zip_code} logged {count:,} noise complaints in {TARGET_YEAR} with no Manhattan rivals — {score}/10 by default."
    louder = sum(1 for c in counts if c > count)
    quieter = sum(1 for c in counts if c < count)
    median = int(statistics.median(counts))
    if score >= 9:
        vibe, kick = "😴 Blissfully quiet.", "You can actually hear yourself think."
    elif score >= 7:
        vibe, kick = "🙂 Pretty peaceful for Manhattan.", "The odd siren, nothing more."
    elif score >= 4:
        vibe, kick = "🤷 Middle-of-the-road on noise.", "Bring earplugs for the bad nights, you'll be fine."
    elif score >= 2:
        vibe, kick = "😬 It gets loud here.", "Light sleepers, beware."
    else:
        vibe, kick = "🚨 One of Manhattan's loudest.", "A white-noise machine is not optional."
    return (
        f"{vibe} ZIP {zip_code} clocked {count:,} noise complaints in {TARGET_YEAR} — "
        f"{louder} Manhattan zip{'s' if louder != 1 else ''} were louder and {quieter} quieter "
        f"(median: {median:,}); mostly {subtype.lower()} noise. "
        f"Score: {score}/10 (10 = quietest). {kick}"
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description="Noise livability score (0-10) for Manhattan zips.")
    ap.add_argument("zip_code", nargs="?", help="Zip to score; omit for all.")
    ap.add_argument("--data", help="Path to nyc_noise_complaints.csv")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    counts, subtypes = load(find_data_file(args.data))
    if not counts:
        print(json.dumps({"error": "No 2026 Manhattan zips in the dataset."})); return 1
    scores = {z: score_for(c, list(counts.values())) for z, c in counts.items()}

    if args.zip_code is None:
        result = [{"Zipcode": z, "Score": scores[z]}
                  for z in sorted(counts, key=lambda z: (-scores[z], counts[z]))]
        print(json.dumps(result, indent=2, ensure_ascii=False)); return 0

    z = args.zip_code.strip()
    if z not in counts:
        print(json.dumps({"Zipcode": z, "Score": None,
            "Rationale": f"🗺️ ZIP {z} isn't one of the {len(counts)} Manhattan zips in the {TARGET_YEAR} noise data — try a Manhattan one!",
            "error": "Zip code is not a 2026 Manhattan zip code in the dataset."}, ensure_ascii=False)); return 1
    print(json.dumps({"Zipcode": z, "Score": scores[z],
        "Rationale": build_rationale(z, counts[z], list(counts.values()), subtypes[z], scores[z])},
        ensure_ascii=False)); return 0


if __name__ == "__main__":
    sys.exit(main())
