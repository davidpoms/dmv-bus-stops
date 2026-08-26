"""Explicit-database Physical Stop Identity V2 cutover orchestrator."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.active.reset_v2_test_contributions import CONFIRMATION, TABLES, reset_test_contributions
from src.amenities.review_priority import rebuild_review_priority
from src.amenities.status_synthesis import rebuild_stop_amenity_status
from src.assessment.calculate_recommendation_confidence import calculate_confidence
from src.assessment.create_opportunity_assessments import create_assessments
from src.assessment.create_project_priorities import create_project_priorities
from src.assessment.generate_bench_installation_candidates import generate_candidates
from src.assessment.generate_impact_summary import generate_impact_summary
from src.assessment.generate_improvement_recommendations import generate_recommendations
from src.assessment.generate_seating_improvement_opportunities import generate_opportunities
from src.assessment.score_improvement_opportunities import score_opportunities
from src.processing.evidence_attribution_v2 import (
    apply_manifest_attribution, preflight_manifest_attribution,
)
from src.processing.heading_audit import maximum_heading_separation
from src.processing.physical_stop_geography import (
    preflight_manifest_geography, recompute_geography,
)
from src.processing.physical_stop_v2_cutover import (
    CUTOVER_VERSION, apply_reviewed_proposal, cutover_state, validate_cutover,
    validate_proposal_gate,
)
from src.processing.physical_stop_v2_proposal import generate_manifest
from src.review.create_review_queue import create_review_queue
from src.scoring.calculate_stop_priority import calculate_scores
from src.processing.serving_directions import load_member_directions


DEFAULT_PRODUCTION_DB = (ROOT / "src" / "database" / "dmv_bus_stops.db").resolve()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require_safe_target(path, *, allow_production=False):
    target = Path(path).resolve()
    if target == DEFAULT_PRODUCTION_DB and not allow_production:
        raise ValueError("refusing repository production database; use a fresh explicit copy")
    if not target.is_file():
        raise FileNotFoundError(target)
    return target


def migrate_review_schema(path):
    """Run the supported idempotent review migration against this exact DB."""
    previous = os.environ.get("DMV_BUS_STOPS_DB")
    os.environ["DMV_BUS_STOPS_DB"] = str(path)
    try:
        runpy.run_path(str(ROOT / "scripts" / "active" / "create_review_tables.py"),
                       run_name="v2_cutover_review_schema")
    finally:
        if previous is None:
            os.environ.pop("DMV_BUS_STOPS_DB", None)
        else:
            os.environ["DMV_BUS_STOPS_DB"] = previous


def table_counts(conn):
    tables = [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {table: conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in tables if not table.startswith("sqlite_")}


def heading_audit(conn):
    directions = load_member_directions(conn)
    active = {row[0] for row in conn.execute(
        "SELECT physical_stop_id FROM stop_gtfs_status WHERE current_gtfs=1")}
    counts = {"no_heading": 0, "one_heading": 0, "multiple_headings": 0,
              "contradictory_135": 0, "opposed_160": 0}
    opposed = []
    for stop_id in sorted(active):
        headings = sorted({item["heading_degrees"]
                           for values in directions.get(stop_id, {}).values()
                           for item in values})
        counts["no_heading" if not headings else
               "one_heading" if len(headings) == 1 else "multiple_headings"] += 1
        separation = maximum_heading_separation(headings)
        if separation >= 135:
            counts["contradictory_135"] += 1
        if separation >= 160:
            counts["opposed_160"] += 1
            opposed.append({"stop_id": stop_id, "headings": headings})
    return {"counts": counts, "opposed_stops": opposed}


def acceptance_results(conn):
    stop_935 = conn.execute("""SELECT ed.successor_physical_stop_id
        FROM physical_stop_identity_edges ed WHERE ed.predecessor_physical_stop_id=935
        ORDER BY 1""").fetchall()
    attribution = {row[0]: row[1] for row in conn.execute("""SELECT
        CASE WHEN a.physical_stop_id IS NULL THEN 'unresolved'
             ELSE COALESCE(s.identity_status,'orphan') END,COUNT(*)
        FROM physical_stop_evidence_attribution a
        LEFT JOIN physical_stop_identity_state s ON s.physical_stop_id=a.physical_stop_id
        WHERE a.attribution_version=? GROUP BY 1""", (CUTOVER_VERSION,))}
    return {
        "stop_935_status": conn.execute("""SELECT identity_status
            FROM physical_stop_identity_state WHERE physical_stop_id=935""").fetchone()[0],
        "stop_935_successors": [row[0] for row in stop_935],
        "manual_exceptions": conn.execute("""SELECT physical_stop_id,identity_status
            FROM physical_stop_identity_state WHERE physical_stop_id IN
            (406,2231,4468,5196,6080) ORDER BY 1""").fetchall(),
        "parent_870_successor_geography": conn.execute("""SELECT
            ed.successor_physical_stop_id,j.state,j.county,j.municipality,j.dc_ward,j.dc_anc
            FROM physical_stop_identity_edges ed LEFT JOIN stop_jurisdiction j
            ON j.stop_id=ed.successor_physical_stop_id
            WHERE ed.predecessor_physical_stop_id=870 ORDER BY 1""").fetchall(),
        "attribution_identity_state": attribution,
    }


def rebuild_gtfs_status(conn):
    with conn:
        conn.execute("DROP TABLE IF EXISTS stop_gtfs_status")
        conn.execute("""CREATE TABLE stop_gtfs_status(
            physical_stop_id INTEGER PRIMARY KEY,current_gtfs INTEGER NOT NULL,
            route_served INTEGER NOT NULL,gtfs_stop_count INTEGER NOT NULL,
            route_count INTEGER NOT NULL,status TEXT NOT NULL,source TEXT NOT NULL,
            checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        conn.execute("""INSERT INTO stop_gtfs_status
            (physical_stop_id,current_gtfs,route_served,gtfs_stop_count,route_count,status,source)
            SELECT ps.id,COUNT(DISTINCT gm.gtfs_stop_id)>0,COUNT(DISTINCT sr.id)>0,
                   COUNT(DISTINCT gm.gtfs_stop_id),COUNT(DISTINCT r.id),
                   CASE WHEN COUNT(DISTINCT gm.gtfs_stop_id)>0 THEN 'current' ELSE 'not_current' END,
                   'current GTFS stop membership'
            FROM physical_stops ps
            LEFT JOIN physical_stop_members pm ON pm.physical_stop_id=ps.id
            LEFT JOIN gtfs_stop_map gm ON gm.bus_stop_id=pm.bus_stop_id
            LEFT JOIN stop_routes sr ON sr.stop_id=pm.bus_stop_id
            LEFT JOIN routes r ON r.id=sr.route_id GROUP BY ps.id""")


def rebuild_compatibility_outputs(conn):
    """Refresh compatibility tables still read by current API/dashboard code."""
    with conn:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='stop_transit_evidence'").fetchone():
            conn.execute("DELETE FROM stop_transit_evidence")
            conn.execute("""INSERT INTO stop_transit_evidence(stop_id,gtfs_bus_stop,route_count,source)
                SELECT physical_stop_id,current_gtfs,route_count,'stop_gtfs_status V2 compatibility'
                FROM stop_gtfs_status WHERE current_gtfs=1""")
        summary_specs = (
            ("county_summary", "state,county", "state IS NOT NULL AND county IS NOT NULL"),
            ("municipality_summary", "state,county,municipality",
             "state IS NOT NULL AND municipality IS NOT NULL"),
            ("dc_ward_summary", "dc_ward", "dc_ward IS NOT NULL"),
            ("dc_anc_summary", "dc_anc", "dc_anc IS NOT NULL"),
        )
        for table, columns, predicate in summary_specs:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                continue
            output_columns = {"dc_ward_summary": "ward", "dc_anc_summary": "anc"}.get(table, columns)
            conn.execute(f"DELETE FROM {table}")
            conn.execute(f"""INSERT INTO {table}({output_columns},stop_count)
                SELECT {columns},COUNT(*) FROM stop_jurisdiction j
                JOIN stop_gtfs_status s ON s.physical_stop_id=j.stop_id AND s.current_gtfs=1
                WHERE {predicate} GROUP BY {columns}""")


def rebuild_products(path):
    with sqlite3.connect(path) as conn:
        rebuild_gtfs_status(conn)
        rebuild_compatibility_outputs(conn)
        rebuild_stop_amenity_status(conn)
        rebuild_review_priority(conn)
    calculate_scores(path)
    create_assessments(path)
    score_opportunities(path)
    generate_opportunities(path)
    generate_candidates(path)
    generate_recommendations(path)
    calculate_confidence(path)
    generate_impact_summary(path)
    create_project_priorities(path)
    create_review_queue(path)


def validate_database(conn):
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
    retired_derived = {}
    for table, column in (
        ("stop_amenity_status", "physical_stop_id"),
        ("stop_amenity_review_priority", "physical_stop_id"),
        ("opportunity_assessments", "physical_stop_id"),
        ("improvement_opportunities", "physical_stop_id"),
        ("seating_improvement_opportunities", "physical_stop_id"),
        ("bench_installation_candidates", "physical_stop_id"),
        ("improvement_recommendations", "physical_stop_id"),
        ("stop_improvement_impact", "physical_stop_id"),
        ("recommendation_confidence", "physical_stop_id"),
        ("project_priorities", "physical_stop_id"),
        ("review_queue", "physical_stop_id"),
        ("stop_priority_snapshots", "stop_id"),
        ("stop_transit_evidence", "stop_id"),
    ):
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
            retired_derived[table] = conn.execute(f"""SELECT COUNT(*) FROM {table} d
                JOIN physical_stop_identity_state s ON s.physical_stop_id=d.{column}
                WHERE s.identity_status='retired'""").fetchone()[0]
    active_retired = conn.execute("""SELECT COUNT(*) FROM stop_gtfs_status g JOIN
        physical_stop_identity_state s ON s.physical_stop_id=g.physical_stop_id
        WHERE g.current_gtfs=1 AND s.identity_status='retired'""").fetchone()[0]
    stale = {table: count for table, count in retired_derived.items() if count}
    if integrity != "ok" or foreign_keys or active_retired or stale:
        raise RuntimeError(f"database invariant failure: integrity={integrity}, fk={len(foreign_keys)}, active_retired={active_retired}")
    return {"integrity_check": integrity, "foreign_key_violations": len(foreign_keys),
            "active_retired": active_retired, "retired_derived_rows": retired_derived}


def run(path, *, apply=False, reset_contributions=True, allow_production=False):
    target = require_safe_target(path, allow_production=allow_production)
    report = {"database": str(target), "sha256_before": sha256(target), "mode": "apply" if apply else "plan"}
    with sqlite3.connect(target) as conn:
        state = cutover_state(conn)
        report["cutover_state_before"] = state
        if state == "pristine":
            manifest = generate_manifest(conn, validate=True)
            report["proposal_gate"] = validate_proposal_gate(manifest)
            report["evidence_preflight"] = preflight_manifest_attribution(conn, manifest)
            geography = preflight_manifest_geography(conn, manifest)
            report["geography_preflight"] = {
                "coverage": geography["coverage"],
                "parent_child_differences": len(geography["parent_child_differences"]),
                "sibling_crossing_parents": len(geography["child_geography_crossings"]),
            }
        elif state == "applied":
            manifest = None
            report["proposal_gate"] = "already applied; verified by lineage"
        else:
            raise RuntimeError("partial cutover state; refusing to continue")
        report["counts_before"] = table_counts(conn)
        report["heading_audit_before"] = heading_audit(conn)
        if not apply:
            return report
        migrate_review_schema(target)
        if manifest is not None:
            result = apply_reviewed_proposal(conn, manifest, confirm=True)
            report["identity_apply"] = {**result,
                "successor_id_range": [min(result["successor_ids"]), max(result["successor_ids"])]}
            current_ids = result["successor_ids"]
            report["contribution_reset_before"] = {
                table: report["counts_before"].get(table, 0) for table in TABLES}
            if reset_contributions:
                report["contribution_reset_deleted"] = reset_test_contributions(
                    conn, confirmation=CONFIRMATION, database_path=target)
            report["geography_recomputed"] = recompute_geography(conn, current_ids)
            report["evidence_attribution"] = apply_manifest_attribution(conn, manifest)
        else:
            report["identity_apply"] = apply_reviewed_proposal(conn, confirm=True)
        validate_cutover(conn)
    rebuild_products(target)
    with sqlite3.connect(target) as conn:
        report["identity_validation"] = validate_cutover(conn)
        report["database_validation"] = validate_database(conn)
        report["counts_after"] = table_counts(conn)
        report["active_stops"] = conn.execute(
            "SELECT COUNT(*) FROM stop_gtfs_status WHERE current_gtfs=1").fetchone()[0]
        report["heading_audit_after"] = heading_audit(conn)
        report["acceptance"] = acceptance_results(conn)
    report["sha256_after"] = sha256(target)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--skip-test-contribution-reset", action="store_true")
    parser.add_argument("--allow-production-database", action="store_true",
                        help="production-only emergency override; never use for rehearsal")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report = run(args.db, apply=args.apply,
                 reset_contributions=not args.skip_test_contribution_reset,
                 allow_production=args.allow_production_database)
    output = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
