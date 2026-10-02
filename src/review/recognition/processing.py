"""Bounded, explicit processing primitives. No scheduling or automatic issuance."""

from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import uuid

from . import DISABLED
from .qualification import Quarantined, require_transaction
from .rules import canonical, digest, explorer_candidates, load_rule
from .integrity import check_award_integrity, stable_evidence, validate_evidence
from .schema import connection


@dataclass(frozen=True)
class PreparedEvaluation:
    reviewer_id: int
    rule_key: str
    ledger_sequence: int
    candidates_json: str


@dataclass(frozen=True)
class LedgerSnapshot:
    rule_key: str
    definition: dict
    ledger_sequence: int
    facts: tuple


def completion_sequence(conn):
    # UNIQUE index supplies an O(log N) end lookup, including late/backdated IDs.
    return conn.execute("SELECT COALESCE(MAX(ledger_sequence),0) FROM recognition_completions").fetchone()[0]


def materialize_ledger(conn, rule_key, *, reviewer_id=None, assignment_bounds=None):
    """Read complete inputs only; caller must close before CPU evaluation."""
    if conn.execute("PRAGMA query_only").fetchone()[0] != 1:
        raise ValueError("candidate_calculation_requires_read_only_connection")
    if not conn.in_transaction:
        raise ValueError("ledger_materialization_requires_read_snapshot")
    sequence = completion_sequence(conn)
    definition = load_rule(conn, rule_key)
    if assignment_bounds is None:
        query = "SELECT * FROM recognition_completions WHERE reviewer_id=?"
        parameters = (reviewer_id,)
    else:
        # One bounded-cohort subquery, not one history query per owner or a
        # generated IN parameter list. All matching history is retained.
        query = """SELECT c.* FROM recognition_completions c WHERE c.reviewer_id IN
            (SELECT a.reviewer_id FROM stop_review_assignments a WHERE a.id>? AND a.id<=?)"""
        parameters = assignment_bounds
    facts = tuple(dict(row) for row in conn.execute(query, parameters))
    return LedgerSnapshot(rule_key, definition, sequence, facts)


def ledger_candidates(snapshot, reviewer_ids=None):
    """CPU-only calculation; accepts materialized inputs, never a connection."""
    facts = snapshot.facts if reviewer_ids is None else (
        fact for fact in snapshot.facts if fact["reviewer_id"] in reviewer_ids)
    return explorer_candidates(facts, snapshot.rule_key, snapshot.definition)


def prepare_evaluation(database, reviewer_id, rule_key):
    """Close the read snapshot/connection before sorting, hashing or serializing."""
    with connection(database) as conn:
        conn.execute("BEGIN")
        snapshot = materialize_ledger(conn, rule_key, reviewer_id=reviewer_id)
    candidates = ledger_candidates(snapshot)
    return PreparedEvaluation(reviewer_id, rule_key, snapshot.ledger_sequence, canonical(candidates))


def bounded(limit):
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("batch_limit_must_be_1_to_1000")
    return limit


def lease_jobs(conn, rule_key, *, gate=DISABLED, limit=100):
    if not gate.issuance:
        return []
    require_transaction(conn)
    bounded(limit)
    load_rule(conn, rule_key)
    now = conn.execute("SELECT strftime('%Y-%m-%dT%H:%M:%SZ','now')").fetchone()[0]
    until = (datetime.fromisoformat(now.replace("Z", "+00:00")) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    rows = conn.execute("""SELECT assignment_id FROM recognition_jobs WHERE rule_key=?
        AND (state='pending' OR (state='leased' AND lease_until_utc<=?)) ORDER BY assignment_id LIMIT ?""",
        (rule_key, now, limit)).fetchall()
    leased = []
    for row in rows:
        token = uuid.uuid4().hex
        conn.execute("""UPDATE recognition_jobs SET state='leased',lease_token=?,lease_until_utc=?,
            attempts=attempts+1,updated_at_utc=? WHERE assignment_id=?""", (token, until, now, row[0]))
        leased.append({"assignment_id": row[0], "lease_token": token, "rule_key": rule_key})
    return leased


def finalize_job(conn, assignment_id, lease_token, rule_key, prepared, *, gate=DISABLED):
    """Caller uses BEGIN IMMEDIATE; savepoint makes award/witness/job atomic.

    Only a ledger sequence lookup and bounded award/witness validation run here.
    Any new completion invalidates the prepared snapshot; retry calculation
    outside the writer. Unrelated job/award writes do not invalidate it.
    """
    if not gate.issuance:
        return []
    require_transaction(conn)
    job = conn.execute("""SELECT j.*,c.reviewer_id,c.origin FROM recognition_jobs j
        JOIN recognition_completions c USING(assignment_id) WHERE j.assignment_id=?""", (assignment_id,)).fetchone()
    now = conn.execute("SELECT strftime('%Y-%m-%dT%H:%M:%SZ','now')").fetchone()[0]
    if (job is None or job["state"] != "leased" or job["lease_token"] != lease_token
            or job["lease_until_utc"] <= now or job["rule_key"] != rule_key):
        raise Quarantined("stale_job_lease")
    if (not isinstance(prepared, PreparedEvaluation) or prepared.reviewer_id != job["reviewer_id"]
            or prepared.rule_key != rule_key or prepared.ledger_sequence != completion_sequence(conn)):
        raise Quarantined("stale_or_invalid_candidates")
    candidates = json.loads(prepared.candidates_json)
    definition = load_rule(conn, rule_key)
    if (not isinstance(candidates, list) or len(candidates) > len(definition["thresholds"])
            or [c["numerator"] for c in candidates] != definition["thresholds"][:len(candidates)]):
        raise Quarantined("stale_or_invalid_candidates")
    conn.execute("SAVEPOINT recognition_issue")
    try:
        awards = []
        for candidate in candidates:
            if candidate["reviewer_id"] != job["reviewer_id"] or candidate["rule_key"] != rule_key:
                raise Quarantined("candidate_identity_mismatch")
            validate_evidence(candidate, candidate["evidence"], definition)
            identity = tuple(candidate[k] for k in ("reviewer_id", "family", "scope_key", "tier_key"))
            existing = conn.execute("""SELECT award_id,rule_key,evidence_sha256 FROM recognition_awards
                WHERE reviewer_id=? AND family=? AND scope_key=? AND tier_key=?""", identity).fetchone()
            if existing:
                # Finding a lifetime identity is only 'already awarded'. It is
                # verified idempotency only after comparing version-neutral facts.
                original = check_award_integrity(conn, existing["award_id"])
                if original != stable_evidence(candidate, candidate["evidence"]):
                    raise Quarantined("award_qualification_evidence_conflict")
                awards.append(existing["award_id"])
                continue
            award_id = digest(identity)
            conn.execute("""INSERT INTO recognition_awards VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (award_id, *identity, rule_key, candidate["earned_at_utc"], now, job["origin"],
                          candidate["numerator"], canonical(candidate["evidence"]), digest(candidate["evidence"])))
            conn.executemany("INSERT INTO recognition_award_witnesses VALUES(?,?)",
                             [(award_id, w["assignment_id"]) for w in candidate["evidence"]["witnesses"]])
            check_award_integrity(conn, award_id)
            awards.append(award_id)
        conn.execute("""UPDATE recognition_jobs SET state='done',lease_token=NULL,lease_until_utc=NULL,
            last_error_code=NULL,updated_at_utc=? WHERE assignment_id=?""", (now, assignment_id))
        conn.execute("RELEASE recognition_issue")
        return awards
    except Exception:
        conn.execute("ROLLBACK TO recognition_issue")
        conn.execute("RELEASE recognition_issue")
        raise


def record_run(conn, manifest, *, gate=DISABLED):
    """Finalize an idempotent private manifest in the caller's batch transaction."""
    if not gate.capture:
        return None
    require_transaction(conn)
    run_id = digest(manifest)
    encoded = canonical(manifest)
    old = conn.execute("SELECT manifest_json,state FROM recognition_runs WHERE run_id=?", (run_id,)).fetchone()
    if old:
        if old["manifest_json"] != encoded or old["state"] != "complete":
            raise Quarantined("run_manifest_conflict")
        return run_id
    conn.execute("""INSERT INTO recognition_runs
        VALUES(?,'backfill',strftime('%Y-%m-%dT%H:%M:%SZ','now'),strftime('%Y-%m-%dT%H:%M:%SZ','now'),
               ?,?,'complete',?)""",
        (run_id, encoded, run_id, canonical({"qualified": len(manifest["qualified"]),
                                           "excluded": len(manifest["excluded"])})))
    return run_id
