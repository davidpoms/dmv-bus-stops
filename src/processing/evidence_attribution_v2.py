"""Fail-closed, source-preserving evidence attribution for V2 identities."""

import json

from src.processing.heading_audit import distance_m


def ensure_attribution_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS physical_stop_evidence_attribution(
        evidence_table TEXT NOT NULL,evidence_row_id INTEGER NOT NULL,
        physical_stop_id INTEGER,attribution_method TEXT NOT NULL,
        attribution_version TEXT NOT NULL,distance_m REAL,provenance_json TEXT NOT NULL,
        attributed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(evidence_table,evidence_row_id,attribution_version))""")


def attribute(conn, *, evidence_table, evidence_row_id, version,
              exact_member_stop_id=None, exact_source_stop_id=None,
              spatial_stop_id=None, distance_m=None, spatial_is_unambiguous=False,
              provenance=None):
    """Record attribution separately from immutable/raw source evidence."""
    if exact_member_stop_id is not None:
        stop_id, method = exact_member_stop_id, "exact_member"
    elif exact_source_stop_id is not None:
        stop_id, method = exact_source_stop_id, "exact_source_record"
    elif spatial_stop_id is not None and spatial_is_unambiguous:
        stop_id, method = spatial_stop_id, "spatial_reassessed"
    else:
        stop_id, method = None, "unresolved"
    ensure_attribution_schema(conn)
    conn.execute("""INSERT INTO physical_stop_evidence_attribution
        (evidence_table,evidence_row_id,physical_stop_id,attribution_method,
         attribution_version,distance_m,provenance_json)
        VALUES (?,?,?,?,?,?,?) ON CONFLICT(evidence_table,evidence_row_id,
        attribution_version) DO UPDATE SET physical_stop_id=excluded.physical_stop_id,
        attribution_method=excluded.attribution_method,distance_m=excluded.distance_m,
        provenance_json=excluded.provenance_json""",
        (evidence_table, evidence_row_id, stop_id, method, version, distance_m,
         json.dumps(provenance or {}, sort_keys=True)))
    return method, stop_id


def preflight_manifest_attribution(conn, manifest, *, maximum_spatial_m=100):
    """Classify affected raw evidence against proposed children without writes."""
    children = []
    affected = set()
    for parent in manifest["parents"]:
        affected.add(parent["predecessor_physical_stop_id"])
        for ordinal, child in enumerate(parent["proposed_children"], 1):
            children.append({
                "key": (parent["predecessor_physical_stop_id"], ordinal),
                "external": set(map(str, child["external_source_ids"])),
                "gtfs": set(map(str, child["eligible_gtfs_stop_ids"])),
                "coordinates": tuple(child["proposed_coordinates"]),
            })
    external = {}
    gtfs = {}
    for child in children:
        for value in child["external"]:
            external.setdefault(value, []).append(child)
        for value in child["gtfs"]:
            gtfs.setdefault(value, []).append(child)

    def exact(values, index):
        matches = {item["key"] for value in values for item in index.get(str(value), [])}
        return "exact_source_record" if len(matches) == 1 else None

    def spatial(latitude, longitude):
        if latitude is None or longitude is None:
            return None
        ranked = sorted((distance_m((latitude, longitude), child["coordinates"]), child["key"])
                        for child in children)
        if not ranked or ranked[0][0] > maximum_spatial_m:
            return None
        if len(ranked) > 1 and abs(ranked[0][0] - ranked[1][0]) < 0.01:
            return None
        return "spatial_reassessed"

    counts = {}
    placeholders = ",".join("?" for _ in affected)

    def tally(table, classifications):
        value = {name: 0 for name in (
            "exact_member", "exact_source_record", "spatial_reassessed", "unresolved"
        )}
        for classification in classifications:
            value[classification or "unresolved"] += 1
        counts[table] = value

    wmata = []
    for physical_stop_id, stop_id in conn.execute(
            "SELECT physical_stop_id,wmata_stop_id FROM stop_wmata_evidence"):
        matches = {item["key"] for item in gtfs.get(str(stop_id), [])}
        if physical_stop_id in affected or matches:
            wmata.append("exact_member" if len(matches) == 1 else None)
    tally("stop_wmata_evidence", wmata)

    amenity = []
    for source_id, metadata in conn.execute(
            f"SELECT source_record_id,source_metadata FROM stop_amenity_evidence "
            f"WHERE physical_stop_id IN ({placeholders})", tuple(sorted(affected))):
        parsed = _metadata(metadata)
        amenity.append(exact(_identity_values(source_id, parsed), external)
                       or spatial(parsed.get("source_lat"), parsed.get("source_lon")))
    tally("stop_amenity_evidence", amenity)

    jurisdiction = []
    for source_id, latitude, longitude, metadata in conn.execute(
            f"SELECT source_record_id,source_latitude,source_longitude,source_metadata "
            f"FROM jurisdiction_source_evidence WHERE physical_stop_id IN ({placeholders})",
            tuple(sorted(affected))):
        parsed = _metadata(metadata)
        jurisdiction.append(exact(_identity_values(source_id, parsed), external)
                            or spatial(latitude, longitude))
    tally("jurisdiction_source_evidence", jurisdiction)

    osm = []
    for tags, in conn.execute(
            f"SELECT osm_tags FROM stop_osm_evidence WHERE stop_id IN ({placeholders})",
            tuple(sorted(affected))):
        parsed = _metadata(tags)
        osm.append(exact([parsed.get("ref:wmata")], external))
    tally("stop_osm_evidence", osm)

    derived = {}
    for table, column in (
        ("stop_amenity_status", "physical_stop_id"),
        ("stop_amenity_review_priority", "physical_stop_id"),
        ("opportunity_assessments", "physical_stop_id"),
        ("improvement_opportunities", "physical_stop_id"),
        ("seating_improvement_opportunities", "physical_stop_id"),
        ("bench_installation_candidates", "physical_stop_id"),
        ("improvement_recommendations", "physical_stop_id"),
        ("stop_improvement_impact", "physical_stop_id"),
        ("review_queue", "physical_stop_id"),
    ):
        if conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                        (table,)).fetchone()[0]:
            derived[table] = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {column} IN ({placeholders})",
                tuple(sorted(affected)),
            ).fetchone()[0]
    counts["derived_rebuild"] = derived
    return counts


def apply_manifest_attribution(conn, manifest, *, version="physical-stop-v2-cutover-1",
                               maximum_spatial_m=100):
    """Persist fail-closed attribution for evidence associated with split parents."""
    children, affected = [], set()
    for parent in manifest["parents"]:
        predecessor = parent["predecessor_physical_stop_id"]
        affected.add(predecessor)
        for child in parent["proposed_children"]:
            members = tuple(child["member_bus_stop_ids"])
            successor = conn.execute("""SELECT successor_physical_stop_id
                FROM physical_stop_member_lineage ml
                JOIN physical_stop_identity_events e ON e.id=ml.event_id
                WHERE e.migration_version=? AND ml.predecessor_physical_stop_id=?
                  AND ml.bus_stop_id=?""", (version, predecessor, members[0])).fetchone()
            if not successor:
                raise RuntimeError(f"missing successor lineage for {predecessor}/{members[0]}")
            children.append({
                "stop_id": successor[0], "members": set(members),
                "external": set(map(str, child["external_source_ids"])),
                "gtfs": set(map(str, child["eligible_gtfs_stop_ids"])),
                "coordinates": tuple(child["proposed_coordinates"]),
            })
    external, gtfs = {}, {}
    for child in children:
        for value in child["external"]:
            external.setdefault(value, []).append(child)
        for value in child["gtfs"]:
            gtfs.setdefault(value, []).append(child)

    def exact(values, index):
        matches = {item["stop_id"] for value in values for item in index.get(str(value), [])
                   if value not in (None, "")}
        return next(iter(matches)) if len(matches) == 1 else None

    def spatial(latitude, longitude):
        if latitude is None or longitude is None:
            return None, None
        ranked = sorted((distance_m((latitude, longitude), child["coordinates"]),
                         child["stop_id"]) for child in children)
        if not ranked or ranked[0][0] > maximum_spatial_m:
            return None, None
        if len(ranked) > 1 and abs(ranked[0][0] - ranked[1][0]) < 0.01:
            return None, None
        return ranked[0][1], ranked[0][0]

    placeholders = ",".join("?" for _ in affected)
    results = {table: {method: 0 for method in (
        "exact_member", "exact_source_record", "spatial_reassessed", "unresolved"
    )} for table in ("stop_wmata_evidence", "stop_amenity_evidence",
                     "jurisdiction_source_evidence", "stop_osm_evidence")}

    def record(table, row_id, method, stop_id=None, distance=None, provenance=None):
        attribute(conn, evidence_table=table, evidence_row_id=row_id, version=version,
                  exact_member_stop_id=stop_id if method == "exact_member" else None,
                  exact_source_stop_id=stop_id if method == "exact_source_record" else None,
                  spatial_stop_id=stop_id if method == "spatial_reassessed" else None,
                  spatial_is_unambiguous=method == "spatial_reassessed", distance_m=distance,
                  provenance=provenance)
        results[table][method] += 1

    for row_id, predecessor, source_id in conn.execute(
            "SELECT id,physical_stop_id,wmata_stop_id FROM stop_wmata_evidence"):
        matches = {item["stop_id"] for item in gtfs.get(str(source_id), [])}
        if predecessor in affected or matches:
            stop_id = next(iter(matches)) if len(matches) == 1 else None
            record("stop_wmata_evidence", row_id,
                   "exact_member" if stop_id else "unresolved", stop_id,
                   provenance={"source_stop_id": str(source_id)})
    for row_id, source_id, metadata in conn.execute(
            f"SELECT id,source_record_id,source_metadata FROM stop_amenity_evidence "
            f"WHERE physical_stop_id IN ({placeholders})", tuple(sorted(affected))):
        parsed = _metadata(metadata); stop_id = exact(_identity_values(source_id, parsed), external)
        if stop_id:
            record("stop_amenity_evidence", row_id, "exact_source_record", stop_id)
        else:
            stop_id, distance = spatial(parsed.get("source_lat"), parsed.get("source_lon"))
            record("stop_amenity_evidence", row_id,
                   "spatial_reassessed" if stop_id else "unresolved", stop_id, distance)
    for row_id, source_id, latitude, longitude, metadata in conn.execute(
            f"SELECT id,source_record_id,source_latitude,source_longitude,source_metadata "
            f"FROM jurisdiction_source_evidence WHERE physical_stop_id IN ({placeholders})",
            tuple(sorted(affected))):
        parsed = _metadata(metadata); stop_id = exact(_identity_values(source_id, parsed), external)
        if stop_id:
            record("jurisdiction_source_evidence", row_id, "exact_source_record", stop_id)
        else:
            stop_id, distance = spatial(latitude, longitude)
            record("jurisdiction_source_evidence", row_id,
                   "spatial_reassessed" if stop_id else "unresolved", stop_id, distance)
    for row_id, tags in conn.execute(
            f"SELECT id,osm_tags FROM stop_osm_evidence WHERE stop_id IN ({placeholders})",
            tuple(sorted(affected))):
        parsed = _metadata(tags); stop_id = exact([parsed.get("ref:wmata")], external)
        record("stop_osm_evidence", row_id,
               "exact_source_record" if stop_id else "unresolved", stop_id)
    conn.commit()
    return results


def _metadata(value):
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _identity_values(source_id, metadata):
    values = [source_id]
    for key in ("source_stop_id", "stop_id", "REG_ID", "RegionalID", "regional_id",
                "ref:wmata", "stop_code"):
        if metadata.get(key) not in (None, ""):
            values.append(metadata[key])
    return values
