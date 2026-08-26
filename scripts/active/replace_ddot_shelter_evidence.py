"""Atomically replace contaminated DDOT evidence with clean ArcGIS evidence.

Default behavior is read-only preflight. Database mutation requires --apply.
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from scripts.import_ddot_arcgis_amenities import (
    DB,
    JURISDICTION,
    SOURCE,
    analyze_features,
    build_report,
    fetch_features,
)
from src.amenities.importer import upsert_amenity_evidence

DEFAULT_DB = Path(os.environ.get("DMV_BUS_STOPS_DB", DB))


BASELINE = {
    "source_feature_count": 887,
    "accepted_count": 659,
    "review_count": 137,
    "unmatched_count": 91,
    "deletion_candidate_count": 1684,
    "preserved_legacy_ddot_count": 79,
    "historical_table_count": 1884,
}
LEGACY_STATUSES = (
    "CONFIRMED_ACTIVE",
    "API_ONLY_ACTIVE_STOP",
    "ROUTE_PRESENT",
    "NO_ROUTE",
    "POSSIBLE_NEW_DDOT_SHELTER",
    "REMOVED_BUT_ROUTE_ACTIVE",
)


def legacy_predicate(alias="e"):
    placeholders = ",".join("?" for _ in LEGACY_STATUSES)
    return f"""
        {alias}.source = 'DDOT'
        AND {alias}.amenity_type = 'shelter'
        AND {alias}.raw_value IN ({placeholders})
        AND EXISTS (
            SELECT 1 FROM stop_ddot_shelter_evidence d
            WHERE d.physical_stop_id = {alias}.physical_stop_id
              AND CAST(d.ddot_id AS TEXT) = CAST({alias}.source_record_id AS TEXT)
        )
    """


def table_fingerprint(conn, table):
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
    payload = json.dumps(rows, separators=(",", ":"), default=str).encode("utf-8")
    return len(rows), hashlib.sha256(payload).hexdigest()


def database_snapshot(conn):
    deletion_count = conn.execute(
        f"SELECT COUNT(*) FROM stop_amenity_evidence e WHERE {legacy_predicate()}",
        LEGACY_STATUSES,
    ).fetchone()[0]
    preserved_count = conn.execute(
        f"SELECT COUNT(*) FROM stop_amenity_evidence e WHERE e.source='DDOT' AND NOT ({legacy_predicate()})",
        LEGACY_STATUSES,
    ).fetchone()[0]
    historical_count, historical_hash = table_fingerprint(
        conn, "stop_ddot_shelter_evidence"
    )
    return {
        "deletion_candidate_count": deletion_count,
        "preserved_legacy_ddot_count": preserved_count,
        "historical_table_count": historical_count,
        "historical_table_hash": historical_hash,
    }


def validate_source_report(report):
    failures = []
    if report["distinct_source_identity_count"] != report["source_feature_count"]:
        failures.append("source identities are missing")
    if report["duplicate_generated_identities"]:
        failures.append("duplicate generated source identities")
    if report["accepted_non_dc_count"]:
        failures.append("accepted non-DC match")
    matches_1000087 = [
        result for result in report["results"]
        if str(result.get("attributes", {}).get("DDOT_ID")) == "1000087"
        and result.get("status") == "accepted"
    ]
    stop_11 = any(result.get("physical_stop_id") == 11 for result in matches_1000087)
    stop_5136 = any(result.get("physical_stop_id") == 5136 for result in matches_1000087)
    if not stop_11 or stop_5136:
        failures.append("DDOT 1000087 regression failed")
    if failures:
        raise RuntimeError("; ".join(failures))
    return {"stop_11": stop_11, "stop_5136": stop_5136}


def preflight(db, features):
    results = analyze_features(features, db)
    source_report = build_report(features, results)
    regression = validate_source_report(source_report)
    conn = sqlite3.connect(f"file:{Path(db).resolve()}?mode=ro", uri=True)
    snapshot = database_snapshot(conn)
    conn.close()
    deltas = {
        key: source_report[key] - BASELINE[key]
        for key in ("source_feature_count", "accepted_count", "review_count", "unmatched_count")
    }
    deltas.update({
        key: snapshot[key] - BASELINE[key]
        for key in ("deletion_candidate_count", "preserved_legacy_ddot_count", "historical_table_count")
    })
    accepted = [result for result in results if result["status"] == "accepted"]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_feature_count": source_report["source_feature_count"],
        "accepted_count": source_report["accepted_count"],
        "review_count": source_report["review_count"],
        "unmatched_count": source_report["unmatched_count"],
        "identity_count": source_report["distinct_source_identity_count"],
        "duplicate_generated_identities": source_report["duplicate_generated_identities"],
        "accepted_physical_stop_count": len({r["physical_stop_id"] for r in accepted}),
        "accepted_asset_count": len(accepted),
        "accepted_non_dc_count": source_report["accepted_non_dc_count"],
        "deletion_candidate_count": snapshot["deletion_candidate_count"],
        "preserved_legacy_ddot_count": snapshot["preserved_legacy_ddot_count"],
        "historical_table_count": snapshot["historical_table_count"],
        "historical_table_hash": snapshot["historical_table_hash"],
        "baseline_deltas": deltas,
        "regression_1000087": regression,
        "transaction_status": "dry_run_no_database_mutation",
        "rollback_reason": None,
        "results": results,
    }


def validate_clean_rows(conn, accepted_count):
    checks = {
        "row_count": conn.execute(
            "SELECT COUNT(*) FROM stop_amenity_evidence WHERE source=?", (SOURCE,)
        ).fetchone()[0],
        "non_dc": conn.execute(
            """SELECT COUNT(*) FROM stop_amenity_evidence e
               JOIN physical_stops p ON p.id=e.physical_stop_id
               WHERE e.source=? AND p.state<>'DC'""", (SOURCE,)
        ).fetchone()[0],
        "duplicates": conn.execute(
            """SELECT COUNT(*) FROM (
               SELECT physical_stop_id,source,source_record_id,amenity_type,COUNT(*) n
               FROM stop_amenity_evidence WHERE source=? GROUP BY 1,2,3,4 HAVING n>1)""",
            (SOURCE,),
        ).fetchone()[0],
        "invalid": conn.execute(
            """SELECT COUNT(*) FROM stop_amenity_evidence
               WHERE source=? AND (source_record_id IS NULL OR TRIM(source_record_id)=''
               OR LOWER(TRIM(source_record_id)) IN ('none','null','nan') OR present<>1
               OR amenity_type<>'shelter' OR jurisdiction<>?)""",
            (SOURCE, JURISDICTION),
        ).fetchone()[0],
    }
    if checks != {"row_count": accepted_count, "non_dc": 0, "duplicates": 0, "invalid": 0}:
        raise RuntimeError(f"clean evidence validation failed: {checks}")


def apply_replacement(
    db,
    report,
    acknowledge_feed_change=False,
    acknowledge_deletion_change=False,
    failure_stage=None,
):
    feed_changed = any(
        report["baseline_deltas"][key] != 0
        for key in ("source_feature_count", "accepted_count")
    )
    if feed_changed and not acknowledge_feed_change:
        raise RuntimeError("material feed count change requires acknowledgement")
    if report["baseline_deltas"]["deletion_candidate_count"] != 0 and not acknowledge_deletion_change:
        raise RuntimeError("legacy deletion-set change requires acknowledgement")

    conn = sqlite3.connect(db, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        for result in report["results"]:
            if result["status"] != "accepted":
                continue
            state = conn.execute(
                "SELECT state FROM physical_stops WHERE id=?",
                (result["physical_stop_id"],),
            ).fetchone()
            if result.get("state") != "DC" or state is None or state[0] != "DC":
                raise RuntimeError("accepted DDOT record is not attached to DC")
            attrs = result["attributes"]
            metadata = dict(attrs)
            metadata.update({
                "source_latitude": result["latitude"],
                "source_longitude": result["longitude"],
                "match_policy": "nearest_dc_physical_stop",
            })
            upsert_amenity_evidence(
                conn, result["physical_stop_id"], SOURCE,
                result["source_record_id"], "shelter", 1,
                confidence=result["confidence"],
                match_distance_m=result["distance_m"],
                notes=attrs.get("Sales_Address"), jurisdiction=JURISDICTION,
                value="yes", raw_value="published_shelter_asset",
                source_metadata=json.dumps(metadata, sort_keys=True, default=str),
            )
        if failure_stage in {"during_insertion", "after_insertion"}:
            raise RuntimeError(f"injected failure: {failure_stage}")
        validate_clean_rows(conn, report["accepted_count"])
        before_cleanup = database_snapshot(conn)
        if before_cleanup["deletion_candidate_count"] != report["deletion_candidate_count"]:
            raise RuntimeError("deletion set changed after preflight")
        cursor = conn.execute(
            f"DELETE FROM stop_amenity_evidence AS e WHERE {legacy_predicate()}",
            LEGACY_STATUSES,
        )
        if cursor.rowcount != report["deletion_candidate_count"]:
            raise RuntimeError("deleted row count differs from preflight")
        if failure_stage == "after_cleanup":
            raise RuntimeError("injected failure: after_cleanup")
        validate_clean_rows(conn, report["accepted_count"])
        after_cleanup = database_snapshot(conn)
        if after_cleanup["deletion_candidate_count"] != 0:
            raise RuntimeError("targeted legacy contamination remains")
        if after_cleanup["preserved_legacy_ddot_count"] != report["preserved_legacy_ddot_count"]:
            raise RuntimeError("ambiguous legacy evidence was not preserved")
        if (after_cleanup["historical_table_count"] != report["historical_table_count"]
                or after_cleanup["historical_table_hash"] != report["historical_table_hash"]):
            raise RuntimeError("historical DDOT table changed")
        conn.execute("COMMIT")
        return "committed"
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def public_report(report):
    return {key: value for key, value in report.items() if key != "results"}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--acknowledge-feed-change", action="store_true")
    parser.add_argument("--acknowledge-deletion-change", action="store_true")
    args = parser.parse_args(argv)
    report = preflight(args.db, fetch_features())
    if args.apply:
        try:
            report["transaction_status"] = apply_replacement(
                args.db, report,
                args.acknowledge_feed_change,
                args.acknowledge_deletion_change,
            )
        except Exception as exc:
            report["transaction_status"] = "rolled_back_or_not_started"
            report["rollback_reason"] = str(exc)
            if args.report:
                args.report.write_text(json.dumps(public_report(report), indent=2), encoding="utf-8")
            raise
    if args.report:
        args.report.write_text(json.dumps(public_report(report), indent=2), encoding="utf-8")
    print(json.dumps(public_report(report), indent=2))


if __name__ == "__main__":
    main()
