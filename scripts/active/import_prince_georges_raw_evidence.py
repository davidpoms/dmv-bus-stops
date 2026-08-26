"""Import raw Prince George's County ArcGIS stop records.

The source's inventory fields are intentionally opaque. This importer stores
their attributes as provenance only and never creates amenity evidence.
"""

import argparse
import hashlib
import json
import math
import sqlite3
import sys
import urllib.parse
import urllib.request
import uuid
from collections import Counter, defaultdict
from pathlib import Path


SOURCE = "PRINCE_GEORGES_COUNTY"
JURISDICTION = SOURCE
DEFAULT_URL = (
    "https://gis.princegeorgescountymd.gov/arcgis/rest/services/"
    "transportation/Transportation/MapServer/6"
)


def normalize_globalid(value):
    if value is None or not str(value).strip():
        raise ValueError("Prince George's source record requires GLOBALID")
    try:
        return str(uuid.UUID(str(value).strip().strip("{}"))).lower()
    except ValueError as exc:
        raise ValueError(f"Invalid Prince George's GLOBALID: {value!r}") from exc


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


def fetch_features(base_url=DEFAULT_URL, page_size=1000):
    identity = _arcgis_get(
        base_url, "/query", {"where": "1=1", "returnIdsOnly": "true", "f": "json"}
    )
    object_ids = identity.get("objectIds") or []
    features = []
    for offset in range(0, len(object_ids), page_size):
        payload = _arcgis_get(
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
        features.extend(payload.get("features", []))
    if len(features) != len(object_ids):
        raise RuntimeError(
            f"ArcGIS pagination returned {len(features)} of {len(object_ids)} records"
        )
    return features


def validate_features(features):
    identities = [normalize_globalid(f.get("attributes", {}).get("GLOBALID")) for f in features]
    duplicates = [key for key, count in Counter(identities).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate Prince George's GLOBALID values: {duplicates[:5]}")
    return identities


def load_candidates(conn):
    current = [
        dict(row)
        for row in conn.execute(
            """
            SELECT p.id, p.latitude, p.longitude, j.state, j.county
            FROM physical_stops p
            JOIN stop_gtfs_status g
              ON g.physical_stop_id=p.id AND g.current_gtfs=1
            LEFT JOIN stop_jurisdiction j ON j.stop_id=p.id
            """
        )
    ]
    pg = [
        stop
        for stop in current
        if stop["state"] == "MD" and stop["county"] == "Prince George's"
    ]
    current_ids = {stop["id"] for stop in current}
    pg_ids = {stop["id"] for stop in pg}
    external = defaultdict(set)
    for row in conn.execute(
        """
        SELECT b.external_stop_id, m.physical_stop_id
        FROM bus_stops b
        JOIN physical_stop_members m ON m.bus_stop_id=b.id
        JOIN stop_gtfs_status g
          ON g.physical_stop_id=m.physical_stop_id AND g.current_gtfs=1
        WHERE b.external_stop_id IS NOT NULL
        """
    ):
        if row[1] in current_ids:
            external[str(row[0]).strip()].add(row[1])
    return current, pg, pg_ids, external


def feature_coordinates(feature):
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry") or {}
    latitude = attrs.get("BSTP_LAT", geometry.get("y"))
    longitude = attrs.get("BSTP_LON", geometry.get("x"))
    if latitude is None or longitude is None:
        raise ValueError(
            f"Source {attrs.get('GLOBALID')!r} has no usable coordinates"
        )
    return float(latitude), float(longitude)


def classify_features(conn, features):
    identities = validate_features(features)
    current, pg_stops, pg_ids, external = load_candidates(conn)
    current_by_id = {stop["id"]: stop for stop in current}
    accepted, review, unmatched = [], [], []
    distance_distribution = Counter()

    for feature, source_record_id in zip(features, identities):
        attrs = feature["attributes"]
        latitude, longitude = feature_coordinates(feature)
        pg_distances = sorted(
            (
                haversine_m(latitude, longitude, s["latitude"], s["longitude"]),
                s,
            )
            for s in pg_stops
        )
        if not pg_distances:
            raise RuntimeError("No canonical current Prince George's stops")
        nearest_distance, nearest_pg = pg_distances[0]
        global_distance, nearest_global = min(
            (
                haversine_m(latitude, longitude, s["latitude"], s["longitude"]),
                s,
            )
            for s in current
        )
        distance_distribution[_distance_bucket(nearest_distance)] += 1
        reg_id = str(attrs.get("REG_ID", "")).strip()
        exact_ids = external.get(reg_id, set()) if reg_id else set()
        exact_pg_ids = exact_ids & pg_ids

        result = {
            "source_record_id": source_record_id,
            "original_globalid": attrs.get("GLOBALID"),
            "latitude": latitude,
            "longitude": longitude,
            "attributes": attrs,
        }
        if exact_ids and not exact_pg_ids:
            result.update(reason="exact_id_non_pg")
            unmatched.append(result)
            continue
        if exact_ids and (len(exact_ids) != 1 or len(exact_pg_ids) != 1):
            result.update(reason="exact_id_ambiguous")
            review.append(result)
            continue
        if len(exact_pg_ids) == 1:
            physical_stop_id = next(iter(exact_pg_ids))
            stop = current_by_id[physical_stop_id]
            distance = haversine_m(
                latitude, longitude, stop["latitude"], stop["longitude"]
            )
            if distance <= 50:
                result.update(
                    physical_stop_id=physical_stop_id,
                    match_method="exact_reg_id",
                    match_distance_m=distance,
                )
                accepted.append(result)
            else:
                result.update(reason="exact_id_over_50m", match_distance_m=distance)
                review.append(result)
            continue

        candidates_10m = [stop for distance, stop in pg_distances if distance <= 10]
        if (
            len(candidates_10m) == 1
            and nearest_distance <= 10
            and nearest_global["id"] == nearest_pg["id"]
        ):
            result.update(
                physical_stop_id=nearest_pg["id"],
                match_method="unique_spatial_10m",
                match_distance_m=nearest_distance,
            )
            accepted.append(result)
        elif nearest_distance <= 50:
            result.update(reason="spatial_review", match_distance_m=nearest_distance)
            review.append(result)
        else:
            result.update(reason="unmatched", match_distance_m=nearest_distance)
            unmatched.append(result)

    return {
        "accepted": accepted,
        "review": review,
        "unmatched": unmatched,
        "current_pg_count": len(pg_stops),
        "distance_distribution": dict(distance_distribution),
    }


def _distance_bucket(distance):
    if distance <= 10:
        return "<=10m"
    if distance <= 20:
        return "10-20m"
    if distance <= 30:
        return "20-30m"
    if distance <= 50:
        return "30-50m"
    return ">50m"


def setup_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jurisdiction_source_evidence (
            id INTEGER PRIMARY KEY,
            physical_stop_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            source_record_id TEXT NOT NULL,
            jurisdiction TEXT NOT NULL,
            source_latitude REAL,
            source_longitude REAL,
            match_method TEXT NOT NULL,
            match_distance_m REAL,
            source_metadata TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
            idx_jurisdiction_source_evidence_identity
        ON jurisdiction_source_evidence (source, source_record_id)
        """
    )


def existing_identities(conn):
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='jurisdiction_source_evidence'"
    ).fetchone()
    if not exists:
        return set()
    return {
        row[0]
        for row in conn.execute(
            "SELECT source_record_id FROM jurisdiction_source_evidence WHERE source=?",
            (SOURCE,),
        )
    }


def upsert_rows(conn, accepted):
    for result in accepted:
        metadata = dict(result["attributes"])
        metadata["original_globalid"] = result["original_globalid"]
        conn.execute(
            """
            INSERT INTO jurisdiction_source_evidence (
                physical_stop_id, source, source_record_id, jurisdiction,
                source_latitude, source_longitude, match_method,
                match_distance_m, source_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_record_id) DO UPDATE SET
                physical_stop_id=excluded.physical_stop_id,
                jurisdiction=excluded.jurisdiction,
                source_latitude=excluded.source_latitude,
                source_longitude=excluded.source_longitude,
                match_method=excluded.match_method,
                match_distance_m=excluded.match_distance_m,
                source_metadata=excluded.source_metadata,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                result["physical_stop_id"], SOURCE, result["source_record_id"],
                JURISDICTION, result["latitude"], result["longitude"],
                result["match_method"], result["match_distance_m"],
                json.dumps(metadata, sort_keys=True, separators=(",", ":"), default=str),
            ),
        )


def validate_applied(conn, accepted):
    expected = len(accepted)
    row_count, distinct_count, empty_metadata = conn.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT source_record_id),
               SUM(CASE WHEN source_metadata IS NULL OR TRIM(source_metadata)='' THEN 1 ELSE 0 END)
        FROM jurisdiction_source_evidence WHERE source=?
        """,
        (SOURCE,),
    ).fetchone()
    if row_count != expected or distinct_count != expected or empty_metadata:
        raise RuntimeError(
            f"Post-import identity/metadata validation failed: "
            f"rows={row_count}, distinct={distinct_count}, empty={empty_metadata}"
        )
    non_pg = conn.execute(
        """
        SELECT COUNT(*) FROM jurisdiction_source_evidence e
        JOIN stop_gtfs_status g ON g.physical_stop_id=e.physical_stop_id
        LEFT JOIN stop_jurisdiction j ON j.stop_id=e.physical_stop_id
        WHERE e.source=? AND (
            g.current_gtfs<>1 OR j.state<>'MD' OR j.county<>"Prince George's"
        )
        """,
        (SOURCE,),
    ).fetchone()[0]
    if non_pg:
        raise RuntimeError(f"Post-import validation found {non_pg} non-PG rows")


def build_report(conn, features, classified):
    accepted = classified["accepted"]
    identities = {row["source_record_id"] for row in accepted}
    existing = existing_identities(conn)
    physical_counts = Counter(row["physical_stop_id"] for row in accepted)
    return {
        "source": SOURCE,
        "source_feature_count": len(features),
        "unique_source_identities": len(validate_features(features)),
        "accepted_records": len(accepted),
        "accepted_physical_stops": len(physical_counts),
        "review_records": len(classified["review"]),
        "unmatched_records": len(classified["unmatched"]),
        "non_pg_accepted_count": 0,
        "exact_id_accepted_count": sum(r["match_method"] == "exact_reg_id" for r in accepted),
        "spatial_fallback_accepted_count": sum(r["match_method"] == "unique_spatial_10m" for r in accepted),
        "match_distance_distribution": classified["distance_distribution"],
        "physical_stops_receiving_multiple_source_records": sum(n > 1 for n in physical_counts.values()),
        "current_pg_stops": classified["current_pg_count"],
        "current_pg_stops_covered": len(physical_counts),
        "current_pg_stops_uncovered": classified["current_pg_count"] - len(physical_counts),
        "expected_inserts": len(identities - existing),
        "expected_updates": len(identities & existing),
        "existing_source_rows": len(existing),
    }


def database_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def run(db_path, features, apply=False):
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    before = database_sha256(db_path)
    amenity_before = conn.execute("SELECT COUNT(*) FROM stop_amenity_evidence").fetchone()[0]
    classified = classify_features(conn, features)
    report = build_report(conn, features, classified)
    report["database_sha256_before"] = before
    if apply:
        try:
            conn.execute("BEGIN IMMEDIATE")
            setup_schema(conn)
            upsert_rows(conn, classified["accepted"])
            validate_applied(conn, classified["accepted"])
            amenity_after = conn.execute("SELECT COUNT(*) FROM stop_amenity_evidence").fetchone()[0]
            if amenity_after != amenity_before:
                raise RuntimeError("stop_amenity_evidence changed during raw import")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    conn.close()
    report["applied"] = apply
    report["stop_amenity_evidence_rows_before"] = amenity_before
    report["stop_amenity_evidence_rows_after"] = amenity_before
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
    features = fetch_features(args.url)
    report = run(args.db, features, apply=args.apply)
    output = json.dumps(report, indent=2, sort_keys=True)
    print(output)
    if args.report:
        Path(args.report).write_text(output + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
