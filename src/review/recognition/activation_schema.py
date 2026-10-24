"""Explicit disposable activation ledger; not protected production storage."""

import sqlite3

from .trust import require


def definitions():
    result = {
        "recognition_activation_installation": "CREATE TABLE recognition_activation_installation (singleton INTEGER PRIMARY KEY CHECK(singleton=1), body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL)",
        "recognition_activation_history": "CREATE TABLE recognition_activation_history (sequence INTEGER PRIMARY KEY CHECK(sequence>=1), ceremony_id TEXT NOT NULL UNIQUE, body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL)",
    }
    for table in tuple(result):
        for action in ("UPDATE", "DELETE"):
            name = table + "_immutable_" + action.lower()
            result[name] = f"CREATE TRIGGER {name} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_activation'); END"
        key = "singleton=NEW.singleton" if table.endswith("installation") else "sequence=NEW.sequence OR ceremony_id=NEW.ceremony_id"
        name = table + "_immutable_replace"
        result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN EXISTS(SELECT 1 FROM {table} WHERE {key}) BEGIN SELECT RAISE(ABORT,'immutable_activation'); END"
    result["recognition_activation_sequence"] = """CREATE TRIGGER recognition_activation_sequence BEFORE INSERT ON recognition_activation_history
        WHEN NEW.sequence != COALESCE((SELECT MAX(sequence) FROM recognition_activation_history),0)+1
        BEGIN SELECT RAISE(ABORT,'activation_sequence_conflict'); END"""
    return result


def check_schema(conn):
    expected = definitions()
    actual = dict(conn.execute("SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
    require(set(actual) == set(expected) and all(
        " ".join(actual[name].split()) == " ".join(sql.split()) for name, sql in expected.items()),
        "activation_schema_mismatch")


def install(conn):
    """Caller owns transaction. Only separate disposable ledgers use this schema."""
    require(type(conn) is sqlite3.Connection and conn.in_transaction, "activation_transaction_required")
    conn.execute("SAVEPOINT install_activation")
    try:
        for name, sql in definitions().items():
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone():
                conn.execute(sql)
        check_schema(conn)
    except BaseException:
        conn.execute("ROLLBACK TO install_activation")
        raise
    finally:
        conn.execute("RELEASE install_activation")
