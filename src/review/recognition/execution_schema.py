"""Explicit target-local claim, commit seal, execution and stop audit storage."""

from .authorization import verify_migration, verify, target_identity
from .operation_schema import check_schema as check_operations
from .permanent_schema import check_schema as check_private
from .qualification import Quarantined, require_transaction
import sqlite3
from dataclasses import asdict
from .rules import digest


TABLES = {
    "recognition_execution_storage": """singleton INTEGER PRIMARY KEY CHECK(singleton=1),
        body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL""",
    "recognition_execution_claims": """operation_id TEXT PRIMARY KEY NOT NULL
        REFERENCES recognition_operation_contracts(operation_id),
        body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL""",
    "recognition_execution_seals": """operation_id TEXT PRIMARY KEY NOT NULL
        REFERENCES recognition_execution_claims(operation_id), writer_sha256 TEXT NOT NULL UNIQUE,
        body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL""",
    "recognition_execution_audit": """operation_id TEXT NOT NULL REFERENCES recognition_operation_contracts(operation_id),
        sequence INTEGER NOT NULL CHECK(sequence>=1), state TEXT NOT NULL, kind TEXT NOT NULL,
        body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL, PRIMARY KEY(operation_id,sequence)""",
}
CONTROL_TABLES = {
    "recognition_execution_stops": """sequence INTEGER PRIMARY KEY NOT NULL CHECK(sequence>=1),
        body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL""",
    "recognition_execution_blocks": """operation_id TEXT PRIMARY KEY NOT NULL,
        body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL""",
}
TRANSITIONS = {
    "NOT_STARTED": {"WAITING", "EXECUTING", "FAILED_BEFORE_COMMIT"},
    "WAITING": {"WAITING", "EXECUTING", "FAILED_BEFORE_COMMIT"},
    "EXECUTING": {"COMPLETED", "COMPLETED_WITH_QUARANTINE", "FAILED_BEFORE_COMMIT",
        "UNKNOWN_RECOVERY_REQUIRED", "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED"},
    "UNKNOWN_RECOVERY_REQUIRED": {"UNKNOWN_RECOVERY_REQUIRED", "COMPLETED", "FAILED_BEFORE_COMMIT",
        "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED"},
    "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED": {"PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED"},
    "COMPLETED": set(), "COMPLETED_WITH_QUARANTINE": set(), "FAILED_BEFORE_COMMIT": set(),
}


def definitions():
    result = {name: f"CREATE TABLE {name} ({body})" for name, body in TABLES.items()}
    for table in TABLES:
        key = "singleton=NEW.singleton" if table.endswith("storage") else "operation_id=NEW.operation_id"
        if table.endswith("audit"):
            key += " AND sequence=NEW.sequence"
        if table.endswith("seals"):
            key += " OR writer_sha256=NEW.writer_sha256"
        for verb in ("UPDATE", "DELETE"):
            name = table + "_immutable_" + verb.lower()
            result[name] = f"CREATE TRIGGER {name} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_execution'); END"
        name = table + "_immutable_replace"
        result[name] = (f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN EXISTS(SELECT 1 FROM {table} WHERE {key}) "
                        "BEGIN SELECT RAISE(ABORT,'immutable_execution'); END")
    name = "recognition_execution_audit_transition"
    allowed = " OR ".join(f"(old.state='{a}' AND NEW.state='{b}')" for a, targets in TRANSITIONS.items() for b in sorted(targets))
    result[name] = f"""CREATE TRIGGER {name} BEFORE INSERT ON recognition_execution_audit
        WHEN NEW.sequence != COALESCE((SELECT MAX(sequence) FROM recognition_execution_audit
            WHERE operation_id=NEW.operation_id),0)+1
        OR NOT ((NEW.sequence=1 AND NEW.state IN ('WAITING','EXECUTING','FAILED_BEFORE_COMMIT')) OR EXISTS(
            SELECT 1 FROM recognition_execution_audit old WHERE old.operation_id=NEW.operation_id
            AND old.sequence=NEW.sequence-1 AND ({allowed})))
        OR (EXISTS(SELECT 1 FROM recognition_execution_audit old WHERE old.operation_id=NEW.operation_id
            AND old.sequence=NEW.sequence-1 AND old.state IN ('UNKNOWN_RECOVERY_REQUIRED','PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED'))
            AND NEW.kind!='RECOVERY')
        BEGIN SELECT RAISE(ABORT,'invalid_execution_transition'); END"""
    return result


def control_definitions():
    result = {name: f"CREATE TABLE {name} ({body})" for name, body in CONTROL_TABLES.items()}
    for table in CONTROL_TABLES:
        key = "sequence=NEW.sequence" if table.endswith("stops") else "operation_id=NEW.operation_id"
        for verb in ("UPDATE", "DELETE"):
            name = table + "_immutable_" + verb.lower()
            result[name] = f"CREATE TRIGGER {name} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_execution_control'); END"
        name = table + "_immutable_replace"
        result[name] = (f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN EXISTS(SELECT 1 FROM {table} WHERE {key}) "
                        "BEGIN SELECT RAISE(ABORT,'immutable_execution_control'); END")
    name = "recognition_execution_stops_sequence"
    result[name] = f"""CREATE TRIGGER {name} BEFORE INSERT ON recognition_execution_stops
        WHEN NEW.sequence != COALESCE((SELECT MAX(sequence) FROM recognition_execution_stops),0)+1
        BEGIN SELECT RAISE(ABORT,'invalid_stop_sequence'); END"""
    return result


def storage_subject(conn, control_path, checkpoint_path):
    return dict(target=asdict(target_identity(conn)), control=asdict(target_identity(control_path)),
                checkpoint=asdict(target_identity(checkpoint_path)))


def storage_binding(subject):
    return dict(family="recognition_execution", permission="administration", action="bind_stores",
                operation_sha256=digest(subject), policy_sha256=digest("execution-storage-v1"),
                population_sha256=None, reference="project-owner")


def bind_stores(conn, control_path, checkpoint_path, *, authorization=None, authority=None):
    """Explicit immutable administrative binding, before target enrollment."""
    require_transaction(conn)
    check_schema(conn)
    subject = storage_subject(conn, control_path, checkpoint_path)
    if getattr(authorization, "environment", None) != "disposable":
        raise Quarantined("disposable_storage_binding_only")
    verify(conn, authorization, authority, **storage_binding(subject))
    from . import events
    old = conn.execute("SELECT body_json,body_sha256 FROM recognition_execution_storage WHERE singleton=1").fetchone()
    if old:
        if events._read(old) != subject:
            raise Quarantined("execution_storage_already_bound")
        return subject
    events._insert(conn, "recognition_execution_storage", "singleton", (1,), subject)
    return subject


def check_control(conn):
    expected = control_definitions()
    rows = conn.execute("SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
    if {r[0] for r in rows} != set(expected) or any(
            " ".join(sql.split()) != " ".join(expected[name].split()) for name, sql in rows):
        raise Quarantined("execution_control_schema_mismatch")
    databases = conn.execute("PRAGMA database_list").fetchall()
    if len(databases) != 1 or not databases[0][2]:
        raise Quarantined("isolated_execution_control_file_required")


def install_control(conn):
    """Explicit disposable control-store installation; no target/production root."""
    if type(conn) is not sqlite3.Connection or not conn.in_transaction:
        raise ValueError("control_transaction_required")
    conn.execute("SAVEPOINT install_execution_control")
    try:
        for name, sql in control_definitions().items():
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone():
                conn.execute(sql)
        check_control(conn)
    except BaseException:
        conn.execute("ROLLBACK TO install_execution_control")
        raise
    finally:
        conn.execute("RELEASE install_execution_control")


def check_schema(conn):
    check_operations(conn)
    check_private(conn)
    expected = definitions()
    for name, sql in expected.items():
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()
        if row is None or " ".join(row[0].split()) != " ".join(sql.split()):
            raise Quarantined("execution_schema_mismatch:" + name)
    for name, table in conn.execute("SELECT name,tbl_name FROM sqlite_master WHERE type='trigger'"):
        if table in TABLES and name not in expected:
            raise Quarantined("unexpected_execution_trigger")


def install(conn, *, authorization=None, authority=None):
    require_transaction(conn)
    verify_migration(conn, "recognition_execution", definitions(), authorization, authority)
    conn.execute("SAVEPOINT install_execution")
    try:
        for name, sql in definitions().items():
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone():
                conn.execute(sql)
        check_schema(conn)
        if conn.execute("PRAGMA foreign_key_check").fetchone():
            raise Quarantined("foreign_key_check_failed")
    except BaseException:
        conn.execute("ROLLBACK TO install_execution")
        raise
    finally:
        conn.execute("RELEASE install_execution")
