"""Explicit additive control v3 migration; no target/startup migration."""

from . import administration_schema as base
from .administration import need


def definitions():
    result = {
        "recognition_approvals": "CREATE TABLE recognition_approvals (approval_id TEXT PRIMARY KEY, operation_id TEXT NOT NULL UNIQUE, confirmation_sha256 TEXT NOT NULL UNIQUE, body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL)",
        "recognition_approval_history": "CREATE TABLE recognition_approval_history (approval_id TEXT NOT NULL REFERENCES recognition_approvals(approval_id), sequence INTEGER NOT NULL, state TEXT NOT NULL CHECK(state IN ('APPROVED','INVALIDATED','SUPERSEDED')), body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL, PRIMARY KEY(approval_id,sequence))",
    }
    for table, key in (("recognition_approvals", "approval_id=NEW.approval_id OR confirmation_sha256=NEW.confirmation_sha256 OR operation_id=NEW.operation_id"),
                       ("recognition_approval_history", "approval_id=NEW.approval_id AND sequence=NEW.sequence")):
        for verb in ("UPDATE", "DELETE"):
            name = table + "_immutable_" + verb.lower()
            result[name] = f"CREATE TRIGGER {name} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_approval'); END"
        name = table + "_immutable_replace"
        result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN EXISTS(SELECT 1 FROM {table} WHERE {key}) BEGIN SELECT RAISE(ABORT,'immutable_approval'); END"
    name = "recognition_approval_history_transition"
    result[name] = f"""CREATE TRIGGER {name} BEFORE INSERT ON recognition_approval_history
        WHEN NEW.sequence != COALESCE((SELECT MAX(sequence) FROM recognition_approval_history WHERE approval_id=NEW.approval_id),0)+1
        OR (NEW.sequence=1 AND NEW.state!='APPROVED')
        OR (NEW.sequence>1 AND (NEW.state NOT IN ('INVALIDATED','SUPERSEDED') OR
            (SELECT state FROM recognition_approval_history WHERE approval_id=NEW.approval_id ORDER BY sequence DESC LIMIT 1)!='APPROVED'))
        BEGIN SELECT RAISE(ABORT,'invalid_approval_transition'); END"""
    return result


def check(conn):
    base.check_control(conn)
    need(conn.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_approvals'").fetchone(), "approval_migration_required", 503)


def install(conn):
    need(conn.in_transaction, "approval_migration_transaction_required")
    base.check_control(conn)
    conn.execute("SAVEPOINT install_approvals")
    try:
        for name, sql in definitions().items():
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone():
                conn.execute(sql)
        check(conn)
        need(not conn.execute("PRAGMA foreign_key_check").fetchone(), "approval_foreign_key_failure")
    except BaseException:
        conn.execute("ROLLBACK TO install_approvals")
        raise
    finally:
        conn.execute("RELEASE install_approvals")
