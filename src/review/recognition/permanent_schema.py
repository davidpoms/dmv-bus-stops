"""Explicit additive storage for controlled First Look/Geography operations.

Explorer tables are prerequisites, never migration targets. No import-time DDL.
"""

import sqlite3

from .qualification import Quarantined
from .schema import TABLES as EXPLORER_TABLES, connection


TABLES = {
    "recognition_private_rules": """
        rule_key TEXT PRIMARY KEY NOT NULL,
        family TEXT NOT NULL CHECK(family IN ('first_look','geography_steward')),
        definition_json TEXT NOT NULL, definition_sha256 TEXT NOT NULL""",
    "recognition_private_operations": """
        operation_id TEXT PRIMARY KEY NOT NULL,
        rule_key TEXT NOT NULL REFERENCES recognition_private_rules(rule_key),
        manifest_json TEXT NOT NULL, manifest_sha256 TEXT NOT NULL,
        authorization_reference TEXT NOT NULL, sealed_at_utc TEXT NOT NULL""",
    "recognition_first_look_claims": """
        physical_stop_id INTEGER PRIMARY KEY REFERENCES physical_stops(id),
        reviewer_id INTEGER NOT NULL REFERENCES community_reviewers(id),
        assignment_id INTEGER NOT NULL UNIQUE REFERENCES recognition_completions(assignment_id),
        operation_id TEXT NOT NULL REFERENCES recognition_private_operations(operation_id),
        earned_at_utc TEXT NOT NULL, evidence_json TEXT NOT NULL, evidence_sha256 TEXT NOT NULL""",
    "recognition_first_look_discrepancies": """
        discrepancy_id TEXT PRIMARY KEY NOT NULL,
        physical_stop_id INTEGER NOT NULL REFERENCES recognition_first_look_claims(physical_stop_id),
        reviewed_at_utc TEXT NOT NULL, review_reference TEXT NOT NULL,
        evidence_json TEXT NOT NULL, evidence_sha256 TEXT NOT NULL""",
    "recognition_geography_scope_identities": """
        scope_key TEXT PRIMARY KEY NOT NULL, dimension TEXT NOT NULL,
        canonical_geography_id TEXT NOT NULL, display_label TEXT NOT NULL,
        UNIQUE(dimension,canonical_geography_id)""",
    "recognition_geography_snapshots": """
        snapshot_id TEXT PRIMARY KEY NOT NULL,
        scope_key TEXT NOT NULL UNIQUE REFERENCES recognition_geography_scope_identities(scope_key),
        operation_id TEXT NOT NULL REFERENCES recognition_private_operations(operation_id),
        scope_json TEXT NOT NULL, scope_sha256 TEXT NOT NULL""",
    "recognition_geography_members": """
        snapshot_id TEXT NOT NULL REFERENCES recognition_geography_snapshots(snapshot_id),
        physical_stop_id INTEGER NOT NULL REFERENCES physical_stops(id),
        PRIMARY KEY(snapshot_id,physical_stop_id)""",
    "recognition_geography_awards": """
        award_id TEXT PRIMARY KEY NOT NULL,
        reviewer_id INTEGER NOT NULL REFERENCES community_reviewers(id),
        scope_key TEXT NOT NULL REFERENCES recognition_geography_scope_identities(scope_key),
        tier_key TEXT NOT NULL CHECK(tier_key IN ('tier_1','tier_2','tier_3','tier_4')),
        snapshot_id TEXT NOT NULL REFERENCES recognition_geography_snapshots(snapshot_id),
        operation_id TEXT NOT NULL REFERENCES recognition_private_operations(operation_id),
        earned_at_utc TEXT NOT NULL, numerator INTEGER NOT NULL CHECK(numerator>0),
        denominator INTEGER NOT NULL CHECK(denominator>=10),
        percentage INTEGER NOT NULL CHECK(percentage BETWEEN 1 AND 100),
        size_band TEXT NOT NULL CHECK(size_band IN ('small','large')),
        evidence_json TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,
        UNIQUE(reviewer_id,scope_key,tier_key)""",
    "recognition_geography_witnesses": """
        award_id TEXT NOT NULL REFERENCES recognition_geography_awards(award_id),
        assignment_id INTEGER NOT NULL REFERENCES recognition_completions(assignment_id),
        PRIMARY KEY(award_id,assignment_id)""",
}


def definitions():
    result = {name: f"CREATE TABLE {name} ({body})" for name, body in TABLES.items()}
    for table in TABLES:
        for verb in ("UPDATE", "DELETE"):
            name = f"{table}_immutable_{verb.lower()}"
            result[name] = (f"CREATE TRIGGER {name} BEFORE {verb} ON {table} "
                            "BEGIN SELECT RAISE(ABORT,'immutable_private_recognition'); END")
        # Block INSERT OR REPLACE even with recursive_triggers disabled.
        keys = {"recognition_first_look_claims": ["physical_stop_id", "assignment_id"],
                "recognition_geography_scope_identities": ["scope_key", "dimension,canonical_geography_id"],
                "recognition_geography_snapshots": ["snapshot_id", "scope_key"],
                "recognition_geography_members": ["snapshot_id,physical_stop_id"],
                "recognition_geography_awards": ["award_id", "reviewer_id,scope_key,tier_key"],
                "recognition_geography_witnesses": ["award_id,assignment_id"]}.get(
                    table, [TABLES[table].strip().split()[0]])
        where = " OR ".join("(" + " AND ".join(f"{k}=NEW.{k}" for k in key.split(",")) + ")" for key in keys)
        name = f"{table}_immutable_replace"
        result[name] = (f"CREATE TRIGGER {name} BEFORE INSERT ON {table} "
                        f"WHEN EXISTS(SELECT 1 FROM {table} WHERE {where}) "
                        "BEGIN SELECT RAISE(ABORT,'immutable_private_recognition'); END")
    return result


def _same(a, b):
    return " ".join(a.split()) == " ".join(b.split())


def check_schema(conn):
    for name, sql in definitions().items():
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()
        if row is None or not _same(row[0], sql):
            raise Quarantined("private_schema_mismatch:" + name)
    for row in conn.execute("SELECT name,tbl_name FROM sqlite_master WHERE type='trigger'"):
        if row[1] in TABLES and row[0] not in definitions():
            raise Quarantined("unexpected_private_trigger")


def install(conn):
    if not conn.in_transaction or conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise ValueError("migration_requires_transaction_and_foreign_keys")
    for name, body in EXPLORER_TABLES.items():
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()
        if row is None or not _same(row[0], f"CREATE TABLE {name} ({body})"):
            raise Quarantined("existing_explorer_schema_required")
    for name, sql in definitions().items():
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()
        if row is None:
            conn.execute(sql)
        elif not _same(row[0], sql):
            raise Quarantined("private_schema_mismatch:" + name)
    check_schema(conn)
    if conn.execute("PRAGMA foreign_key_check").fetchone():
        raise Quarantined("foreign_key_check_failed")


def migrate(database, *, apply=False):
    """Default rehearses DDL in memory; explicit apply is caller authorization."""
    if apply:
        with connection(database, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            install(conn)
            conn.commit()
    else:
        with connection(database) as source:
            memory = sqlite3.connect(":memory:")
            try:
                source.backup(memory)
                memory.execute("PRAGMA foreign_keys=ON")
                memory.execute("BEGIN IMMEDIATE")
                install(memory)
            finally:
                memory.close()
    return {"applied": apply, "tables": sorted(TABLES)}
