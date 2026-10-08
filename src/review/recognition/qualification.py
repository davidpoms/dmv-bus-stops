"""Strict permanent qualification, independent of Phase 1's current projections."""

from datetime import datetime, timezone
import re

from . import DISABLED
from .rules import load_rule


class Quarantined(ValueError):
    """Bounded reason code; never includes raw private source payloads."""


def permanent_time(value, *, sqlite_utc_provenance=None):
    if not isinstance(value, str):
        raise Quarantined("missing_completion_time")
    if re.search(r"\d{2}:\d{2}:\d{2}[.,]\d", value):
        raise Quarantined("fractional_timestamp_policy_unresolved")
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value):
            if not sqlite_utc_provenance:
                raise Quarantined("unattested_naive_timestamp")
            instant = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            provenance = "sqlite_current_timestamp_utc:" + sqlite_utc_provenance
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)", value):
            instant = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
            provenance = "explicit_offset"
        else:
            raise Quarantined("invalid_completion_time")
        return instant.isoformat(timespec="seconds").replace("+00:00", "Z"), provenance
    except (ValueError, OverflowError) as error:
        if isinstance(error, Quarantined):
            raise
        raise Quarantined("invalid_completion_time") from None


def qualify(conn, assignment_id, *, sqlite_utc_provenance=None):
    assignment = conn.execute(
        "SELECT id,stop_id,reviewer_id,status,completed_at FROM stop_review_assignments WHERE id=?",
        (assignment_id,),
    ).fetchone()
    if assignment is None or assignment[3] != "completed":
        raise Quarantined("assignment_not_completed")
    observations = conn.execute(
        "SELECT id,reviewer_id,physical_stop_id FROM stop_observations "
        "WHERE assignment_id=? AND source='community_review' ORDER BY id", (assignment_id,),
    ).fetchall()
    if len(observations) != 1:
        raise Quarantined("ambiguous_community_evidence" if observations else "missing_community_evidence")
    observation, owner, stop = observations[0]
    if owner != assignment[2] or stop != assignment[1]:
        raise Quarantined("evidence_identity_mismatch")
    if (conn.execute("SELECT 1 FROM community_reviewers WHERE id=?", (owner,)).fetchone() is None
            or conn.execute("SELECT 1 FROM physical_stops WHERE id=?", (stop,)).fetchone() is None):
        raise Quarantined("missing_identity")
    timestamp, provenance = permanent_time(assignment[4], sqlite_utc_provenance=sqlite_utc_provenance)
    return dict(assignment_id=assignment_id, observation_id=observation, reviewer_id=owner,
                physical_stop_id=stop, completed_at_utc=timestamp,
                original_completed_at=assignment[4], timestamp_provenance=provenance)


def require_transaction(conn):
    if not conn.in_transaction or conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise ValueError("recognition_requires_transaction_and_foreign_keys")


def capture_completion(conn, assignment_id, rule_key, *, gate=DISABLED, origin="live", sqlite_utc_provenance=None):
    """Capture shared immutable evidence only, without creating any family job.

    Caller owns the transaction. The qualification rule/sequence/provenance are
    identical to Explorer capture; disabled returns before any SQL.
    """
    if not gate.capture:
        return None
    require_transaction(conn)
    load_rule(conn, rule_key)
    fact = qualify(conn, assignment_id, sqlite_utc_provenance=sqlite_utc_provenance)
    old = conn.execute("SELECT * FROM recognition_completions WHERE assignment_id=?", (assignment_id,)).fetchone()
    if old:
        if any(old[key] != value for key, value in fact.items()) or old["qualification_rule_key"] != rule_key:
            raise Quarantined("immutable_completion_conflict")
    else:
        conn.execute("""INSERT INTO recognition_completions
            (assignment_id,observation_id,reviewer_id,physical_stop_id,completed_at_utc,
             original_completed_at,timestamp_provenance,qualification_rule_key,origin,recorded_at_utc,ledger_sequence)
            VALUES(?,?,?,?,?,?,?,?,?,strftime('%Y-%m-%dT%H:%M:%SZ','now'),
                   (SELECT COALESCE(MAX(ledger_sequence),0)+1 FROM recognition_completions))""",
            (*fact.values(), rule_key, origin))
    return fact


def capture(conn, assignment_id, rule_key, *, gate=DISABLED, origin="live", sqlite_utc_provenance=None):
    """Capture evidence and an Explorer job in the caller-owned transaction.

    Future integration order: evidence commit -> derived refresh -> assignment
    completion -> this capture, with the last two in ONE short transaction.
    Never call before refresh, use retry payloads, commit, or close caller state.
    """
    if not gate.capture:
        return None
    fact = capture_completion(conn, assignment_id, rule_key, gate=gate, origin=origin,
                              sqlite_utc_provenance=sqlite_utc_provenance)
    job = conn.execute("SELECT rule_key FROM recognition_jobs WHERE assignment_id=?", (assignment_id,)).fetchone()
    if job is None:
        conn.execute("""INSERT INTO recognition_jobs(assignment_id,rule_key,updated_at_utc)
            VALUES(?,?,strftime('%Y-%m-%dT%H:%M:%SZ','now'))""", (assignment_id, rule_key))
    elif job[0] != rule_key:
        raise Quarantined("immutable_job_conflict")
    return fact
