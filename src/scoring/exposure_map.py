"""Read-only presentation of canonical route exposure; no new scoring model."""

from src.scoring.rider_exposure import percentile_by_stop


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
            ridership_value=value if usable else None,
            ridership_label="Combined route weekday boardings in source period",
            active_route_count=len(routes), active_routes=routes,
            connection_class=connection_class(len(routes)),
            bench_status=bench, shelter_status=shelter))
    result.sort(key=lambda r: (-(r["exposure_score"] or 0), r["physical_stop_id"]))
    for rank, row in enumerate(result, 1):
        row["rank"] = rank if row["exposure_score"] is not None else None
    return result


def map_payload(conn, mode, route=None, limit=100):
    rows = exposure_rows(conn)
    routes = {}
    for row in rows:
        for item in row["active_routes"]:
            entry = routes.setdefault(item["route_id"], dict(item, stop_count=0))
            entry["stop_count"] += 1
    selected = routes.get(route)
    if mode == "route":
        rows = [r for r in rows if any(x["route_id"] == route for x in r["active_routes"])]
    else:
        rows = [r for r in rows if r["exposure_score"] is not None]
    mappable = [r for r in rows if r["latitude"] is not None and r["longitude"] is not None]
    cap = min(max(limit, 1), 100)
    return dict(stops=mappable[:cap], total_matching=len(rows),
                missing_coordinates=len(rows)-len(mappable), limit=cap,
                truncated=len(mappable)>cap, selected_route=selected,
                routes=[routes[k] for k in sorted(routes)],
                source_period=conn.execute("SELECT MAX(period) FROM ridership_snapshots").fetchone()[0])
