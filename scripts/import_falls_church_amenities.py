"""Import curated positive City of Falls Church shelter-program evidence."""

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.amenities.importer import upsert_amenity_evidence


SOURCE = "FALLS_CHURCH_CITY"
JURISDICTION = "FALLS_CHURCH"
SOURCE_URL = "https://fallschurchva.gov/410/Bus-Stop-Master-Plan"
AMENITY_TYPES = ("shelter", "bench", "bikerack", "trash_can")
PROGRAM_DESCRIPTION = (
    "City of Falls Church completed Bus Stop and Bus Shelter Master Plan "
    "implementation program"
)
PROGRAM_STATEMENT = (
    "Each of the 15 constructed bus shelters contains a bench, two map "
    "cases, bike racks, and trash containers."
)

# These are intentionally fixed manual crosswalks. Do not add suffix or spatial
# fallback matching: a changed target must be reviewed and updated explicitly.
CURATED_CROSSWALKS = (
    ("w-broad-birch-eb", "W Broad / Birch, EB", 4324, "W Broad St+Birch St"),
    (
        "w-broad-chanel-terrace-eb",
        "W Broad / Chanel Terrace, EB",
        7016,
        "W Broad St+Chanel Terr",
    ),
    (
        "n-washington-columbia-nb",
        "N Washington / Columbia, NB",
        1678,
        "N Washington St+Columbia St",
    ),
    (
        "s-washington-broad-nb",
        "S Washington / Broad, NB",
        6309,
        "S Washington St+E Broad St",
    ),
    (
        "s-washington-broad-sb",
        "S Washington / Broad, SB",
        5080,
        "S Washington St+Broad St",
    ),
    (
        "n-washington-park-ave-sb",
        "N Washington / Park Ave, SB",
        1127,
        "N Washington St+Park Av",
    ),
    (
        "w-broad-lee-wb",
        "W Broad / Lee, WB",
        7068,
        "W Broad St+N Lee St",
    ),
    (
        "w-broad-little-falls-eb",
        "W Broad / Little Falls, EB",
        7249,
        "W Broad St+Little Falls St",
    ),
)

# Documented quarantine only. These entries never flow into evidence_rows().
QUARANTINED_PLACEMENTS = (
    "E Broad / S Washington, EB",
    "E Broad / Fairfax Drive, EB",
    "E Broad / Roosevelt Street, EB",
    "E Broad / Roosevelt Street, WB",
    "Roosevelt Boulevard / Roosevelt Street, EB",
    "Roosevelt Boulevard / Roosevelt Street, WB",
    "Stated fifteenth shelter missing from the displayed list",
)


def database_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_source_identities():
    identities = [row[0] for row in CURATED_CROSSWALKS]
    if any(not identity.strip() for identity in identities):
        raise RuntimeError("Curated source identities must be nonempty")
    if len(identities) != len(set(identities)):
        raise RuntimeError("Curated source identities must be unique")


def validate_crosswalks(conn):
    validate_source_identities()
    validated = []
    for source_record_id, location, stop_id, expected_name in CURATED_CROSSWALKS:
        stop = conn.execute(
            "SELECT primary_name FROM physical_stops WHERE id=?", (stop_id,)
        ).fetchone()
        if stop is None:
            raise RuntimeError(f"Curated physical stop {stop_id} does not exist")
        if stop[0] != expected_name:
            raise RuntimeError(
                f"Curated physical stop {stop_id} changed name: "
                f"expected {expected_name!r}, found {stop[0]!r}"
            )
        status = conn.execute(
            "SELECT current_gtfs FROM stop_gtfs_status WHERE physical_stop_id=?",
            (stop_id,),
        ).fetchone()
        if status is None:
            raise RuntimeError(f"Curated physical stop {stop_id} has no GTFS status")
        if status[0] != 1:
            raise RuntimeError(f"Curated physical stop {stop_id} is not current")
        geography = conn.execute(
            """SELECT state, county, municipality FROM stop_jurisdiction
               WHERE stop_id=?""",
            (stop_id,),
        ).fetchone()
        if geography is None or tuple(geography) != (
            "VA",
            "Falls Church",
            "Falls Church",
        ):
            raise RuntimeError(
                f"Curated physical stop {stop_id} is not in independent "
                "City of Falls Church"
            )
        validated.append(
            {
                "source_record_id": source_record_id,
                "source_location": location,
                "physical_stop_id": stop_id,
                "canonical_name": expected_name,
            }
        )
    return validated


def evidence_rows(validated):
    rows = []
    for record in validated:
        metadata = json.dumps(
            {
                "official_directional_source_location": record["source_location"],
                "canonical_physical_stop_id": record["physical_stop_id"],
                "official_city_source_url": SOURCE_URL,
                "program_description": PROGRAM_DESCRIPTION,
                "constructed_shelter_contents_statement": PROGRAM_STATEMENT,
                "source_program_completion_context": (
                    "Official page states project is complete; construction "
                    "occurred August 2016 through November 2017."
                ),
                "curated_match": True,
                "matching_method": "directional_intersection_manual_crosswalk",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        for amenity_type in AMENITY_TYPES:
            rows.append(
                {
                    **record,
                    "amenity_type": amenity_type,
                    "present": 1,
                    "value": "yes",
                    "raw_value": "CONSTRUCTED_SHELTER_CONTENTS",
                    "source_metadata": metadata,
                }
            )
    return rows


def existing_keys(conn):
    return {
        tuple(row)
        for row in conn.execute(
            """SELECT physical_stop_id,source_record_id,amenity_type
               FROM stop_amenity_evidence WHERE source=?""",
            (SOURCE,),
        )
    }


def upsert_rows(conn, rows):
    for row in rows:
        upsert_amenity_evidence(
            conn,
            physical_stop_id=row["physical_stop_id"],
            source=SOURCE,
            source_record_id=row["source_record_id"],
            amenity_type=row["amenity_type"],
            present=1,
            confidence="high",
            match_distance_m=None,
            notes="Curated City of Falls Church completed shelter-program record",
            jurisdiction=JURISDICTION,
            value="yes",
            raw_value=row["raw_value"],
            source_metadata=row["source_metadata"],
        )


def validate_applied(conn, expected_rows):
    expected_keys = {
        (row["physical_stop_id"], row["source_record_id"], row["amenity_type"])
        for row in expected_rows
    }
    actual_keys = existing_keys(conn)
    duplicates = conn.execute(
        """SELECT COUNT(*) FROM (
             SELECT physical_stop_id,source,source_record_id,amenity_type,COUNT(*) n
             FROM stop_amenity_evidence WHERE source=?
             GROUP BY 1,2,3,4 HAVING n>1)""",
        (SOURCE,),
    ).fetchone()[0]
    invalid_types = conn.execute(
        """SELECT COUNT(*) FROM stop_amenity_evidence
           WHERE source=? AND amenity_type NOT IN
             ('shelter','bench','bikerack','trash_can')""",
        (SOURCE,),
    ).fetchone()[0]
    nonpositive = conn.execute(
        """SELECT COUNT(*) FROM stop_amenity_evidence
           WHERE source=? AND (present IS NOT 1 OR LOWER(value) IS NOT 'yes')""",
        (SOURCE,),
    ).fetchone()[0]
    invalid_targets = conn.execute(
        """SELECT COUNT(*) FROM stop_amenity_evidence e
           LEFT JOIN stop_gtfs_status s ON s.physical_stop_id=e.physical_stop_id
           LEFT JOIN stop_jurisdiction j ON j.stop_id=e.physical_stop_id
           WHERE e.source=? AND (
             s.current_gtfs IS NOT 1 OR j.state IS NOT 'VA'
             OR j.county IS NOT 'Falls Church'
             OR j.municipality IS NOT 'Falls Church')""",
        (SOURCE,),
    ).fetchone()[0]
    if actual_keys != expected_keys:
        raise RuntimeError("Applied source rows do not equal the curated evidence set")
    if duplicates or invalid_types or nonpositive or invalid_targets:
        raise RuntimeError(
            "Post-import validation failed: "
            f"duplicates={duplicates}, invalid_types={invalid_types}, "
            f"nonpositive={nonpositive}, invalid_targets={invalid_targets}"
        )


def build_report(conn, validated, rows):
    prior_keys = existing_keys(conn)
    desired_keys = {
        (row["physical_stop_id"], row["source_record_id"], row["amenity_type"])
        for row in rows
    }
    counts = {amenity: 0 for amenity in AMENITY_TYPES}
    for row in rows:
        counts[row["amenity_type"]] += 1
    return {
        "source": SOURCE,
        "jurisdiction": JURISDICTION,
        "validated_curated_records": len(validated),
        "expected_evidence_rows": len(rows),
        "positive_rows_by_amenity": counts,
        "negative_rows": sum(row["present"] != 1 for row in rows),
        "non_current_accepted": 0,
        "non_falls_church_accepted": 0,
        "duplicate_identities": len(rows) - len(desired_keys),
        "existing_source_rows": len(prior_keys),
        "expected_inserts": len(desired_keys - prior_keys),
        "expected_updates": len(desired_keys & prior_keys),
        "quarantined_placements": list(QUARANTINED_PLACEMENTS),
        "quarantined_count": len(QUARANTINED_PLACEMENTS),
    }


def run(db_path, apply=False):
    db_path = Path(db_path)
    before_hash = database_sha256(db_path)
    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        if apply:
            conn.execute("BEGIN IMMEDIATE")
        validated = validate_crosswalks(conn)
        rows = evidence_rows(validated)
        report = build_report(conn, validated, rows)
        if apply:
            upsert_rows(conn, rows)
            validate_applied(conn, rows)
            conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()
    report["applied"] = apply
    report["database_sha256_before"] = before_hash
    report["database_sha256_after"] = database_sha256(db_path)
    return report


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    report = run(args.db, apply=args.apply)
    output = json.dumps(report, indent=2, sort_keys=True)
    print(output)
    if args.report:
        Path(args.report).write_text(output + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
