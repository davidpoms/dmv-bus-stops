"""Explicit local control v2; legacy Slice 6 isolated v1 remains unchanged."""

from . import execution_schema
from .trust import require


TABLES = {
    "recognition_admin_bindings": "generation INTEGER PRIMARY KEY CHECK(generation>=1), body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL",
    "recognition_admin_audit": "sequence INTEGER PRIMARY KEY CHECK(sequence>=1), body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL",
    "recognition_admin_primary": "token_hash TEXT PRIMARY KEY, actor INTEGER NOT NULL, key_hash TEXT NOT NULL, auth_epoch INTEGER NOT NULL, generation INTEGER NOT NULL, created INTEGER NOT NULL, expires INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0",
    "recognition_admin_mfa": "actor INTEGER PRIMARY KEY, seed_ciphertext TEXT, state TEXT NOT NULL, epoch INTEGER NOT NULL, last_counter INTEGER NOT NULL DEFAULT -1, pending_primary TEXT, pending_until INTEGER",
    "recognition_admin_sessions": "token_hash TEXT PRIMARY KEY, primary_hash TEXT NOT NULL, actor INTEGER NOT NULL, generation INTEGER NOT NULL, auth_epoch INTEGER NOT NULL, mfa_epoch INTEGER NOT NULL, created INTEGER NOT NULL, expires INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0",
    "recognition_admin_stepups": "token_hash TEXT PRIMARY KEY, session_hash TEXT NOT NULL, action TEXT NOT NULL, operation_id TEXT, operation_sha256 TEXT, state_sha256 TEXT, generation INTEGER NOT NULL, expires INTEGER NOT NULL",
    "recognition_admin_confirmations": "token_hash TEXT PRIMARY KEY, session_hash TEXT NOT NULL, actor INTEGER NOT NULL, operation_id TEXT NOT NULL, operation_sha256 TEXT NOT NULL, state_sha256 TEXT NOT NULL, generation INTEGER NOT NULL, expires INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0",
    "recognition_admin_attempts": "actor INTEGER PRIMARY KEY, window_start INTEGER NOT NULL, failures INTEGER NOT NULL",
}


def definitions():
    result = execution_schema.control_definitions().copy()
    for table, body in TABLES.items():
        result[table] = f"CREATE TABLE {table} ({body})"
    for table, key in (("recognition_admin_bindings", "generation"), ("recognition_admin_audit", "sequence")):
        for verb in ("UPDATE", "DELETE"):
            name = table + "_immutable_" + verb.lower()
            result[name] = f"CREATE TRIGGER {name} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_admin_control'); END"
        name = table + "_immutable_replace"
        result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN EXISTS(SELECT 1 FROM {table} WHERE {key}=NEW.{key}) BEGIN SELECT RAISE(ABORT,'immutable_admin_control'); END"
        name = table + "_sequence"
        result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN NEW.{key} != COALESCE((SELECT MAX({key}) FROM {table}),0)+1 BEGIN SELECT RAISE(ABORT,'admin_sequence_conflict'); END"
    return result


def check_control(conn):
    expected = definitions()
    actual = dict(conn.execute("SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
    if "recognition_approvals" in actual:
        from .approval_schema import definitions as approval_definitions
        expected.update(approval_definitions())
    if "recognition_local_activation" in actual:
        from .local_readiness import definitions as readiness_definitions
        expected.update(readiness_definitions())
    from . import runtime_profile_schema as runtime
    extended = any(n.startswith('recognition_runtime_') or n == 'recognition_admin_runtime_binding_guard' for n in actual)
    if 'recognition_admin_bindings' in actual:
        extended = extended or bool(conn.execute(
            "SELECT 1 FROM recognition_admin_bindings WHERE json_extract(body_json,'$.format')=?",
            (runtime.V3,)).fetchone())
    if extended:
        expected.update(runtime.definitions())
    require(set(actual) == set(expected) and all(" ".join(actual[n].split()) == " ".join(s.split())
            for n, s in expected.items()), "administration_schema_mismatch")
    require(len(conn.execute("PRAGMA database_list").fetchall()) == 1, "isolated_admin_control_required")
    if extended:
        runtime.check_rows(conn)


def install_runtime_extension(conn):
    """Explicit Slice 1 DDL only; ordinary access never calls this installer."""
    require(conn.in_transaction and conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1,
            'runtime_migration_transaction_required')
    from . import runtime_profile_schema as runtime
    check_control(conn)  # Never repair a partial or malformed extension.
    conn.execute('SAVEPOINT install_runtime_extension')
    try:
        for name, sql in runtime.definitions().items():
            if not conn.execute('SELECT 1 FROM sqlite_master WHERE name=?', (name,)).fetchone():
                conn.execute(sql)
        check_control(conn)
    except BaseException:
        conn.execute('ROLLBACK TO install_runtime_extension')
        raise
    finally:
        conn.execute('RELEASE install_runtime_extension')


def install_control(conn):
    require(conn.in_transaction, "admin_migration_transaction_required")
    conn.execute("SAVEPOINT install_local_administration")
    try:
        for name, sql in definitions().items():
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone():
                conn.execute(sql)
        check_control(conn)
    except BaseException:
        conn.execute("ROLLBACK TO install_local_administration")
        raise
    finally:
        conn.execute("RELEASE install_local_administration")


TARGET_TABLE = "recognition_local_installation"


def target_definitions():
    return {
        TARGET_TABLE: f"CREATE TABLE {TARGET_TABLE} (singleton INTEGER PRIMARY KEY CHECK(singleton=1), installation_id TEXT NOT NULL, target_id TEXT NOT NULL, owner_id INTEGER NOT NULL, auth_epoch INTEGER NOT NULL)",
        "recognition_local_owner_epoch": f"""CREATE TRIGGER recognition_local_owner_epoch AFTER UPDATE OF role,reviewer_key,email_verified_at ON community_reviewers
            WHEN (OLD.role IS NOT NEW.role OR OLD.reviewer_key IS NOT NEW.reviewer_key OR OLD.email_verified_at IS NOT NEW.email_verified_at)
            BEGIN UPDATE {TARGET_TABLE} SET auth_epoch=auth_epoch+1 WHERE owner_id=OLD.id; END""",
    }


def check_target(conn):
    for name, sql in target_definitions().items():
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()
        require(row is not None and " ".join(row[0].split()) == " ".join(sql.split()), "admin_target_schema_mismatch")


def install_target(conn):
    require(conn.in_transaction, "admin_migration_transaction_required")
    conn.execute("SAVEPOINT install_local_target")
    try:
        for name, sql in target_definitions().items():
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone():
                conn.execute(sql)
        check_target(conn)
    except BaseException:
        conn.execute("ROLLBACK TO install_local_target")
        raise
    finally:
        conn.execute("RELEASE install_local_target")
