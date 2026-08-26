"""Transactional application and validation for the reviewed V2 split proposal."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from src.processing.physical_stop_identity_v2 import (
    MANUAL_EXCEPTIONS, allocate_successor_ids, ensure_identity_schema,
)
from src.processing.physical_stop_v2_proposal import (
    EXPECTED_CHILD_COUNT, EXPECTED_PARENT_COUNT, PROPOSAL_VERSION,
    generate_manifest, manifest_sha256,
)


EXPECTED_SHA256 = "A21D2223DBC08C6D6327C7072404B8B9912C17898AA91282511F2A4B8B724D23"
CUTOVER_VERSION = "physical-stop-v2-cutover-1"


def validate_proposal_gate(manifest):
    actual = {
        "version": manifest.get("proposal_version"),
        "parents": manifest.get("automatic_parent_count"),
        "children": manifest.get("child_group_count"),
        "manual_exceptions": manifest.get("manual_exceptions"),
        "sha256": manifest_sha256(manifest),
    }
    expected = {
        "version": PROPOSAL_VERSION,
        "parents": EXPECTED_PARENT_COUNT,
        "children": EXPECTED_CHILD_COUNT,
        "manual_exceptions": sorted(MANUAL_EXCEPTIONS),
        "sha256": EXPECTED_SHA256,
    }
    differences = {key: {"expected": expected[key], "actual": actual[key]}
                   for key in expected if actual[key] != expected[key]}
    if differences:
        raise ValueError(f"proposal gate failed: {json.dumps(differences, sort_keys=True)}")
    return actual


def cutover_state(conn):
    exists = conn.execute("""SELECT 1 FROM sqlite_master WHERE type='table'
        AND name='physical_stop_identity_events'""").fetchone()
    if not exists:
        return "pristine"
    events = conn.execute("SELECT COUNT(*) FROM physical_stop_identity_events WHERE migration_version=?",
                          (CUTOVER_VERSION,)).fetchone()[0]
    if events == 0:
        return "pristine"
    if events == EXPECTED_PARENT_COUNT:
        return "applied"
    return "partial"


def apply_reviewed_proposal(conn, manifest=None, *, confirm=False, now=None):
    """Apply the canonical proposal atomically; never infer a different split."""
    if not confirm:
        raise ValueError("cutover application requires confirm=True")
    state = cutover_state(conn)
    if state == "applied":
        validate_cutover(conn)
        return {"already_applied": True, "retired_parents": 0,
                "successors_created": 0, "successor_ids": []}
    if state == "partial":
        raise RuntimeError("partial V2 cutover state detected")
    manifest = manifest or generate_manifest(conn, validate=True)
    validate_proposal_gate(manifest)
    groups = [
        (parent["predecessor_physical_stop_id"], child["member_bus_stop_ids"])
        for parent in manifest["parents"] for child in parent["proposed_children"]
    ]
    allocation = allocate_successor_ids(conn, groups)
    timestamp = now or datetime.now(timezone.utc).isoformat()
    with conn:
        ensure_identity_schema(conn)
        for manual_id in sorted(MANUAL_EXCEPTIONS):
            conn.execute("""UPDATE physical_stop_identity_state SET
                identity_status='manual_exception',updated_at=? WHERE physical_stop_id=?""",
                         (timestamp, manual_id))
        for sequence, parent in enumerate(manifest["parents"], 1):
            predecessor = parent["predecessor_physical_stop_id"]
            cursor = conn.execute("""INSERT INTO physical_stop_identity_events
                (migration_version,event_sequence,event_type,reason_code,reason_json,effective_at)
                VALUES (?,?,?,?,?,?)""", (
                    CUTOVER_VERSION, sequence, "split", parent["classification"],
                    json.dumps({"proposal_version": PROPOSAL_VERSION,
                                "proposal_sha256": EXPECTED_SHA256,
                                "reason_flags": parent["reason_flags"]}, sort_keys=True),
                    timestamp,
                ))
            event_id = cursor.lastrowid
            conn.execute("""UPDATE physical_stop_identity_state SET identity_status='retired',
                retirement_event_id=?,retired_at=?,updated_at=? WHERE physical_stop_id=?""",
                         (event_id, timestamp, timestamp, predecessor))
            for child in parent["proposed_children"]:
                members = tuple(child["member_bus_stop_ids"])
                successor = allocation[(predecessor, tuple(sorted(members)))]
                latitude, longitude = child["proposed_coordinates"]
                conn.execute("""INSERT INTO physical_stops
                    (id,latitude,longitude,primary_name,member_count)
                    VALUES (?,?,?,?,?)""",
                    (successor, latitude, longitude, child["proposed_name"], len(members)))
                conn.execute("""INSERT INTO physical_stop_identity_state
                    (physical_stop_id,identity_status,updated_at) VALUES (?,'current',?)""",
                    (successor, timestamp))
                conn.execute("""INSERT INTO physical_stop_identity_edges
                    (event_id,predecessor_physical_stop_id,successor_physical_stop_id,
                     relationship_type) VALUES (?,?,?,'split_successor')""",
                    (event_id, predecessor, successor))
                for member in members:
                    conn.execute("""UPDATE physical_stop_members SET physical_stop_id=?
                        WHERE physical_stop_id=? AND bus_stop_id=?""",
                        (successor, predecessor, member))
                    if conn.execute("SELECT changes()").fetchone()[0] != 1:
                        raise RuntimeError(f"member ownership drift: {predecessor}/{member}")
                    conn.execute("""INSERT INTO physical_stop_member_lineage
                        (event_id,bus_stop_id,predecessor_physical_stop_id,
                         successor_physical_stop_id) VALUES (?,?,?,?)""",
                        (event_id, member, predecessor, successor))
    validate_cutover(conn)
    successor_ids = sorted(allocation.values())
    return {"already_applied": False, "retired_parents": len(manifest["parents"]),
            "successors_created": len(successor_ids), "successor_ids": successor_ids}


def validate_cutover(conn):
    retired = conn.execute("""SELECT COUNT(*) FROM physical_stop_identity_events e
        JOIN physical_stop_identity_state s ON s.retirement_event_id=e.id
        WHERE e.migration_version=? AND s.identity_status='retired'""",
        (CUTOVER_VERSION,)).fetchone()[0]
    successors = conn.execute("""SELECT COUNT(DISTINCT ed.successor_physical_stop_id)
        FROM physical_stop_identity_edges ed JOIN physical_stop_identity_events e
        ON e.id=ed.event_id WHERE e.migration_version=?""", (CUTOVER_VERSION,)).fetchone()[0]
    duplicate = conn.execute("""SELECT bus_stop_id FROM physical_stop_members
        GROUP BY bus_stop_id HAVING COUNT(*)<>1 LIMIT 1""").fetchone()
    orphan = conn.execute("""SELECT COUNT(*) FROM physical_stop_identity_edges ed
        LEFT JOIN physical_stops p ON p.id=ed.predecessor_physical_stop_id
        LEFT JOIN physical_stops s ON s.id=ed.successor_physical_stop_id
        WHERE p.id IS NULL OR s.id IS NULL""").fetchone()[0]
    manual = dict(conn.execute("""SELECT physical_stop_id,identity_status
        FROM physical_stop_identity_state WHERE physical_stop_id IN (406,2231,4468,5196,6080)"""))
    if retired != EXPECTED_PARENT_COUNT or successors != EXPECTED_CHILD_COUNT:
        raise RuntimeError(f"cutover count drift: retired={retired}, successors={successors}")
    if duplicate or orphan or set(manual.values()) != {"manual_exception"} or len(manual) != 5:
        raise RuntimeError(f"cutover integrity failure: duplicate={duplicate}, orphan={orphan}, manual={manual}")
    return {"retired_parents": retired, "successors": successors,
            "duplicate_member_owners": 0, "orphan_edges": orphan}
