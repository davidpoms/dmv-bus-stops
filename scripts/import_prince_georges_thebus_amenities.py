"""Import conflict-free Prince George's County TheBus amenity evidence."""

import argparse
import hashlib
import json
import math
import sqlite3
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.amenities.importer import upsert_amenity_evidence


SOURCE = "PRINCE_GEORGES_COUNTY_THEBUS"
JURISDICTION = "PRINCE_GEORGES_COUNTY"
DEFAULT_URL = (
    "https://gis.princegeorgescountymd.gov/arcgis/rest/services/DPWT/"
    "BUSTOPS_THEBUS/MapServer/3"
)
SEMANTIC_FIELDS = {"SHELTER": "shelter", "RECEPTACLE": "trash_can"}


def normalize_stop_id(value):
    if value is None or not str(value).strip():
        raise ValueError("TheBus source row requires Stop_ID")
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def normalize_binary(value):
    if value is None:
        return None
    normalized = str(value).strip().upper()
    if normalized == "YES":
        return 1
    if normalized == "NO":
        return 0
    return None


def haversine_m(lat1, lon1, lat2, lon2):
    radius = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    value = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _arcgis_get(base_url, path, parameters):
    url = base_url.rstrip("/") + path + "?" + urllib.parse.urlencode(parameters)
    with urllib.request.urlopen(url, timeout=90) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(f"ArcGIS error: {payload['error']}")
    return payload


def fetch_features(base_url=DEFAULT_URL, page_size=200):
    result = _arcgis_get(
        base_url, "/query", {"where": "1=1", "returnIdsOnly": "true", "f": "json"}
    )
    object_ids = result.get("objectIds") or []
    features = []
    for offset in range(0, len(object_ids), page_size):
        response = _arcgis_get(
            base_url,
            "/query",
            {
                "objectIds": ",".join(map(str, object_ids[offset : offset + page_size])),
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
            },
        )
        features.extend(response.get("features", []))
    if len(features) != len(object_ids):
        raise RuntimeError(
            f"ArcGIS pagination returned {len(features)} of {len(object_ids)} rows"
        )
    return features


def group_features(features):
    groups = defaultdict(list)
    for feature in features:
        groups[normalize_stop_id(feature.get("attributes", {}).get("Stop_ID"))].append(
            feature
        )
    return dict(groups)


def load_current_stops(conn):
    current = [
        dict(row)
        for row in conn.execute(
            """
            SELECT p.id, p.latitude, p.longitude, j.state, j.county
            FROM physical_stops p
            JOIN stop_gtfs_status s
              ON s.physical_stop_id=p.id AND s.current_gtfs=1
            LEFT JOIN stop_jurisdiction j ON j.stop_id=p.id
            """
        )
    ]
    pg = [
        stop
        for stop in current
        if stop["state"] == "MD" and stop["county"] == "Prince George's"
    ]
    return current, pg


def feature_coordinates(feature):
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry") or {}
    latitude = attrs.get("stop_lat", geometry.get("y"))
    longitude = attrs.get("stop_lon", geometry.get("x"))
    if latitude is None or longitude is None:
        return None
    return float(latitude), float(longitude)


def match_feature(feature, current_stops, pg_stops):
    coordinates = feature_coordinates(feature)
    if coordinates is None:
        return {"status": "quarantine", "reason": "missing_coordinates"}
    latitude, longitude = coordinates
    pg_distances = sorted(
        (
            haversine_m(latitude, longitude, stop["latitude"], stop["longitude"]),
            stop,
        )
        for stop in pg_stops
    )
    if not pg_distances:
        raise RuntimeError("No canonical current Prince George's candidates")
    global_distance, global_stop = min(
        (
            haversine_m(latitude, longitude, stop["latitude"], stop["longitude"]),
            stop,
        )
        for stop in current_stops
    )
    candidates = [stop for distance, stop in pg_distances if distance <= 10]
    nearest_distance, nearest_pg = pg_distances[0]
    if (
        len(candidates) == 1
        and nearest_distance <= 10
        and global_stop["id"] == nearest_pg["id"]
    ):
        return {
            "status": "accepted",
            "physical_stop_id": nearest_pg["id"],
            "distance_m": nearest_distance,
        }
    reason = "multiple_pg_candidates" if len(candidates) > 1 else "no_unique_10m_match"
    if global_distance <= 10 and global_stop["id"] != nearest_pg["id"]:
        reason = "nearest_current_stop_is_non_pg"
    return {"status": "quarantine", "reason": reason}


def classify_amenity(rows, field):
    raw_values = [row.get("attributes", {}).get(field) for row in rows]
    if any(value is None or not str(value).strip() for value in raw_values):
        return {"status": "unsupported", "reason": "empty", "raw_values": raw_values}
    normalized = [normalize_binary(value) for value in raw_values]
    if any(value is None for value in normalized):
        return {
            "status": "unsupported",
            "reason": "unknown_value",
            "raw_values": raw_values,
        }
    if len(set(normalized)) != 1:
        return {"status": "conflict", "reason": "yes_no_conflict", "raw_values": raw_values}
    present = normalized[0]
    return {
        "status": "accepted",
        "present": present,
        "value": "yes" if present else "no",
        "raw_value": "YES" if present else "NO",
        "raw_values": raw_values,
    }


def classify_groups(conn, features):
    groups = group_features(features)
    current_stops, pg_stops = load_current_stops(conn)
    evidence = []
    matching_quarantine = {}
    amenity_summary = {
        field: Counter(positive=0, negative=0, conflict=0, unsupported=0, emitted=0)
        for field in SEMANTIC_FIELDS
    }
    conflict_identities = set()

    for source_record_id, rows in groups.items():
        matches = [match_feature(row, current_stops, pg_stops) for row in rows]
        accepted_matches = [m for m in matches if m["status"] == "accepted"]
        target_ids = {m["physical_stop_id"] for m in accepted_matches}
        if len(accepted_matches) != len(rows) or len(target_ids) != 1:
            matching_quarantine[source_record_id] = {
                "reasons": sorted(
                    {m.get("reason", "different_physical_stops") for m in matches}
                    | ({"different_physical_stops"} if len(target_ids) > 1 else set())
                )
            }
            continue
        physical_stop_id = next(iter(target_ids))
        match_distance = max(m["distance_m"] for m in matches)
        metadata = json.dumps(
            {"source_stop_id": source_record_id, "contributing_rows": rows},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        for field, amenity_type in SEMANTIC_FIELDS.items():
            classification = classify_amenity(rows, field)
            status = classification["status"]
            if status == "conflict":
                amenity_summary[field]["conflict"] += 1
                conflict_identities.add((source_record_id, amenity_type))
                continue
            if status == "unsupported":
                amenity_summary[field]["unsupported"] += 1
                continue
            present = classification["present"]
            amenity_summary[field]["positive" if present else "negative"] += 1
            amenity_summary[field]["emitted"] += 1
            evidence.append(
                {
                    "physical_stop_id": physical_stop_id,
                    "source_record_id": source_record_id,
                    "amenity_type": amenity_type,
                    "present": present,
                    "value": classification["value"],
                    "raw_value": classification["raw_value"],
                    "match_distance_m": match_distance,
                    "source_metadata": metadata,
                }
            )
    return {
        "groups": groups,
        "evidence": evidence,
        "matching_quarantine": matching_quarantine,
        "amenity_summary": amenity_summary,
        "conflict_identities": conflict_identities,
        "current_pg_count": len(pg_stops),
    }


def existing_source_rows(conn):
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT id, physical_stop_id, source_record_id, amenity_type
            FROM stop_amenity_evidence WHERE source=?
            """,
            (SOURCE,),
        )
    ]


def apply_reconciliation(conn, classified):
    accepted_keys = {
        (r["physical_stop_id"], r["source_record_id"], r["amenity_type"])
        for r in classified["evidence"]
    }
    for result in classified["evidence"]:
        upsert_amenity_evidence(
            conn,
            physical_stop_id=result["physical_stop_id"],
            source=SOURCE,
            source_record_id=result["source_record_id"],
            amenity_type=result["amenity_type"],
            present=result["present"],
            confidence="high",
            match_distance_m=result["match_distance_m"],
            notes="Prince George's County DPW&T TheBus inventory",
            jurisdiction=JURISDICTION,
            value=result["value"],
            raw_value=result["raw_value"],
            source_metadata=result["source_metadata"],
        )
    stale_ids = [
        row["id"]
        for row in existing_source_rows(conn)
        if (row["physical_stop_id"], row["source_record_id"], row["amenity_type"])
        not in accepted_keys
    ]
    if stale_ids:
        conn.executemany(
            "DELETE FROM stop_amenity_evidence WHERE id=? AND source=?",
            [(row_id, SOURCE) for row_id in stale_ids],
        )
    return len(stale_ids)


def validate_applied(conn, classified):
    expected = len(classified["evidence"])
    actual = conn.execute(
        "SELECT COUNT(*) FROM stop_amenity_evidence WHERE source=?", (SOURCE,)
    ).fetchone()[0]
    if actual != expected:
        raise RuntimeError(f"Expected {expected} source rows, found {actual}")
    duplicates = conn.execute(
        """
        SELECT COUNT(*) FROM (
          SELECT physical_stop_id,source,source_record_id,amenity_type,COUNT(*) n
          FROM stop_amenity_evidence WHERE source=? GROUP BY 1,2,3,4 HAVING n>1
        )
        """,
        (SOURCE,),
    ).fetchone()[0]
    non_pg = conn.execute(
        """
        SELECT COUNT(*) FROM stop_amenity_evidence e
        LEFT JOIN stop_gtfs_status s ON s.physical_stop_id=e.physical_stop_id
        LEFT JOIN stop_jurisdiction j ON j.stop_id=e.physical_stop_id
        WHERE e.source=? AND (
          s.current_gtfs IS NOT 1 OR j.state IS NOT 'MD'
          OR j.county IS NOT "Prince George's"
        )
        """,
        (SOURCE,),
    ).fetchone()[0]
    ada = conn.execute(
        """SELECT COUNT(*) FROM stop_amenity_evidence
           WHERE source=? AND amenity_type NOT IN ('shelter','trash_can')""",
        (SOURCE,),
    ).fetchone()[0]
    empty_metadata = conn.execute(
        """SELECT COUNT(*) FROM stop_amenity_evidence
           WHERE source=? AND (source_metadata IS NULL OR TRIM(source_metadata)='')""",
        (SOURCE,),
    ).fetchone()[0]
    conflicts = sum(
        conn.execute(
            """SELECT COUNT(*) FROM stop_amenity_evidence
               WHERE source=? AND source_record_id=? AND amenity_type=?""",
            (SOURCE, source_record_id, amenity_type),
        ).fetchone()[0]
        for source_record_id, amenity_type in classified["conflict_identities"]
    )
    if duplicates or non_pg or ada or empty_metadata or conflicts:
        raise RuntimeError(
            "Post-import validation failed: "
            f"duplicates={duplicates}, non_pg={non_pg}, non_semantic={ada}, "
            f"empty_metadata={empty_metadata}, conflicts={conflicts}"
        )


def database_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def table_counts_by_source(conn):
    return dict(
        conn.execute(
            """SELECT source,COUNT(*) FROM stop_amenity_evidence
               WHERE source<>? GROUP BY source ORDER BY source""",
            (SOURCE,),
        )
    )


def build_report(conn, features, classified):
    existing = existing_source_rows(conn)
    existing_keys = {
        (r["physical_stop_id"], r["source_record_id"], r["amenity_type"])
        for r in existing
    }
    accepted_keys = {
        (r["physical_stop_id"], r["source_record_id"], r["amenity_type"])
        for r in classified["evidence"]
    }
    covered_stops = {r["physical_stop_id"] for r in classified["evidence"]}
    other_amenity_stops = {
        row[0]
        for row in conn.execute(
            """SELECT DISTINCT physical_stop_id FROM stop_amenity_evidence
               WHERE source NOT IN (?, 'DDOT')""",
            (SOURCE,),
        )
    }
    raw_table = conn.execute(
        """SELECT 1 FROM sqlite_master
           WHERE type='table' AND name='jurisdiction_source_evidence'"""
    ).fetchone()
    raw_covered = set()
    if raw_table:
        raw_covered = {
            row[0]
            for row in conn.execute(
                """SELECT DISTINCT physical_stop_id FROM jurisdiction_source_evidence
                   WHERE source='PRINCE_GEORGES_COUNTY'"""
            )
        }
    current_pg = {
        row[0]
        for row in conn.execute(
            """
            SELECT s.physical_stop_id FROM stop_gtfs_status s
            JOIN stop_jurisdiction j ON j.stop_id=s.physical_stop_id
            WHERE s.current_gtfs=1 AND j.state='MD' AND j.county="Prince George's"
            """
        )
    }
    raw_gap = current_pg - raw_covered if raw_table else set()
    return {
        "source": SOURCE,
        "feature_rows_fetched": len(features),
        "unique_stop_id_groups": len(classified["groups"]),
        "accepted_source_stop_groups": len(
            {r["source_record_id"] for r in classified["evidence"]}
        ),
        "matching_quarantine_groups": len(classified["matching_quarantine"]),
        "shelter": dict(classified["amenity_summary"]["SHELTER"]),
        "receptacle": dict(classified["amenity_summary"]["RECEPTACLE"]),
        "ada_raw_distribution": dict(
            Counter(
                "<EMPTY>"
                if row.get("attributes", {}).get("ADA") is None
                or not str(row["attributes"].get("ADA")).strip()
                else str(row["attributes"].get("ADA")).strip()
                for row in features
            )
        ),
        "unique_current_pg_stops_receiving_evidence": len(covered_stops),
        "already_having_other_local_amenity_evidence": len(
            covered_stops & other_amenity_stops
        ),
        "newly_receiving_local_amenity_evidence": len(
            covered_stops - other_amenity_stops
        ),
        "prior_raw_pg_gap_size": len(raw_gap) if raw_table else None,
        "prior_raw_pg_gap_reached": len(covered_stops & raw_gap) if raw_table else None,
        "expected_inserts": len(accepted_keys - existing_keys),
        "expected_updates": len(accepted_keys & existing_keys),
        "expected_stale_deletions": len(existing_keys - accepted_keys),
        "existing_source_rows": len(existing),
        "non_pg_rows": 0,
        "ada_semantic_rows": 0,
    }


def run(db_path, features, apply=False):
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    before_hash = database_sha256(db_path)
    other_before = table_counts_by_source(conn)
    classified = classify_groups(conn, features)
    report = build_report(conn, features, classified)
    report["database_sha256_before"] = before_hash
    if apply:
        try:
            conn.execute("BEGIN IMMEDIATE")
            deleted = apply_reconciliation(conn, classified)
            validate_applied(conn, classified)
            if table_counts_by_source(conn) != other_before:
                raise RuntimeError("Another jurisdiction's amenity evidence changed")
            conn.commit()
            report["stale_rows_deleted"] = deleted
        except Exception:
            conn.rollback()
            raise
    conn.close()
    report["applied"] = apply
    report["database_sha256_after"] = database_sha256(db_path)
    return report


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report")
    parser.add_argument("--url", default=DEFAULT_URL)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    report = run(args.db, fetch_features(args.url), apply=args.apply)
    output = json.dumps(report, indent=2, sort_keys=True)
    print(output)
    if args.report:
        Path(args.report).write_text(output + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
