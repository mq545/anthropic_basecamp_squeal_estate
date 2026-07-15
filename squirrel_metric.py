"""
Squirrel Charm Score — the "squirrel" specialist's data tool for the swarm.

Turns the 2018 Central Park Squirrel Census (lat/long point data, no ZIP) into a
per-Manhattan-ZIP metric that answers: "how delightful is the squirrel life near
this apartment?"

It is DETERMINISTIC on purpose — an LLM eyeballing 3,000+ rows to count-by-ZIP
would hallucinate. The swarm agent's job is to *serve and explain* this JSON, not
to recompute it. Runs with zero API key.

Pipeline:
  1. Read the census CSV.
  2. Spatially join each sighting to a Manhattan ZIP via pure-Python
     point-in-polygon (ray casting) against a cached MODZCTA GeoJSON. No shapely.
  3. Compute 4 sub-scores + a weighted headline score, each an INTEGER 0-10.
  4. Template a human-readable rationale per ZIP (the "why").
  5. Write outputs/squirrel_metric.json in the team contract shape.

Usage:
    python squirrel_metric.py
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# YOUR DIAL — the "fun" part. These four weights decide the metric's
# personality: is squirrel charm mostly about how MANY squirrels you'll see,
# how FRIENDLY they are, how PLAYFUL, or how RARE (black squirrels)? They only
# need to be positive; they're normalized to sum to 1 automatically. Tune away.
# ---------------------------------------------------------------------------
WEIGHTS = {
    "abundance": 0.40,     # how many squirrels you'll encounter
    "friendliness": 0.30,  # squirrels that approach vs. run from you
    "playfulness": 0.20,   # running / chasing / climbing antics
    "rarity": 0.10,        # rare black-squirrel bragging rights
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
CSV_PATH = BASE / "synthetic-data" / "2018_Central_Park_Squirrel_Census.csv"
GEOJSON_PATH = BASE / "data" / "manhattan_zips.geojson"
OUTPUT_PATH = BASE / "outputs" / "squirrel_metric.json"
# The skill bundle serves its own copy next to fetch_squirrel_tool.py — keep it in sync.
SKILL_COPY_PATH = BASE / "skills" / "squirrel-charm" / "squirrel_metric.json"

METRIC_NAME = "squirrel_charm_score"


# ---------------------------------------------------------------------------
# Geometry — pure-Python point-in-polygon (no dependencies)
# ---------------------------------------------------------------------------
def _point_in_ring(x: float, y: float, ring: list) -> bool:
    """Ray-casting test: is (x, y) inside this single ring of [lon, lat] pairs?"""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        # Does a ray to +x cross the edge (i, j)?
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i
    return inside


def _point_in_polygon(x: float, y: float, polygon: list) -> bool:
    """A GeoJSON Polygon = [outer_ring, hole1, hole2, ...]. Inside outer, outside holes."""
    if not polygon or not _point_in_ring(x, y, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(x, y, hole):
            return False
    return True


def load_zip_shapes(path: Path) -> list:
    """Return [(zip, bbox, [polygon, ...]), ...] with a bbox for fast prefiltering."""
    gj = json.loads(path.read_text())
    shapes = []
    for feat in gj["features"]:
        zip_code = feat["properties"]["zip"]
        geom = feat["geometry"]
        # Normalize Polygon vs MultiPolygon into a flat list of polygons.
        if geom["type"] == "Polygon":
            polygons = [geom["coordinates"]]
        elif geom["type"] == "MultiPolygon":
            polygons = geom["coordinates"]
        else:
            continue
        # Bounding box across all rings for a cheap reject.
        xs, ys = [], []
        for poly in polygons:
            for ring in poly:
                for lon, lat in ring:
                    xs.append(lon)
                    ys.append(lat)
        bbox = (min(xs), min(ys), max(xs), max(ys))
        shapes.append((zip_code, bbox, polygons))
    return shapes


def _seg_dist2(px, py, ax, ay, bx, by) -> float:
    """Squared distance (in degrees) from point to segment AB — fine for ranking."""
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return (px - ax) ** 2 + (py - ay) ** 2
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return (px - cx) ** 2 + (py - cy) ** 2


def _poly_dist2(px, py, polygons) -> float:
    """Min squared distance from a point to the boundary of any polygon/ring."""
    best = float("inf")
    for poly in polygons:
        for ring in poly:
            for i in range(len(ring)):
                ax, ay = ring[i - 1]
                bx, by = ring[i]
                d = _seg_dist2(px, py, ax, ay, bx, by)
                if d < best:
                    best = d
    return best


def zip_for_point(x: float, y: float, shapes: list):
    """
    Assign (lon=x, lat=y) to a Manhattan ZIP.

    Central Park is a population 'hole' in MODZCTA boundaries, so most census
    sightings fall *between* ZIP polygons. We first try a true point-in-polygon
    hit (edge sightings); otherwise we snap to the NEAREST bordering ZIP — i.e.
    "which neighborhood's squirrels are these?". Returns (zip, was_inside).
    """
    for zip_code, (minx, miny, maxx, maxy), polygons in shapes:
        if not (minx <= x <= maxx and miny <= y <= maxy):
            continue
        for poly in polygons:
            if _point_in_polygon(x, y, poly):
                return zip_code, True
    # Fallback: nearest ZIP by boundary distance.
    nearest, best = None, float("inf")
    for zip_code, _, polygons in shapes:
        d = _poly_dist2(x, y, polygons)
        if d < best:
            best, nearest = d, zip_code
    return nearest, False


# ---------------------------------------------------------------------------
# Census parsing + per-ZIP aggregation
# ---------------------------------------------------------------------------
def _is_true(value: str) -> bool:
    return (value or "").strip().lower() == "true"


def aggregate_by_zip(csv_path: Path, shapes: list):
    """Roll census sightings up to raw per-ZIP counts. Returns (stats, diagnostics)."""
    stats = defaultdict(lambda: {
        "sightings": 0,
        "approaches": 0,
        "runs_from": 0,
        "playful": 0,   # running / chasing / climbing events
        "black": 0,
    })
    placed = 0
    unplaced = 0
    inside = 0
    snapped = 0

    with csv_path.open() as fh:
        for row in csv.DictReader(fh):
            lon, lat = row.get("X", ""), row.get("Y", "")
            if not lon or not lat:
                unplaced += 1
                continue
            zip_code, was_inside = zip_for_point(float(lon), float(lat), shapes)
            if zip_code is None:
                unplaced += 1
                continue
            placed += 1
            inside += was_inside
            snapped += not was_inside
            s = stats[zip_code]
            s["sightings"] += 1
            if _is_true(row.get("Approaches")):
                s["approaches"] += 1
            if _is_true(row.get("Runs from")):
                s["runs_from"] += 1
            s["playful"] += sum(
                _is_true(row.get(col)) for col in ("Running", "Chasing", "Climbing")
            )
            if (row.get("Primary Fur Color") or "").strip() == "Black":
                s["black"] += 1

    return stats, {"placed": placed, "unplaced": unplaced,
                   "inside": inside, "snapped": snapped}


# ---------------------------------------------------------------------------
# Scoring — raw signals → normalized fractions → integer 0-10 scores
# ---------------------------------------------------------------------------
def _raw_signals(s: dict) -> dict:
    """Turn raw counts into comparable per-sighting rates (friendliness may be negative)."""
    n = s["sightings"]
    return {
        "abundance": float(n),
        "friendliness": (s["approaches"] - s["runs_from"]) / n,
        "playfulness": s["playful"] / (3 * n),  # 3 behaviors tracked per sighting
        "rarity": s["black"] / n,
    }


def _normalize(raw_by_zip: dict) -> dict:
    """Min-max each signal across scored ZIPs to a 0..1 fraction."""
    norm_by_zip = {z: {} for z in raw_by_zip}
    for key in WEIGHTS:
        values = [raw[key] for raw in raw_by_zip.values()]
        lo, hi = min(values), max(values)
        span = hi - lo
        for z, raw in raw_by_zip.items():
            # If every ZIP ties on this signal, give a neutral 0.5.
            norm_by_zip[z][key] = 0.5 if span == 0 else (raw[key] - lo) / span
    return norm_by_zip


def _to_score(fraction: float) -> int:
    """Map a 0..1 fraction to an INTEGER 1-10 (scored ZIPs never collide with no_data 0)."""
    return round(1 + fraction * 9)


def _band(score: int) -> str:
    if score >= 9:
        return "exceptional"
    if score >= 7:
        return "high"
    if score >= 5:
        return "moderate"
    if score >= 3:
        return "modest"
    return "low"


def _rationale(score: int, sub: dict, black: int) -> str:
    rare = (
        f"{black} rare black-squirrel sighting{'s' if black != 1 else ''}"
        if black else "no rare black squirrels recorded"
    )
    return (
        f"{score}/10 — {_band(sub['abundance'])} squirrel abundance, "
        f"{_band(sub['friendliness'])} friendliness (approaches vs. flees), "
        f"{_band(sub['playfulness'])} play activity, and {rare}."
    )


def build_records(stats: dict, all_zips: list) -> list:
    """Produce one contract record per Manhattan ZIP (scored, or no_data)."""
    scored_zips = [z for z in stats if stats[z]["sightings"] > 0]
    weight_total = sum(WEIGHTS.values())

    records = {}
    if scored_zips:
        raw_by_zip = {z: _raw_signals(stats[z]) for z in scored_zips}
        norm_by_zip = _normalize(raw_by_zip)
        for z in scored_zips:
            norm = norm_by_zip[z]
            sub_scores = {k: _to_score(norm[k]) for k in WEIGHTS}
            blend = sum(WEIGHTS[k] * norm[k] for k in WEIGHTS) / weight_total
            score = _to_score(blend)
            records[z] = {
                "zip_code": z,
                "score": score,
                "sub_scores": sub_scores,
                "sightings": stats[z]["sightings"],
                "rationale": _rationale(score, sub_scores, stats[z]["black"]),
            }

    # Every Manhattan ZIP appears; those with no census coverage are flagged.
    for z in all_zips:
        if z not in records:
            records[z] = {
                "zip_code": z,
                "score": 0,
                "sub_scores": {k: 0 for k in WEIGHTS},
                "sightings": 0,
                "no_data": True,
                "rationale": "No squirrel census data (outside Central Park).",
            }

    return [records[z] for z in sorted(records)]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    shapes = load_zip_shapes(GEOJSON_PATH)
    all_zips = [z for z, _, _ in shapes]

    stats, diag = aggregate_by_zip(CSV_PATH, shapes)
    records = build_records(stats, all_zips)

    output = {
        "metric": METRIC_NAME,
        "unit": "0-10",
        "source": "2018 Central Park Squirrel Census",
        "coverage_note": (
            "All sightings are inside Central Park, so only park-adjacent ZIPs "
            "are scored; other Manhattan ZIPs are marked no_data."
        ),
        "weights": WEIGHTS,
        "data": records,
    }
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    payload = json.dumps(output, indent=2)
    OUTPUT_PATH.write_text(payload)
    if SKILL_COPY_PATH.parent.exists():
        SKILL_COPY_PATH.write_text(payload)  # keep the skill's served copy fresh

    # Demo-friendly summary.
    scored = [r for r in records if not r.get("no_data")]
    print(f"Placed {diag['placed']} sightings into ZIPs "
          f"({diag['inside']} inside a ZIP, {diag['snapped']} snapped to nearest; "
          f"{diag['unplaced']} unplaced).")
    print(f"Scored {len(scored)} of {len(records)} Manhattan ZIPs.\n")
    print("Top squirrel-charm ZIPs:")
    for r in sorted(scored, key=lambda r: r["score"], reverse=True)[:3]:
        print(f"  {r['zip_code']}  score {r['score']}/10 "
              f"({r['sightings']} sightings)")
        print(f"      {r['rationale']}")
    print(f"\nWrote {OUTPUT_PATH.relative_to(BASE)}")


if __name__ == "__main__":
    main()
