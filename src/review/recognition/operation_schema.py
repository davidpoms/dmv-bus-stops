"""Explicit additive operation-contract installation; never startup migration."""

from .authorization import verify_migration
from .event_schema import check_schema as check_events
from .qualification import Quarantined, require_transaction


DECISIONS = {
    "PREPARED": {"AUTHORIZED", "REJECTED", "SENT_BACK", "INVALIDATED", "SUPERSEDED"},
    "AUTHORIZED": {"INVALIDATED", "SUPERSEDED"},
    "REJECTED": set(), "SENT_BACK": set(), "INVALIDATED": set(), "SUPERSEDED": set(),
}
EXECUTIONS = {
    "NOT_STARTED": {"WAITING", "EXECUTING", "FAILED_BEFORE_COMMIT"},
    "WAITING": {"WAITING", "EXECUTING", "FAILED_BEFORE_COMMIT"},
    "EXECUTING": {"COMPLETED", "COMPLETED_WITH_QUARANTINE", "FAILED_BEFORE_COMMIT",
                  "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED"},
    "COMPLETED": set(), "COMPLETED_WITH_QUARANTINE": set(),
    "FAILED_BEFORE_COMMIT": set(), "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED": set(),
    "UNKNOWN_RECOVERY_REQUIRED": set(),
}
TABLES = {
    "recognition_operation_contracts": """operation_id TEXT PRIMARY KEY NOT NULL,
        event_id TEXT NOT NULL UNIQUE REFERENCES recognition_frozen_events(event_id),
        body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL""",
    **{f"recognition_operation_{kind}": f"""operation_id TEXT NOT NULL
        REFERENCES recognition_operation_contracts(operation_id),
        sequence INTEGER NOT NULL CHECK(sequence>=1), state TEXT NOT NULL,
        body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL,
        PRIMARY KEY(operation_id,sequence)""" for kind in ("decisions", "executions")},
    "recognition_operation_receipts": """operation_id TEXT PRIMARY KEY NOT NULL
        REFERENCES recognition_operation_contracts(operation_id),
        body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL""",
}


def definitions():
    result = {name: f"CREATE TABLE {name} ({body})" for name, body in TABLES.items()}
    for table in TABLES:
        key = "operation_id=NEW.operation_id"
        if table.endswith(("decisions", "executions")):
            key += " AND sequence=NEW.sequence"
        elif table.endswith("contracts"):
            key += " OR event_id=NEW.event_id"
        for verb in ("UPDATE", "DELETE"):
            name = f"{table}_immutable_{verb.lower()}"
            result[name] = (f"CREATE TRIGGER {name} BEFORE {verb} ON {table} "
                            "BEGIN SELECT RAISE(ABORT,'immutable_operation_contract'); END")
        name = f"{table}_immutable_replace"
        result[name] = (f"CREATE TRIGGER {name} BEFORE INSERT ON {table} "
                        f"WHEN EXISTS(SELECT 1 FROM {table} WHERE {key}) "
                        "BEGIN SELECT RAISE(ABORT,'immutable_operation_contract'); END")
    for kind, graph, initial in (("decisions", DECISIONS, "PREPARED"),
                                 ("executions", EXECUTIONS, "NOT_STARTED")):
        table = f"recognition_operation_{kind}"
        allowed = " OR ".join(
            f"(old.state='{old}' AND NEW.state='{new}')"
            for old, targets in graph.items() for new in sorted(targets))
        name = table + "_transition"
        result[name] = f"""CREATE TRIGGER {name} BEFORE INSERT ON {table}
            WHEN NEW.sequence != COALESCE((SELECT MAX(sequence) FROM {table}
                WHERE operation_id=NEW.operation_id),0)+1
            OR NOT ((NEW.sequence=1 AND NEW.state='{initial}') OR EXISTS(
                SELECT 1 FROM {table} old WHERE old.operation_id=NEW.operation_id
                AND old.sequence=NEW.sequence-1 AND ({allowed})))
            BEGIN SELECT RAISE(ABORT,'invalid_operation_transition'); END"""
    name = "recognition_operation_executions_decision_guard"
    result[name] = f"""CREATE TRIGGER {name} BEFORE INSERT ON recognition_operation_executions
        WHEN NEW.state IN ('WAITING','EXECUTING','COMPLETED','COMPLETED_WITH_QUARANTINE')
        AND COALESCE((SELECT state FROM recognition_operation_decisions
            WHERE operation_id=NEW.operation_id ORDER BY sequence DESC LIMIT 1),'') != 'AUTHORIZED'
        BEGIN SELECT RAISE(ABORT,'authorized_assertion_required'); END"""
    name = "recognition_operation_executions_receipt_guard"
    result[name] = f"""CREATE TRIGGER {name} BEFORE INSERT ON recognition_operation_executions
        WHEN NEW.state IN ('COMPLETED','COMPLETED_WITH_QUARANTINE') AND NOT EXISTS(
            SELECT 1 FROM recognition_operation_receipts WHERE operation_id=NEW.operation_id)
        BEGIN SELECT RAISE(ABORT,'completion_receipt_required'); END"""
    return result


def check_schema(conn):
    check_events(conn)
    expected = definitions()
    for name, sql in expected.items():
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()
        if row is None or " ".join(row[0].split()) != " ".join(sql.split()):
            raise Quarantined("operation_schema_mismatch:" + name)
    for name, table in conn.execute("SELECT name,tbl_name FROM sqlite_master WHERE type='trigger'"):
        if table in TABLES and name not in expected:
            raise Quarantined("unexpected_operation_trigger")


def install(conn, *, authorization=None, authority=None):
    """Caller owns BEGIN/COMMIT; file installation needs existing exact authority."""
    require_transaction(conn)
    check_events(conn)
    verify_migration(conn, "recognition_operations", definitions(), authorization, authority)
    conn.execute("SAVEPOINT install_recognition_operations")
    try:
        for name, sql in definitions().items():
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone() is None:
                conn.execute(sql)
        check_schema(conn)
        if conn.execute("PRAGMA foreign_key_check").fetchone():
            raise Quarantined("foreign_key_check_failed")
    except BaseException:
        conn.execute("ROLLBACK TO install_recognition_operations")
        raise
    finally:
        conn.execute("RELEASE install_recognition_operations")
