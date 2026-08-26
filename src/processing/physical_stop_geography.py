"""Canonical offline geography assignment for physical-stop coordinates."""

from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Point, shape


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GEOGRAPHY_DIR = ROOT / "data" / "geography"

LAYERS = {
    "dc_ward": ("dc_wards.geojson", ("WARD", "WARD_ID", "NAME")),
    "dc_anc": ("dc_anc.geojson", ("ANC_ID", "ANC", "NAME")),
    "md_place": ("md_places.geojson", ("NAME", "NAMELSAD")),
    "va_place": ("va_places.geojson", ("NAME", "NAMELSAD")),
    "county": ("md_va_counties.geojson", ("NAME", "NAMELSAD")),
    "state_fips": ("md_va_counties.geojson", ("STATEFP",)),
}


def _property(properties, candidates):
    upper = {str(key).upper(): value for key, value in properties.items()}
    return next((upper[key] for key in candidates if key in upper), None)


def load_boundaries(directory=DEFAULT_GEOGRAPHY_DIR):
    result = {}
    directory = Path(directory)
    for layer, (filename, candidates) in LAYERS.items():
        path = directory / filename
        if not path.exists():
            result[layer] = []
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        result[layer] = [
            (shape(feature["geometry"]), _property(feature.get("properties", {}), candidates))
            for feature in data.get("features", []) if feature.get("geometry")
        ]
    return result


def assign_geography(latitude, longitude, boundaries):
    point = Point(float(longitude), float(latitude))
    matches = {}
    for layer, features in boundaries.items():
        values = sorted({str(value) for geometry, value in features
                         if value is not None and geometry.covers(point)})
        matches[layer] = values[0] if len(values) == 1 else None
    if matches.get("dc_ward") or matches.get("dc_anc"):
        state, municipality, county = "DC", "District of Columbia", None
    elif matches.get("md_place"):
        state, municipality, county = "MD", matches["md_place"], matches.get("county")
    elif matches.get("va_place"):
        state, municipality, county = "VA", matches["va_place"], matches.get("county")
    else:
        state = {"24": "MD", "51": "VA", "11": "DC"}.get(matches.get("state_fips"))
        municipality = None
        county = matches.get("county") if state != "DC" else None
    return {
        "state": state, "county": county,
        "municipality": municipality, "dc_ward": matches.get("dc_ward"),
        "dc_anc": matches.get("dc_anc"),
    }


def recompute_geography(conn, stop_ids=None, *, boundaries=None):
    boundaries = boundaries if boundaries is not None else load_boundaries()
    params = tuple(sorted(set(stop_ids or ())))
    where = f"WHERE id IN ({','.join('?' for _ in params)})" if params else ""
    rows = conn.execute(
        f"SELECT id,latitude,longitude FROM physical_stops {where} ORDER BY id", params
    ).fetchall()
    with conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS stop_jurisdiction(
            stop_id INTEGER PRIMARY KEY,state TEXT,dc_ward TEXT,dc_anc TEXT,
            county TEXT,municipality TEXT)""")
        for stop_id, latitude, longitude in rows:
            value = assign_geography(latitude, longitude, boundaries)
            conn.execute("""INSERT INTO stop_jurisdiction
                (stop_id,state,dc_ward,dc_anc,county,municipality)
                VALUES (?,?,?,?,?,?) ON CONFLICT(stop_id) DO UPDATE SET
                state=excluded.state,dc_ward=excluded.dc_ward,
                dc_anc=excluded.dc_anc,county=excluded.county,
                municipality=excluded.municipality""",
                (stop_id, value["state"], value["dc_ward"], value["dc_anc"],
                 value["county"], value["municipality"]))
            columns = {r[1] for r in conn.execute("PRAGMA table_info(physical_stops)")}
            if {"state", "dc_ward", "dc_anc", "county", "municipality"} <= columns:
                conn.execute("""UPDATE physical_stops SET state=?,dc_ward=?,dc_anc=?,
                    county=?,municipality=? WHERE id=?""",
                    (value["state"], value["dc_ward"], value["dc_anc"],
                     value["county"], value["municipality"], stop_id))
    return len(rows)


def preflight_manifest_geography(conn, manifest, *, boundaries=None):
    """Project child geography and compare it with predecessor rows without writes."""
    boundaries = boundaries if boundaries is not None else load_boundaries()
    dimensions = ("state", "county", "municipality", "dc_ward", "dc_anc")
    coverage = {dimension: 0 for dimension in dimensions}
    parent_differences = []
    crossings = []
    children = []
    for parent in manifest["parents"]:
        parent_id = parent["predecessor_physical_stop_id"]
        row = conn.execute("""SELECT state,county,municipality,dc_ward,dc_anc
            FROM stop_jurisdiction WHERE stop_id=?""", (parent_id,)).fetchone()
        parent_geo = _normalize_geography(dict(zip(dimensions, row or (None,) * len(dimensions))))
        sibling_geographies = []
        for ordinal, child in enumerate(parent["proposed_children"], 1):
            latitude, longitude = child["proposed_coordinates"]
            geography = assign_geography(latitude, longitude, boundaries)
            sibling_geographies.append((ordinal, geography))
            for dimension in dimensions:
                coverage[dimension] += geography[dimension] is not None
            changed = {dimension: {"parent": parent_geo[dimension],
                                   "child": geography[dimension]}
                       for dimension in dimensions
                       if parent_geo[dimension] != geography[dimension]}
            if changed:
                parent_differences.append({"parent": parent_id, "child_ordinal": ordinal,
                                           "differences": changed})
            children.append({"parent": parent_id, "child_ordinal": ordinal,
                             "geography": geography})
        distinct = {tuple(value[dimension] for dimension in dimensions)
                    for _, value in sibling_geographies}
        if len(distinct) > 1:
            crossings.append({"parent": parent_id, "children": [
                {"child_ordinal": ordinal, "geography": value}
                for ordinal, value in sibling_geographies
            ]})
    return {"child_count": len(children), "coverage": coverage,
            "parent_child_differences": parent_differences,
            "child_geography_crossings": crossings, "children": children}


def _normalize_geography(value):
    result = dict(value)
    if result.get("state") == "DC":
        result["county"] = None
        result["municipality"] = "District of Columbia"
    ward = result.get("dc_ward")
    if ward is not None:
        try:
            result["dc_ward"] = str(int(float(ward)))
        except (TypeError, ValueError):
            result["dc_ward"] = str(ward)
    return result
