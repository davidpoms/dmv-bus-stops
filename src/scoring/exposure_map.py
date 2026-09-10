"""Read-only presentation of canonical route exposure; no new scoring model."""

import calendar
from datetime import date

from src.scoring.rider_exposure import percentile_by_stop

GEOGRAPHIES = {"state": "State", "county": "County", "municipality": "Municipality",
               "dc_ward": "Ward", "dc_anc": "ANC"}
MIN_BAND_POPULATION = 20
DAILY_LABEL = "Estimated combined average weekday route boardings"


def weekday_divisor(period):
    """Existing project convention: calendar Mon–Fri in the recorded month.

    The retained export contains monthly day-type totals, not daily averages.
    Holiday service classifications and the export's filter metadata are absent;
    this produces a calendar-weekday estimate, not an agency service-day average.
    """
    try:
        month = date.fromisoformat(period)
    except (TypeError, ValueError):
        return None
    return sum(date(month.year, month.month, day).weekday() < 5
               for day in range(1, calendar.monthrange(month.year, month.month)[1] + 1))


def geography_value(kind, value):
    if value is None or not str(value).strip():
        return None
    value = str(value).strip()
    if kind == "dc_ward" and value.endswith(".0") and value[:-2].isdigit():
        return value[:-2]
    return value


def geography_options(rows):
    counts = {kind: {} for kind in GEOGRAPHIES}
    for row in rows:
        for kind, value in row["geographies"].items():
            if value:
                group = counts[kind].setdefault(value, {"value": value, "population": 0, "usable_population": 0})
                group["population"] += 1
                group["usable_population"] += row["exposure_score"] is not None
    return [{"type": kind, "label": GEOGRAPHIES[kind],
             "values": [values[k] for k in sorted(values)]}
            for kind, values in counts.items() if values]


def compare_rows(rows, kind=None, value=None):
    """Compare before route filtering/capping; geography dimensions are independent."""
    if not kind and not value:
        return rows, dict(geography_type=None, geography_value=None,
                          population=len(rows), usable_population=sum(r["exposure_score"] is not None for r in rows),
                          small_population=False, minimum_band_population=MIN_BAND_POPULATION)
    if kind not in GEOGRAPHIES or not value:
        raise ValueError("Choose a known geography type and value")
    value = geography_value(kind, value)
    if value is None:
        raise ValueError("Choose a known geography value")
    selected = [dict(r) for r in rows if r["geographies"].get(kind) == value]
    if not selected:
        raise ValueError("Unknown geography value for active stops")
    usable = {r["physical_stop_id"]: r["exposure_score"] for r in selected if r["exposure_score"] is not None}
    ranks = percentile_by_stop(usable)
    small = len(usable) < MIN_BAND_POPULATION
    for index, row in enumerate(selected, 1):
        present = row["exposure_score"] is not None
        row.update(jurisdiction_rank=index if present else None,
                   jurisdiction_population=len(selected), jurisdiction_usable_population=len(usable),
                   jurisdiction_percentile=ranks.get(row["physical_stop_id"]) if not small else None,
                   jurisdiction_band=("Small comparison group" if small else exposure_band(ranks[row["physical_stop_id"]])) if present else "Unavailable")
        row.update(rank=row["jurisdiction_rank"], exposure_percentile=row["jurisdiction_percentile"],
                   exposure_band=row["jurisdiction_band"])
    return selected, dict(geography_type=kind, geography_value=value, population=len(selected),
                          usable_population=len(usable), small_population=small,
                          minimum_band_population=MIN_BAND_POPULATION)


def exposure_band(percentile):
    if percentile is None:
        return "Unavailable"
    return ("Very High" if percentile >= 90 else "High" if percentile >= 75
            else "Moderate" if percentile >= 40 else "Lower")


def connection_class(count):
    return ("No mapped routes" if count == 0 else "Ordinary stop" if count == 1
            else "Connection point" if count == 2 else "Significant connection"
            if count < 5 else "Major transfer point")


def exposure_rows(conn):
    """Use active assessment values, recomputing ranks over today's active set.

    Route membership is the project's canonical stop_routes relation. It has no
    per-route service calendar; do not invent another active-stop criterion.
    """
    period = conn.execute("SELECT MAX(period) FROM ridership_snapshots").fetchone()[0]
    divisor = weekday_divisor(period)
    geographies = {r[0]: {kind: geography_value(kind, value) for kind, value in zip(GEOGRAPHIES, r[1:])}
                   for r in conn.execute("""SELECT j.stop_id,j.state,j.county,j.municipality,j.dc_ward,j.dc_anc
                       FROM stop_jurisdiction j JOIN stop_gtfs_status s
                       ON s.physical_stop_id=j.stop_id AND s.current_gtfs=1""")}
    routes_by_stop = {}
    for stop_id, route_id, name in conn.execute("""
        SELECT DISTINCT pm.physical_stop_id,r.route_id,r.route_name
        FROM physical_stop_members pm
        JOIN stop_gtfs_status s ON s.physical_stop_id=pm.physical_stop_id
          AND s.current_gtfs=1
        JOIN stop_routes sr ON sr.stop_id=pm.bus_stop_id
        JOIN routes r ON r.id=sr.route_id
        ORDER BY r.route_id
    """):
        routes_by_stop.setdefault(stop_id, []).append(
            {"route_id": route_id, "route_name": name})
    rows = conn.execute("""
        SELECT p.id,p.primary_name,p.latitude,p.longitude,
          a.combined_route_weekday_boardings,
          COALESCE(b.derived_status,'unknown'),
          COALESCE(h.derived_status,'unknown')
        FROM physical_stops p
        JOIN stop_gtfs_status s ON s.physical_stop_id=p.id AND s.current_gtfs=1
        LEFT JOIN opportunity_assessments a ON a.physical_stop_id=p.id
        LEFT JOIN stop_amenity_status b ON b.physical_stop_id=p.id AND b.amenity_type='bench'
        LEFT JOIN stop_amenity_status h ON h.physical_stop_id=p.id AND h.amenity_type='shelter'
    """).fetchall()
    # Preserve the canonical percentile denominator and zero normalization.
    percentiles = percentile_by_stop({r[0]: r[4] for r in rows})
    result = []
    for stop_id, name, lat, lon, value, bench, shelter in rows:
        routes = routes_by_stop.get(stop_id, [])
        usable = value is not None and value > 0
        result.append(dict(
            physical_stop_id=stop_id, stop_name=name, latitude=lat, longitude=lon,
            exposure_score=value if usable else None,
            exposure_percentile=percentiles[stop_id] if usable else None,
            exposure_band=exposure_band(percentiles[stop_id] if usable else None),
            ridership_value=value / divisor if usable and divisor else None,
            ridership_label=DAILY_LABEL, weekday_divisor=divisor,
            geographies=geographies.get(stop_id, {}),
            active_route_count=len(routes), active_routes=routes,
            connection_class=connection_class(len(routes)),
            bench_status=bench, shelter_status=shelter))
    result.sort(key=lambda r: (-(r["exposure_score"] or 0), r["physical_stop_id"]))
    for rank, row in enumerate(result, 1):
        row["rank"] = rank if row["exposure_score"] is not None else None
        row.update(regional_rank=row["rank"], regional_percentile=row["exposure_percentile"],
                   regional_band=row["exposure_band"])
    return result


def map_payload(conn, mode, route=None, limit=100, geography_type=None, geography_value=None):
    rows = exposure_rows(conn)
    options = geography_options(rows)
    routes = {}
    for row in rows:
        for item in row["active_routes"]:
            entry = routes.setdefault(item["route_id"], dict(item, stop_count=0))
            entry["stop_count"] += 1
    selected = routes.get(route)
    rows, comparison = compare_rows(rows, geography_type, geography_value)
    if mode == "route":
        rows = [r for r in rows if any(x["route_id"] == route for x in r["active_routes"])]
    else:
        rows = [r for r in rows if r["exposure_score"] is not None]
    mappable = [r for r in rows if r["latitude"] is not None and r["longitude"] is not None]
    cap = min(max(limit, 1), 100)
    return dict(stops=mappable[:cap], total_matching=len(rows),
                missing_coordinates=len(rows)-len(mappable), limit=cap,
                truncated=len(mappable)>cap, selected_route=selected,
                comparison=comparison, geographies=options,
                routes=[routes[k] for k in sorted(routes)],
                source_period=conn.execute("SELECT MAX(period) FROM ridership_snapshots").fetchone()[0])
