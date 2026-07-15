#!/usr/bin/env python3
"""Maintainer tool — regenerates `cop_data_by_zip.csv` from the raw CCRB data.

This is NOT run at agent runtime. The cop specialist just reads the CSV this
produces. Re-run it only when the source data in the repo's `cop_data/` changes:

    python3 build_cop_data_csv.py

It joins NYC CCRB civilian-complaint records to a precinct->ZIP mapping and
writes one row per Manhattan ZIP with the raw ingredients the agent needs to
score it (complaint volume, high-force %, substantiated %, and a severity index).
"""
import csv
import os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COP_DATA = os.path.join(SCRIPT_DIR, "..", "..", "cop_data")
CCRB = os.path.join(COP_DATA,
    "Civilian_Complaint_Review_Board__Complaints_Against_Police_Officers_20260715.csv")
MAPPING = os.path.join(COP_DATA, "nyc_precinct_to_zipcode.csv")
OUT = os.path.join(SCRIPT_DIR, "cop_data_by_zip.csv")
BOROUGH = "Manhattan"

# Arrests where physical force was clearly exchanged.
HIGH_FORCE = {
    "Arrest - OGA",
    "Arrest - resisting arrest",
    "Arrest - disorderly/OGA/resisting",
    "Arrest - assault (against a PO)",
    "Arrest - harrassment (against a PO)",
}


def severity(row):
    outcome = row["Outcome Of Police Encounter"]
    if outcome in HIGH_FORCE:
        s = 3
    elif outcome.startswith("Arrest"):
        s = 2
    else:
        s = 1
    if row["CCRB Complaint Disposition"].startswith("Substantiated"):
        s += 1
    return s


def main():
    # precinct -> ZIPs it serves (many-to-many)
    precinct_to_zips = defaultdict(set)
    with open(MAPPING, newline="") as f:
        for row in csv.DictReader(f):
            if row["Borough"] == BOROUGH:
                precinct_to_zips[row["Precinct"]].add(row["Zip Code"])

    # per-precinct tallies
    p_sev = defaultdict(int)     # summed severity (frequency x viciousness)
    p_total = defaultdict(int)   # complaint count
    p_force = defaultdict(int)   # high-force arrests
    p_subst = defaultdict(int)   # substantiated (confirmed misconduct)
    with open(CCRB, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["Borough Of Incident Occurrence"] != BOROUGH:
                continue
            precinct = row["Precinct Of Incident Occurrence"].lstrip("0")
            if not precinct:
                continue
            p_sev[precinct] += severity(row)
            p_total[precinct] += 1
            if row["Outcome Of Police Encounter"] in HIGH_FORCE:
                p_force[precinct] += 1
            if row["CCRB Complaint Disposition"].startswith("Substantiated"):
                p_subst[precinct] += 1

    # invert to ZIP -> precinct(s) that serve it (only precincts we have data for)
    zip_to_precincts = defaultdict(list)
    for precinct, zips in precinct_to_zips.items():
        if precinct in p_sev:
            for z in zips:
                zip_to_precincts[z].append(precinct)

    # aggregate to ZIP across the precinct(s) serving it
    rows = []
    for zip_code, precincts in zip_to_precincts.items():
        precincts.sort(key=lambda p: -p_total[p])
        total = sum(p_total[p] for p in precincts)
        force = sum(p_force[p] for p in precincts)
        subst = sum(p_subst[p] for p in precincts)
        severity_index = round(sum(p_sev[p] for p in precincts) / len(precincts))
        rows.append({
            "zip_code": zip_code,
            "precincts": " ".join(precincts),
            "total_complaints": total,
            "high_force_arrests": force,
            "high_force_pct": round(100 * force / total) if total else 0,
            "substantiated": subst,
            "substantiated_pct": round(100 * subst / total) if total else 0,
            "severity_index": severity_index,
        })

    rows.sort(key=lambda r: (-r["severity_index"], r["zip_code"]))
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} {BOROUGH} ZIP rows -> {OUT}")


if __name__ == "__main__":
    main()
