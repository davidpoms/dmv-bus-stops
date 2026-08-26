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
