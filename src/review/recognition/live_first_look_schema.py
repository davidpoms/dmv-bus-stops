"""Explicit additive First Look delivery state; no changes to Explorer jobs."""

import sqlite3

from .permanent_schema import check_schema as check_permanent_schema
from .qualification import Quarantined, require_transaction
from .schema import connection


TABLE = "recognition_first_look_pending"
SQL = f"""CREATE TABLE {TABLE} (
    assignment_id INTEGER PRIMARY KEY REFERENCES recognition_completions(assignment_id),
    configuration_json TEXT NOT NULL, configuration_sha256 TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','done','quarantined')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts>=0),
    last_error_code TEXT, outcome TEXT,
    CHECK((state='done' AND outcome IS NOT NULL AND outcome IN ('claim_sealed','existing_claim') AND last_error_code IS NULL)
       OR (state<>'done' AND outcome IS NULL))
)"""
OBJECTS = {TABLE: SQL,
    TABLE + "_context": f"""CREATE TRIGGER {TABLE}_context
        BEFORE UPDATE OF assignment_id,configuration_json,configuration_sha256 ON {TABLE}
        BEGIN SELECT RAISE(ABORT,'immutable_first_look_context'); END""",
    TABLE + "_replace": f"""CREATE TRIGGER {TABLE}_replace BEFORE INSERT ON {TABLE}
        WHEN EXISTS(SELECT 1 FROM {TABLE} WHERE assignment_id=NEW.assignment_id)
        BEGIN SELECT RAISE(ABORT,'existing_first_look_pending'); END""",
    TABLE + "_delete": f"""CREATE TRIGGER {TABLE}_delete BEFORE DELETE ON {TABLE}
        BEGIN SELECT RAISE(ABORT,'retained_first_look_pending'); END""",
    TABLE + "_done": f"""CREATE TRIGGER {TABLE}_done BEFORE UPDATE ON {TABLE}
        WHEN OLD.state='done'
        BEGIN SELECT RAISE(ABORT,'finalized_first_look_pending'); END""",
}


def check_schema(conn):
    check_permanent_schema(conn)
    for name, sql in OBJECTS.items():
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()
        if row is None or " ".join(row[0].split()) != " ".join(sql.split()):
            raise Quarantined("live_first_look_schema_mismatch")
    if any(r[0] not in OBJECTS for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (TABLE,))):
        raise Quarantined("unexpected_live_first_look_trigger")


def install(conn):
    require_transaction(conn)
    check_permanent_schema(conn)
    for name, sql in OBJECTS.items():
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone() is None:
            conn.execute(sql)
    check_schema(conn)
    if conn.execute("PRAGMA foreign_key_check").fetchone():
        raise Quarantined("foreign_key_check_failed")


def migrate(database, *, apply=False):
    """Default is an in-memory rehearsal; no application startup migration."""
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
    return {"applied": apply, "table": TABLE}
