"""Disabled, caller-owned First Look delivery/sealing infrastructure.

No application issuance caller, dispatcher, scheduler or activation instant is supplied.
An independently reviewed guard must establish that the complete competitor
population is final enough to seal. Delivery order is never ordering.
"""

from dataclasses import asdict, dataclass
import json
from datetime import datetime, timezone
import re
import sqlite3

from . import DISABLED
from .geography import _utc
from .live_first_look_schema import check_schema
from . import permanent
from .writer_boundary import production_guard
from .qualification import Quarantined, capture_completion, qualify, require_transaction
from .report_connection import report_connection
from .rules import RULE_KEY, canonical, digest
from .authorization import AuthorizationError, verify, admission_binding, manifest_binding


@dataclass(frozen=True)
class Configuration:
    activation_at_utc: str = None
    historical_cutoff_utc: str = None
    policy_reference: str = None
    policy_sha256: str = None
    sqlite_utc_provenance: str = None


def _configuration(value):
    permanent.require(isinstance(value, dict) and set(value) == set(asdict(Configuration())), "live_configuration_required")
    permanent.require(permanent.text(value["policy_reference"]) and isinstance(value["policy_sha256"], str) and
                      re.fullmatch(r"[0-9a-f]{64}", value["policy_sha256"]) is not None, "reviewed_finality_policy_required")
    permanent.require(_utc(value["activation_at_utc"]) >= _utc(value["historical_cutoff_utc"]), "activation_before_historical_cutoff")
    permanent.require(value["sqlite_utc_provenance"] is None or permanent.text(value["sqlite_utc_provenance"]), "invalid_timestamp_provenance")
    return value


def _rule(config):
    return {"rule_key": "first_look:live:" + digest(config), "family": "first_look",
            "mode": "reviewed-live-finality-guard-v1", "configuration": config,
            "ordering": ["completed_at_utc", "numeric_assignment_id"],
            "qualification": "completed-single-matching-community-observation-v1",
            "identity_transfer": False, "late_discoveries": "quarantine-no-reassignment"}


def enqueue(conn, assignment_id, *, configuration=Configuration(), gate=DISABLED,
            authorization=None, authority=None):
    """After completed-assignment UPDATE, within that caller's transaction.

    Captures shared evidence and only First Look delivery state. Does not commit,
    open a connection, seal a claim, or insert/modify an Explorer job.
    """
    if not gate.capture:
        return None
    production_guard(authorization)
    permanent.require(not gate.issuance, 'issuance_must_remain_disabled')
    require_transaction(conn)
    check_schema(conn)
    config = _configuration(asdict(configuration))
    verify(conn, authorization, authority, **admission_binding(config))
    conn.execute("SAVEPOINT first_look_enqueue")
    try:
        fact = qualify(conn, assignment_id, sqlite_utc_provenance=config["sqlite_utc_provenance"])
        if fact["completed_at_utc"] < config["activation_at_utc"]:
            conn.execute("RELEASE first_look_enqueue")
            return {"enqueued": False, "reason": "before_activation"}
        capture_completion(conn, assignment_id, RULE_KEY, gate=gate,
                           sqlite_utc_provenance=config["sqlite_utc_provenance"])
        old = conn.execute("SELECT * FROM recognition_first_look_pending WHERE assignment_id=?", (assignment_id,)).fetchone()
        if old is None:
            conn.execute("INSERT INTO recognition_first_look_pending(assignment_id,configuration_json,configuration_sha256) VALUES(?,?,?)",
                         (assignment_id, canonical(config), digest(config)))
        else:
            permanent.require(old["configuration_json"] == canonical(config) and old["configuration_sha256"] == digest(config),
                              "live_configuration_conflict")
        conn.execute("RELEASE first_look_enqueue")
        return {"enqueued": True, "assignment_id": assignment_id}
    except Exception:
        conn.execute("ROLLBACK TO first_look_enqueue")
        conn.execute("RELEASE first_look_enqueue")
        raise


def validate_operation_manifest(manifest):
    """Frozen operation validation, reused by permanent claim integrity reads."""
    config = _configuration(manifest["configuration"])
    permanent.require(manifest["family"] == "first_look" and manifest["rule"] == _rule(config) and
                      manifest["rule_sha256"] == digest(_rule(config)), "live_rule_mismatch")
    report = manifest["report"]
    permanent.require(report["report_sha256"] == digest({k: v for k, v in report.items() if k != "report_sha256"}), "report_hash_mismatch")
    decision = manifest["finality_decision"]
    permanent.require(set(decision) == {"historical_operation_id", "evaluation_at_utc", "inputs", "reference"} and
                      permanent.text(decision["reference"]) and manifest["authorization_reference"] == decision["reference"] and
                      manifest["evaluation_at_utc"] == decision["evaluation_at_utc"] and manifest["inputs"] == decision["inputs"],
                      "live_finality_context_mismatch")
    baseline = manifest["historical_baseline"]
    permanent.require(digest(baseline) == decision["historical_operation_id"] and
                      baseline["format"] == "private-recognition-operation-v1" and baseline["family"] == "first_look" and
                      baseline["report"]["cutoff_utc"] == config["historical_cutoff_utc"], "historical_baseline_mismatch")
    permanent._validate_manifest(baseline)
    target = manifest["trigger_completion"]
    permanent.require(config["activation_at_utc"] <= target["completed_at_utc"] < report["cutoff_utc"] <=
                      _utc(manifest["evaluation_at_utc"]), "live_completion_outside_finality_boundary")
    winners = [c for c in permanent._candidates("first_look", report, manifest["evaluation_at_utc"])
               if c["physical_stop_id"] == target["physical_stop_id"]]
    permanent.require(len(winners) == 1 and manifest["candidates"] == winners and
                      winners[0]["completed_at_utc"] >= config["activation_at_utc"], "live_winner_mismatch")
    permanent.require(any(f == target for f in report["qualified"]), "live_trigger_evidence_missing")


def _sealed_baseline(conn, operation_id, config):
    baseline = permanent._operation(conn, operation_id)
    permanent.require(baseline["format"] == "private-recognition-operation-v1" and baseline["family"] == "first_look" and
                      baseline["report"]["cutoff_utc"] == config["historical_cutoff_utc"], "historical_baseline_mismatch")
    permanent._verify_operation_records(conn, operation_id)
    return baseline


def delivery_status(conn, assignment_id):
    """Read delivery status, not a fresh assertion of qualification or finality."""
    row = conn.execute("SELECT * FROM recognition_first_look_pending WHERE assignment_id=?", (assignment_id,)).fetchone()
    permanent.require(row is not None, "missing_live_first_look_pending")
    if row["state"] == "done":
        phase = "sealed"
    elif row["state"] == "quarantined":
        phase = "quarantined/conflict"
    elif row["last_error_code"] == "retryable_sqlite_lock":
        phase = "retryable_failure"
    elif row["last_error_code"] in ("finality_not_ready", "reviewed_finality_guard_required"):
        phase = "eligible_awaiting_finality"
    else:
        phase = "pending"
    return {"phase": phase, "state": row["state"], "attempts": row["attempts"],
            "reason": row["last_error_code"], "outcome": row["outcome"]}


def record_retryable_failure(conn, assignment_id, error, *, gate=DISABLED,
                             authorization=None, authority=None):
    """After failed processing has rolled back, in a NEW caller transaction.

    Only SQLite BUSY/LOCKED errors are classified automatically. Other failures
    propagate for investigation. Failure to obtain this transaction leaves the
    original pending delivery retryable; no independent connection is opened.
    """
    if not gate.issuance:
        return {"state": "disabled"}
    production_guard(authorization)
    permanent.require(not gate.capture, "capture_must_remain_disabled")
    require_transaction(conn)
    check_schema(conn)
    code = getattr(error, "sqlite_errorcode", None)
    permanent.require(isinstance(error, sqlite3.OperationalError) and type(code) is int and
                      (code & 255) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED), "failure_not_retryable")
    row = conn.execute('SELECT configuration_json FROM recognition_first_look_pending WHERE assignment_id=?',
                       (assignment_id,)).fetchone()
    permanent.require(row is not None, 'missing_live_first_look_pending')
    binding = {**delivery_binding(conn, assignment_id), 'action': 'record_retryable_failure'}
    verify(conn, authorization, authority, **binding)
    conn.execute("UPDATE recognition_first_look_pending SET attempts=attempts+1,last_error_code='retryable_sqlite_lock' "
                 "WHERE assignment_id=? AND state='pending'", (assignment_id,))
    return delivery_status(conn, assignment_id)


def delivery_binding(conn, assignment_id):
    """Read-only, exact delivery-state operation for independent review.

    Separate from permission to insert a claim. Includes the stored claim for
    completed acknowledgements and the entire current evidence population.
    """
    row = conn.execute('SELECT * FROM recognition_first_look_pending WHERE assignment_id=?',
                       (assignment_id,)).fetchone()
    permanent.require(row is not None, 'missing_live_first_look_pending')
    config = json.loads(row['configuration_json'])
    ledger = permanent._ledger(conn)
    fact = next((f for f in ledger if f['assignment_id'] == assignment_id), None)
    claim = None if fact is None else conn.execute(
        'SELECT * FROM recognition_first_look_claims WHERE physical_stop_id=?',
        (fact['physical_stop_id'],)).fetchone()
    population = {'ledger': ledger, 'identity': permanent._identity(conn)}
    operation = {'delivery': dict(row), 'population': population,
                 'claim': None if claim is None else dict(claim)}
    return dict(family='first_look', permission='issuance', action='process_delivery',
                operation_sha256=digest(operation), policy_sha256=config['policy_sha256'],
                population_sha256=digest(population), reference=config['policy_reference'])


def seal_pending(conn, assignment_id, *, gate=DISABLED, finality_guard=None, retry_quarantined=False,
                 authorization=None, delivery_authorization=None, authority=None):
    """Process one First Look delivery inside a caller-owned writer transaction.

    Guard(conn, context) is trusted reviewed validation code with SQL writes
    denied. Return None to defer, or a decision with historical_operation_id,
    evaluation_at_utc, inputs (existing First Look report arguments), reference.
    No guard/finality default is supplied. Caller commits returned pending/done/
    quarantined state; unexpected failures roll back this primitive's savepoint.
    """
    if not gate.issuance:
        return {"state": "disabled"}
    production_guard(authorization)
    production_guard(delivery_authorization)
    permanent.require(not gate.capture, "capture_must_remain_disabled")
    require_transaction(conn)
    check_schema(conn)
    delivery_authorized = False
    conn.execute("SAVEPOINT first_look_seal")
    try:
        # Acquire SQLite's writer lock before reading candidate evidence, even
        # for a caller that used deferred BEGIN. No independent BEGIN/COMMIT.
        conn.execute("UPDATE recognition_first_look_pending SET attempts=attempts WHERE 0")
        binding = delivery_binding(conn, assignment_id)
        verify(conn, delivery_authorization, authority, **binding)
        delivery_authorized = True
        row = conn.execute("SELECT * FROM recognition_first_look_pending WHERE assignment_id=?", (assignment_id,)).fetchone()
        permanent.require(row is not None, "missing_live_first_look_pending")
        config = _configuration(json.loads(row["configuration_json"]))
        permanent.require(row["configuration_json"] == canonical(config) and row["configuration_sha256"] == digest(config), "live_configuration_hash_mismatch")
        ledger = permanent._ledger(conn)
        stored = next((f for f in ledger if f["assignment_id"] == assignment_id), None)
        permanent.require(stored is not None, "missing_live_completion")
        stop = stored["physical_stop_id"]
        if row["state"] == "done":
            permanent.check_claim_integrity(conn, stop)
            # An idempotent delivery has no new writes; approval must still be current.
            conn.execute("RELEASE first_look_seal")
            return {"state": "done", "idempotent": True, "outcome": row["outcome"]}
        if row["state"] == "quarantined" and not retry_quarantined:
            conn.execute("RELEASE first_look_seal")
            return {"state": "quarantined", "reason": row["last_error_code"]}
        conn.execute("UPDATE recognition_first_look_pending SET attempts=attempts+1,state='pending',last_error_code=NULL WHERE assignment_id=?", (assignment_id,))
        fact = qualify(conn, assignment_id, sqlite_utc_provenance=config["sqlite_utc_provenance"])
        permanent._check_facts(conn, [fact])
        identity = permanent._identity(conn)
        decision = None
        if finality_guard is not None:
            with report_connection(conn):
                decision = finality_guard(conn, {"configuration": json.loads(canonical(config)),
                    "completion": dict(fact), "ledger_sequence": max((f["ledger_sequence"] for f in ledger), default=0),
                    "identity_sha256": digest(identity)})
        if decision is None:
            reason = "finality_not_ready" if finality_guard is not None else "reviewed_finality_guard_required"
            verify(conn, delivery_authorization, authority, **binding)
            conn.execute("UPDATE recognition_first_look_pending SET last_error_code=? WHERE assignment_id=?", (reason, assignment_id))
            conn.execute("RELEASE first_look_seal")
            return {"state": "pending", "reason": reason}
        decision = json.loads(canonical(decision))
        permanent.require(set(decision) == {"historical_operation_id", "evaluation_at_utc", "inputs", "reference"}, "invalid_finality_decision")
        baseline = _sealed_baseline(conn, decision["historical_operation_id"], config)
        prepared = permanent._prepare(conn, "first_look", decision["inputs"], decision["evaluation_at_utc"], decision["reference"])
        winners = [c for c in prepared["candidates"] if c["physical_stop_id"] == stop]
        permanent.require(len(winners) == 1, "live_stop_requires_adjudication")
        candidate = winners[0]
        permanent.require(fact["completed_at_utc"] < prepared["report"]["cutoff_utc"], "late_arrival_guard_not_final")
        manifest = {**prepared, "format": "live-first-look-operation-v1", "configuration": config,
                    "rule": _rule(config), "rule_sha256": digest(_rule(config)), "candidates": winners,
                    "finality_decision": decision, "historical_baseline": baseline, "trigger_completion": fact}
        manifest = json.loads(canonical(manifest))
        candidate = manifest['candidates'][0]
        verify(conn, authorization, authority, **manifest_binding(manifest))
        old = conn.execute("SELECT 1 FROM recognition_first_look_claims WHERE physical_stop_id=?", (stop,)).fetchone()
        if old:
            permanent.require(permanent.check_claim_integrity(conn, stop) == candidate, "existing_claim_requires_discrepancy")
            outcome = "existing_claim"
        else:
            validate_operation_manifest(manifest)
            rule = manifest["rule"]
            old = conn.execute("SELECT * FROM recognition_private_rules WHERE rule_key=?", (rule["rule_key"],)).fetchone()
            if old:
                permanent.require(old["definition_json"] == canonical(rule) and old["definition_sha256"] == digest(rule), "stored_rule_mismatch")
            else:
                conn.execute("INSERT INTO recognition_private_rules VALUES(?,?,?,?)",
                             (rule["rule_key"], manifest["family"], canonical(rule), digest(rule)))
            sealed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            permanent.require(sealed_at >= manifest["evaluation_at_utc"], "future_evaluation_not_authorized")
            operation_id = digest(manifest)
            conn.execute("INSERT INTO recognition_private_operations VALUES(?,?,?,?,?,?)",
                         (operation_id, rule["rule_key"], canonical(manifest), operation_id,
                          manifest["authorization_reference"], sealed_at))
            permanent.require(conn.execute("SELECT 1 FROM recognition_first_look_claims WHERE physical_stop_id=?",
                                 (candidate["physical_stop_id"],)).fetchone() is None, "existing_claim_requires_discrepancy")
            conn.execute("INSERT INTO recognition_first_look_claims VALUES(?,?,?,?,?,?,?)",
                         (candidate["physical_stop_id"], candidate["reviewer_id"], candidate["assignment_id"],
                          operation_id, candidate["completed_at_utc"], canonical(candidate), digest(candidate)))
            permanent.check_claim_integrity(conn, stop)
            outcome = "claim_sealed"
        verify(conn, authorization, authority, **manifest_binding(manifest))
        verify(conn, delivery_authorization, authority, **binding)
        conn.execute("UPDATE recognition_first_look_pending SET state='done',last_error_code=NULL,outcome=? WHERE assignment_id=?", (outcome, assignment_id))
        conn.execute("RELEASE first_look_seal")
        return {"state": "done", "outcome": outcome}
    except Quarantined as error:
        conn.execute("ROLLBACK TO first_look_seal")
        conn.execute("RELEASE first_look_seal")
        if isinstance(error, AuthorizationError) or not delivery_authorized:
            raise  # No delivery mutation is authorized by a rejected approval.
        current = conn.execute("SELECT state FROM recognition_first_look_pending WHERE assignment_id=?", (assignment_id,)).fetchone()
        if current is None or current[0] == "done":
            # Missing work or corruption of finalized evidence cannot truthfully
            # be reported as a newly persisted quarantine transition.
            raise
        # Durable only when the caller commits. The failed claim/operation has
        # already rolled back; this neither deletes nor replaces any claim.
        verify(conn, delivery_authorization, authority, **binding)
        conn.execute("UPDATE recognition_first_look_pending SET state='quarantined',attempts=attempts+1,last_error_code=?,outcome=NULL WHERE assignment_id=? AND state<>'done'",
                     (str(error), assignment_id))
        return {"state": "quarantined", "reason": str(error)}
    except Exception:
        conn.execute("ROLLBACK TO first_look_seal")
        conn.execute("RELEASE first_look_seal")
        raise
