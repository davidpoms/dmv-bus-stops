"""Migrate amenity evidence uniqueness to source-record identity."""

import argparse
import os
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB = Path(os.environ.get(
    "DMV_BUS_STOPS_DB", ROOT / "src" / "database" / "dmv_bus_stops.db"
))
OLD_INDEX = "idx_stop_amenity_evidence_unique"
NEW_INDEX = "idx_stop_amenity_evidence_identity_unique"
SUPPORTED_SOURCES = (
    "ALEXANDRIA",
    "ARLINGTON_COUNTY",
    "FAIRFAX_COUNTY",
    "MONTGOMERY_COUNTY_WMATA",
    "DDOT_ARCGIS",
)
NEW_COLUMNS = (
    "physical_stop_id",
    "source",
    "source_record_id",
    "amenity_type",
)


def audit(conn):
    placeholders = ",".join("?" for _ in SUPPORTED_SOURCES)
    collisions = conn.execute(
        f"""
        SELECT physical_stop_id, source, source_record_id, amenity_type,
               COUNT(*) AS row_count
        FROM stop_amenity_evidence
        WHERE source IN ({placeholders})
        GROUP BY physical_stop_id, source, source_record_id, amenity_type
        HAVING COUNT(*) > 1
        """,
        SUPPORTED_SOURCES,
    ).fetchall()
    missing = conn.execute(
        f"""
        SELECT source, COUNT(*) AS row_count
        FROM stop_amenity_evidence
        WHERE source IN ({placeholders})
          AND (
              source_record_id IS NULL
              OR TRIM(source_record_id) = ''
              OR LOWER(TRIM(source_record_id)) IN ('none', 'null', 'nan')
          )
        GROUP BY source
        """,
        SUPPORTED_SOURCES,
    ).fetchall()
    legacy = conn.execute(
        """
        SELECT
            COUNT(*) AS rows,
            SUM(CASE WHEN source_record_id IS NULL
                      OR TRIM(source_record_id) = ''
                      OR LOWER(TRIM(source_record_id)) IN ('none','null','nan')
                     THEN 1 ELSE 0 END) AS missing_ids
        FROM stop_amenity_evidence
        WHERE source = 'DDOT'
        """
    ).fetchone()
    return {
        "supported_collisions": collisions,
        "supported_missing_ids": missing,
        "legacy_ddot": legacy,
    }


def index_columns(conn, index_name):
    return tuple(row[2] for row in conn.execute(f"PRAGMA index_info({index_name})"))


def migrate(conn):
    result = audit(conn)
    if result["supported_collisions"] or result["supported_missing_ids"]:
        raise RuntimeError(f"Supported-source safety checks failed: {result}")

    existing = {row[1]: index_columns(conn, row[1])
                for row in conn.execute("PRAGMA index_list(stop_amenity_evidence)")}
    if NEW_INDEX in existing and existing[NEW_INDEX] == NEW_COLUMNS:
        return result
    if OLD_INDEX not in existing or existing[OLD_INDEX] != (
        "physical_stop_id", "source", "amenity_type"
    ):
        raise RuntimeError(f"Unexpected existing index layout: {existing}")

    with conn:
        conn.execute(f"DROP INDEX {OLD_INDEX}")
        conn.execute(
            f"""CREATE UNIQUE INDEX {NEW_INDEX}
                ON stop_amenity_evidence
                (physical_stop_id, source, source_record_id, amenity_type)"""
        )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    conn = sqlite3.connect(args.db)
    result = audit(conn)
    print("Supported full-key collisions:", len(result["supported_collisions"]))
    print("Supported missing identities:", len(result["supported_missing_ids"]))
    print("Legacy DDOT rows/missing identities:", tuple(result["legacy_ddot"]))
    if args.apply:
        migrate(conn)
        print("Migration applied")
    else:
        print("DRY RUN: no schema changes")
    conn.close()


if __name__ == "__main__":
    main()
