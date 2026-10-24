"""Signed status verification and persistent synthetic rollback checkpoints.

No transport, production status root, target database, or execution integration.
Checkpoint connections are supplied explicitly and must contain only this store.
"""

import sqlite3
from contextlib import contextmanager

from . import trust as t
from .rules import canonical, digest


STATUS_FORMAT = "recognition-authority-status-v1"
STATUS_DOMAIN = b"DMV-recognition-authority-status-v1\x00"
PAYLOAD_FIELDS = {"registry_id", "snapshot_id", "key_id", "sequence", "issued_at_utc",
                  "expires_at_utc", "authorities"}
CHECKPOINT_SQL = """CREATE TABLE recognition_status_checkpoint (
    registry_id TEXT PRIMARY KEY NOT NULL, sequence INTEGER NOT NULL CHECK(sequence>=0),
    snapshot_sha256 TEXT NOT NULL, observed_at_utc TEXT NOT NULL, snapshot_json TEXT NOT NULL)"""


def _checkpoint_schema(conn):
    rows = conn.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
    t.require(len(rows) == 1 and rows[0][0:2] == ("table", "recognition_status_checkpoint")
              and " ".join(rows[0][2].split()) == " ".join(CHECKPOINT_SQL.split()),
              "isolated_checkpoint_schema_required")
    databases = conn.execute("PRAGMA database_list").fetchall()
    t.require(len(databases) == 1 and databases[0][1] == "main" and bool(databases[0][2]),
              "isolated_file_checkpoint_required")


def install_checkpoint(conn):
    """Explicit installation in a new disposable store, inside caller transaction.

    This is not a target migration. Never install in an application database.
    Verification subsequently owns its checkpoint transaction and durable commit.
    """
    t.require(type(conn) is sqlite3.Connection and conn.in_transaction, "checkpoint_transaction_required")
    conn.execute("SAVEPOINT install_status_checkpoint")
    try:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_status_checkpoint'").fetchone():
            conn.execute(CHECKPOINT_SQL)
        _checkpoint_schema(conn)
    except BaseException:
        conn.execute("ROLLBACK TO install_status_checkpoint")
        raise
    finally:
        conn.execute("RELEASE install_status_checkpoint")


def _payload(payload, config, *, complete=True):
    t.fields(payload, PAYLOAD_FIELDS)
    for key in ("registry_id", "snapshot_id", "key_id"):
        t.text(payload[key])
    t.identity(payload["snapshot_id"])
    t.require(payload["registry_id"] == config["registry_id"], "unknown_registry")
    t.integer(payload["sequence"], 1)
    t.require(t.utc(payload["issued_at_utc"]) < t.utc(payload["expires_at_utc"]), "invalid_status_interval")
    t.require(type(payload["authorities"]) is list, "authorities_required")
    expected = {(k["authority_id"], k["key_id"]) for k in config["authority_keys"]}
    seen = set()
    for row in payload["authorities"]:
        t.fields(row, {"authority_id", "key_id", "state", "key_state"})
        t.text(row["authority_id"])
        t.text(row["key_id"])
        pair = (row["authority_id"], row["key_id"])
        t.require(pair in expected and pair not in seen, "conflicting_authority_information")
        t.require(row["state"] in ("ENABLED", "REVOKED") and row["key_state"] in ("ENABLED", "REVOKED"),
                  "invalid_authority_state")
        seen.add(pair)
    t.require(bool(seen) and (seen == expected if complete else seen <= expected), "missing_authority_information")


def status_signing_bytes(payload_json):
    """Canonical signature input only; semantic verification requires a provider."""
    payload = t.load(payload_json)
    t.fields(payload, PAYLOAD_FIELDS)
    return STATUS_DOMAIN + canonical(payload).encode("utf-8")


def verify_status_signature(snapshot_json, *, provider=None):
    """Signed content only; no freshness claim or checkpoint changes."""
    return _verify_status_signature(snapshot_json, provider=provider)


def _verify_status_signature(snapshot_json, *, provider, complete=True):
    config = t.configuration(provider)
    value = t.signed_envelope(snapshot_json, STATUS_FORMAT)
    p = value["payload"]
    _payload(p, config, complete=complete)
    key = next((k for k in config["status_keys"] if k["key_id"] == p["key_id"]), None)
    t.require(key is not None, "unknown_status_key")
    t.verify_signature(key["public_key"], value["signature"], status_signing_bytes(canonical(p)))
    return t.VerificationFacts(canonical(value), digest(value))


def verify_current_status(snapshot_json, *, checkpoint_conn, trusted_now_utc, provider=None):
    """Accept fresh signed status and durably advance rollback/time floors.

    Caller must use protected persistent storage and trusted supplied time. Test
    SQLite durability is not protection against privileged checkpoint restoration.
    A valid revoked snapshot is accepted before a later operation is refused.
    """
    with _verified_status_transaction(snapshot_json, checkpoint_conn=checkpoint_conn,
            trusted_now_utc=trusted_now_utc, provider=provider) as checked:
        return checked


@contextmanager
def _verified_status_transaction(snapshot_json, *, checkpoint_conn, trusted_now_utc, provider=None):
    """Hold the accepted status writer lock through a coordinator's durable claim.

    Not a cross-database atomic transaction. The target claim retains these facts
    if interruption prevents this checkpoint commit; recovery must not replay it.
    """
    config = t.configuration(provider)
    checked = verify_status_signature(snapshot_json, provider=provider)
    p = t.load(checked.canonical_json)["payload"]
    now = t.utc(trusted_now_utc)
    issued, expiry = t.utc(p["issued_at_utc"]), t.utc(p["expires_at_utc"])
    t.require(issued <= now < expiry, "status_not_current")
    t.require((now-issued).total_seconds() < provider.max_status_age_seconds, "status_stale")
    t.require(p["sequence"] >= provider.minimum_sequence, "status_sequence_rollback")
    conn = checkpoint_conn
    t.require(type(conn) is sqlite3.Connection and not conn.in_transaction, "idle_checkpoint_connection_required")
    # Full synchronous commit for this dedicated fixture store; no target is opened.
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("BEGIN IMMEDIATE")
    try:
        _checkpoint_schema(conn)
        rows = conn.execute("SELECT registry_id,sequence,snapshot_sha256,observed_at_utc,snapshot_json "
                            "FROM recognition_status_checkpoint").fetchall()
        t.require(len(rows) <= 1, "checkpoint_corrupt")
        if rows:
            registry, sequence, previous, observed, previous_json = rows[0]
            t.require(registry == config["registry_id"], "checkpoint_registry_mismatch")
            t.integer(sequence)
            t.sha(previous)
            previous_snapshot = _verify_status_signature(previous_json, provider=provider, complete=False)
            old = t.load(previous_snapshot.canonical_json)["payload"]
            t.require(previous_snapshot.sha256 == previous and old["sequence"] == sequence,
                      "checkpoint_corrupt")
            t.require(t.utc(observed) <= now, "clock_rollback")
            t.require(p["sequence"] >= sequence, "status_sequence_rollback")
            if p["sequence"] == sequence:
                t.require(checked.sha256 == previous, "status_sequence_conflict")
            else:
                t.require(p["snapshot_id"] != old["snapshot_id"], "snapshot_identity_reused")
                t.require(t.utc(p["issued_at_utc"]) >= t.utc(old["issued_at_utc"]), "status_issuance_rollback")
                current_rows = {r["authority_id"]: r for r in p["authorities"]}
                for row in old["authorities"]:
                    replacement = current_rows[row["authority_id"]]
                    for state_field in ("state", "key_state"):
                        t.require(row[state_field] != "REVOKED" or replacement[state_field] == "REVOKED",
                                  "revoked_identity_reenabled")
        conn.execute("INSERT INTO recognition_status_checkpoint VALUES(?,?,?,?,?) "
                     "ON CONFLICT(registry_id) DO UPDATE SET sequence=excluded.sequence,"
                     "snapshot_sha256=excluded.snapshot_sha256,observed_at_utc=excluded.observed_at_utc,"
                     "snapshot_json=excluded.snapshot_json",
                     (config["registry_id"], p["sequence"], checked.sha256, trusted_now_utc, checked.canonical_json))
        yield checked
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
