"""Explicit, caller-transaction-owned installation of preparation/event storage."""

from .authorization import verify_migration
from .qualification import Quarantined, require_transaction


TABLES = {
    "recognition_preparations": """
        preparation_id TEXT PRIMARY KEY NOT NULL,
        parent_event_id TEXT REFERENCES recognition_frozen_events(event_id),
        body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL""",
    "recognition_frozen_events": """
        event_id TEXT PRIMARY KEY NOT NULL,
        preparation_id TEXT NOT NULL UNIQUE REFERENCES recognition_preparations(preparation_id),
        body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL""",
    "recognition_event_history": """
        event_id TEXT NOT NULL REFERENCES recognition_frozen_events(event_id),
        sequence INTEGER NOT NULL CHECK(sequence>=1),
        body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL,
        PRIMARY KEY(event_id,sequence)""",
}


def definitions():
    result = {name: f"CREATE TABLE {name} ({body})" for name, body in TABLES.items()}
    keys = {"recognition_preparations": "preparation_id=NEW.preparation_id",
            "recognition_frozen_events": "event_id=NEW.event_id OR preparation_id=NEW.preparation_id",
            "recognition_event_history": "event_id=NEW.event_id AND sequence=NEW.sequence"}
    for table in TABLES:
        for verb in ("UPDATE", "DELETE"):
            name = f"{table}_immutable_{verb.lower()}"
            result[name] = (f"CREATE TRIGGER {name} BEFORE {verb} ON {table} "
                            "BEGIN SELECT RAISE(ABORT,'immutable_recognition_event'); END")
        name = f"{table}_immutable_replace"
        result[name] = (f"CREATE TRIGGER {name} BEFORE INSERT ON {table} "
                        f"WHEN EXISTS(SELECT 1 FROM {table} WHERE {keys[table]}) "
                        "BEGIN SELECT RAISE(ABORT,'immutable_recognition_event'); END")
    return result


def check_schema(conn):
    expected = definitions()
    for name, sql in expected.items():
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()
        if row is None or " ".join(row[0].split()) != " ".join(sql.split()):
            raise Quarantined("event_schema_mismatch:" + name)
    for name, table in conn.execute("SELECT name,tbl_name FROM sqlite_master WHERE type='trigger'"):
        if table in TABLES and name not in expected:
            raise Quarantined("unexpected_event_trigger")


def install(conn, *, authorization=None, authority=None):
    """Add only event tables; explicit approval on files, no commit or startup hook."""
    require_transaction(conn)
    verify_migration(conn, "recognition_events", definitions(), authorization, authority)
    conn.execute("SAVEPOINT install_recognition_events")
    try:
        for name, sql in definitions().items():
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone() is None:
                conn.execute(sql)
        check_schema(conn)
        if conn.execute("PRAGMA foreign_key_check").fetchone():
            raise Quarantined("foreign_key_check_failed")
    except BaseException:
        conn.execute("ROLLBACK TO install_recognition_events")
        raise
    finally:
        conn.execute("RELEASE install_recognition_events")
