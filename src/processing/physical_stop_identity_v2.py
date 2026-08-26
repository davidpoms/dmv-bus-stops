"""Persistent physical-stop identity reconciliation primitives.

Reconciliation always produces a plan.  Applying that plan is an explicit,
transactional operation; importing this module cannot mutate a database.
"""

from __future__ import annotations

import dataclasses
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone


MANUAL_EXCEPTIONS = frozenset({406, 2231, 4468, 5196, 6080})
EVENT_TYPES = frozenset({
    "split", "merge", "replacement", "membership_adjustment",
    "creation", "retirement", "movement",
})


@dataclasses.dataclass(frozen=True)
class IncomingMember:
    source_key: str
    bus_stop_id: int
    latitude: float
    longitude: float
    name: str | None = None
    heading: float | None = None
    structure_key: str | None = None
    exact_physical_stop_id: int | None = None


@dataclasses.dataclass(frozen=True)
class PlanAction:
    action: str
    members: tuple[int, ...]
    physical_stop_id: int | None = None
    predecessor_ids: tuple[int, ...] = ()
    reason: str = ""


@dataclasses.dataclass(frozen=True)
class ReconciliationPlan:
    version: str
    actions: tuple[PlanAction, ...]
    ambiguous: tuple[PlanAction, ...] = ()

    def counts(self):
        names = ("new_identity", "retire_identity", "split", "merge",
                 "member_added", "member_removed", "movement")
        return {name: sum(a.action == name for a in self.actions) for name in names}

    @property
    def is_noop(self):
        return not self.actions and not self.ambiguous


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS physical_stop_identity_events (
 id INTEGER PRIMARY KEY, migration_version TEXT NOT NULL,
 event_sequence INTEGER NOT NULL, event_type TEXT NOT NULL CHECK(event_type IN
 ('split','merge','replacement','membership_adjustment','creation','retirement','movement')),
 reason_code TEXT NOT NULL, reason_json TEXT NOT NULL DEFAULT '{}',
 effective_at TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(migration_version,event_sequence));
CREATE TABLE IF NOT EXISTS physical_stop_identity_edges (
 event_id INTEGER NOT NULL, predecessor_physical_stop_id INTEGER NOT NULL,
 successor_physical_stop_id INTEGER NOT NULL, relationship_type TEXT NOT NULL,
 PRIMARY KEY(event_id,predecessor_physical_stop_id,
             successor_physical_stop_id,relationship_type),
 FOREIGN KEY(event_id) REFERENCES physical_stop_identity_events(id),
 FOREIGN KEY(predecessor_physical_stop_id) REFERENCES physical_stops(id),
 FOREIGN KEY(successor_physical_stop_id) REFERENCES physical_stops(id));
CREATE TABLE IF NOT EXISTS physical_stop_identity_state (
 physical_stop_id INTEGER PRIMARY KEY, identity_status TEXT NOT NULL CHECK
 (identity_status IN ('current','retired','manual_exception')),
 retirement_event_id INTEGER, retired_at TEXT,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(physical_stop_id) REFERENCES physical_stops(id),
 FOREIGN KEY(retirement_event_id) REFERENCES physical_stop_identity_events(id),
 CHECK((identity_status='retired' AND retirement_event_id IS NOT NULL AND retired_at IS NOT NULL)
    OR (identity_status<>'retired' AND retirement_event_id IS NULL AND retired_at IS NULL)));
CREATE TABLE IF NOT EXISTS physical_stop_member_lineage (
 event_id INTEGER NOT NULL, bus_stop_id INTEGER NOT NULL,
 predecessor_physical_stop_id INTEGER, successor_physical_stop_id INTEGER,
 PRIMARY KEY(event_id,bus_stop_id),
 FOREIGN KEY(event_id) REFERENCES physical_stop_identity_events(id),
 FOREIGN KEY(bus_stop_id) REFERENCES bus_stops(id),
 FOREIGN KEY(predecessor_physical_stop_id) REFERENCES physical_stops(id),
 FOREIGN KEY(successor_physical_stop_id) REFERENCES physical_stops(id));
CREATE TABLE IF NOT EXISTS physical_stop_evidence_attribution (
 evidence_table TEXT NOT NULL,evidence_row_id INTEGER NOT NULL,
 physical_stop_id INTEGER,attribution_method TEXT NOT NULL CHECK(attribution_method IN
 ('exact_member','exact_source_record','spatial_reassessed','unresolved')),
 attribution_version TEXT NOT NULL,distance_m REAL,
 provenance_json TEXT NOT NULL DEFAULT '{}',
 attributed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(evidence_table,evidence_row_id,attribution_version),
 FOREIGN KEY(physical_stop_id) REFERENCES physical_stops(id),
 CHECK(attribution_method<>'unresolved' OR physical_stop_id IS NULL));
"""


def ensure_identity_schema(conn: sqlite3.Connection) -> None:
    duplicate = conn.execute("""SELECT bus_stop_id FROM physical_stop_members
        GROUP BY bus_stop_id HAVING COUNT(*)>1 LIMIT 1""").fetchone()
    if duplicate:
        raise ValueError(f"member belongs to multiple identities: {duplicate[0]}")
    conn.executescript(SCHEMA_SQL)
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS
        idx_physical_stop_member_owner ON physical_stop_members(bus_stop_id)""")
    conn.execute(
        "INSERT OR IGNORE INTO physical_stop_identity_state"
        "(physical_stop_id,identity_status) SELECT id,'current' FROM physical_stops"
    )


def _current_members(conn):
    has_state = conn.execute("""SELECT COUNT(*) FROM sqlite_master
        WHERE type='table' AND name='physical_stop_identity_state'""").fetchone()[0]
    if has_state:
        rows = conn.execute("""
            SELECT m.physical_stop_id,m.bus_stop_id
            FROM physical_stop_members m
            LEFT JOIN physical_stop_identity_state s
              ON s.physical_stop_id=m.physical_stop_id
            WHERE COALESCE(s.identity_status,'current')<>'retired'
            ORDER BY m.physical_stop_id,m.bus_stop_id
        """)
    else:
        rows = conn.execute("""SELECT physical_stop_id,bus_stop_id
            FROM physical_stop_members ORDER BY physical_stop_id,bus_stop_id""")
    result = defaultdict(set)
    for stop_id, member_id in rows:
        result[stop_id].add(member_id)
    return result


def plan_reconciliation(conn, incoming, *, version="physical-stop-v2"):
    """Compare exact source/member links with persistent identities.

    Geometry never creates an automatic identity here. Incoming records without
    exact identity are returned as ambiguous for a richer proposal layer or a
    human to adjudicate.
    """
    current = _current_members(conn)
    incoming_by_identity = defaultdict(set)
    incoming_positions = defaultdict(list)
    ambiguous = []
    for member in sorted(incoming, key=lambda x: (x.source_key, x.bus_stop_id)):
        target = member.exact_physical_stop_id
        if target is None or target in MANUAL_EXCEPTIONS:
            ambiguous.append(PlanAction(
                "ambiguous", (member.bus_stop_id,), target,
                target and (target,) or (),
                reason="no unambiguous exact persistent identity",
            ))
            continue
        incoming_by_identity[target].add(member.bus_stop_id)
        incoming_positions[target].append((member.latitude, member.longitude))

    actions = []
    for stop_id in sorted(set(current) | set(incoming_by_identity)):
        old, new = current.get(stop_id, set()), incoming_by_identity.get(stop_id, set())
        if stop_id not in current and new:
            actions.append(PlanAction("new_identity", tuple(sorted(new)), stop_id,
                                      reason="new exact source identity"))
            continue
        for member_id in sorted(new - old):
            actions.append(PlanAction("member_added", (member_id,), stop_id,
                                      reason="new exact member"))
        for member_id in sorted(old - new):
            actions.append(PlanAction("member_removed", (member_id,), stop_id,
                                      reason="exact member absent from snapshot"))
        if old and not new:
            actions.append(PlanAction("retire_identity", tuple(sorted(old)), stop_id,
                                      reason="all exact members absent"))
        if new and stop_id in current:
            old_position = conn.execute(
                "SELECT latitude,longitude FROM physical_stops WHERE id=?", (stop_id,)
            ).fetchone()
            if old_position:
                latitude = sum(p[0] for p in incoming_positions[stop_id]) / len(incoming_positions[stop_id])
                longitude = sum(p[1] for p in incoming_positions[stop_id]) / len(incoming_positions[stop_id])
                if _distance_m(*old_position, latitude, longitude) > 5:
                    actions.append(PlanAction("movement", tuple(sorted(new)), stop_id,
                                              reason="exact identity coordinates changed"))
    return ReconciliationPlan(version, tuple(actions), tuple(ambiguous))


def propose_partition(parent_id, groups, *, reason, version="physical-stop-v2"):
    """Create a reviewed split proposal without allocating IDs or mutating data."""
    normalized = tuple(sorted({tuple(sorted(map(int, group))) for group in groups}))
    flattened = [member for group in normalized for member in group]
    if parent_id in MANUAL_EXCEPTIONS:
        return ReconciliationPlan(version, (), (
            PlanAction("ambiguous", tuple(sorted(flattened)), parent_id,
                       (parent_id,), "manual exception"),
        ))
    if len(normalized) < 2 or len(flattened) != len(set(flattened)):
        return ReconciliationPlan(version, (), (
            PlanAction("ambiguous", tuple(sorted(flattened)), parent_id,
                       (parent_id,), "partition is incomplete or overlapping"),
        ))
    return ReconciliationPlan(version, (
        PlanAction("split", tuple(flattened), None, (parent_id,), reason),
    ))


def propose_merge(predecessor_ids, members, *, reason, version="physical-stop-v2"):
    predecessors = tuple(sorted(set(map(int, predecessor_ids))))
    if len(predecessors) < 2 or MANUAL_EXCEPTIONS.intersection(predecessors):
        return ReconciliationPlan(version, (), (
            PlanAction("ambiguous", tuple(sorted(map(int, members))), None,
                       predecessors, "merge includes an unresolved identity"),
        ))
    return ReconciliationPlan(version, (
        PlanAction("merge", tuple(sorted(map(int, members))), None,
                   predecessors, reason),
    ))


def _distance_m(lat1, lon1, lat2, lon2):
    radius = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    value = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1-value))


def allocate_successor_ids(conn, groups):
    """Allocate above the existing ID space in stable predecessor/member order."""
    maximum = conn.execute("SELECT COALESCE(MAX(id),0) FROM physical_stops").fetchone()[0]
    ordered = sorted(
        ((int(parent), tuple(sorted(map(int, members)))) for parent, members in groups),
        key=lambda item: (item[0], item[1]),
    )
    return {(parent, members): maximum + offset
            for offset, (parent, members) in enumerate(ordered, 1)}


def apply_plan(conn, plan, *, confirm=False, now=None):
    """Apply simple exact-link reconciliation actions atomically.

    Split/merge proposal application deliberately requires a separately reviewed
    migration manifest and is not inferred by this routine.
    """
    if not confirm:
        raise ValueError("applying an identity plan requires confirm=True")
    if plan.ambiguous:
        raise ValueError("plan contains ambiguous actions and fails closed")
    unsupported = {a.action for a in plan.actions} - {
        "member_added", "member_removed", "retire_identity"
    }
    if unsupported:
        raise ValueError(f"plan requires reviewed migration handling: {sorted(unsupported)}")
    ensure_identity_schema(conn)
    applied = conn.execute(
        "SELECT COUNT(*) FROM physical_stop_identity_events WHERE migration_version=?",
        (plan.version,),
    ).fetchone()[0]
    if applied:
        raise ValueError(f"migration version already applied: {plan.version}")
    timestamp = now or datetime.now(timezone.utc).isoformat()
    with conn:
        for sequence, action in enumerate(plan.actions, 1):
            event_type = "retirement" if action.action == "retire_identity" else "membership_adjustment"
            cursor = conn.execute("""
                INSERT INTO physical_stop_identity_events
                (migration_version,event_sequence,event_type,reason_code,
                 reason_json,effective_at) VALUES (?,?,?,?,?,?)
            """, (plan.version, sequence, event_type, action.action,
                  json.dumps({"reason": action.reason}, sort_keys=True), timestamp))
            event_id = cursor.lastrowid
            if action.action == "member_added":
                conn.execute("INSERT INTO physical_stop_members VALUES (?,?)",
                             (action.physical_stop_id, action.members[0]))
            elif action.action == "member_removed":
                conn.execute("DELETE FROM physical_stop_members WHERE physical_stop_id=? AND bus_stop_id=?",
                             (action.physical_stop_id, action.members[0]))
            else:
                conn.execute("""UPDATE physical_stop_identity_state SET
                    identity_status='retired',retirement_event_id=?,retired_at=?,updated_at=?
                    WHERE physical_stop_id=?""",
                    (event_id, timestamp, timestamp, action.physical_stop_id))
            for member_id in action.members:
                conn.execute("""INSERT INTO physical_stop_member_lineage
                    (event_id,bus_stop_id,predecessor_physical_stop_id,
                     successor_physical_stop_id) VALUES (?,?,?,?)""",
                    (event_id, member_id, action.physical_stop_id,
                     action.physical_stop_id if action.action == "member_added" else None))
    return len(plan.actions)
