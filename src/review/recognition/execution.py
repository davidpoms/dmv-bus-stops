"""Disposable execution admission, atomic target seals and explicit recovery.

No production factory/authority, no generic callbacks, no automatic retry or live
finality adapter. The only dispatch is the existing historical finalizer.
"""

from contextlib import contextmanager
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from weakref import WeakKeyDictionary

from . import (RecognitionGate, dependencies, enrollment, events, execution_schema,
               operations, permanent, status, trust, writer_boundary)
from .authorization import AuthorizationError, verify, manifest_binding, target_identity
from .qualification import Quarantined
from .rules import canonical, digest
from .schema import connection


POLICY = {"reference": "atomic-historical-v1", "quarantine_categories": [], "other_categories": []}
RECOVERY_STATES = {"EXECUTING", "UNKNOWN_RECOVERY_REQUIRED", "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED"}
_contexts = WeakKeyDictionary()


@dataclass(frozen=True)
class ExecutionResult:
    admission: str
    state: str
    reason: str
    receipt_sha256: str | None = None


class SimulatedInterruption(BaseException):
    """Controlled disposable test interruption, never a retry instruction."""


FAULT_POINTS = {"BEFORE_CLAIM", "AFTER_CLAIM", "AFTER_MUTATION", "AFTER_COMMIT", "AFTER_FINALIZATION"}


def _interrupt(point, fault_point):
    if point == fault_point:
        raise SimulatedInterruption(point)


def execution_binding(envelope, action="execute"):
    trust.require(action in {"execute", "reconcile"}, "unsupported_execution_action")
    return dict(family="recognition_execution", permission="execution" if action == "execute" else "recovery",
                action=action, operation_sha256=digest(envelope), policy_sha256=digest("execution-foundation-v1"),
                population_sha256=envelope["population_sha256"], reference="project-owner" if action == "reconcile" else "synthetic-execution")


def stop_binding(active, reason, expected_sequence):
    trust.require(type(active) is bool and type(expected_sequence) is int and expected_sequence >= 0,
                  "invalid_stop_request")
    trust.text(reason)
    return dict(family="recognition_execution", permission="administration", action="stop" if active else "clear_stop",
        operation_sha256=digest(dict(active=active, reason=reason, expected_sequence=expected_sequence)),
        policy_sha256=digest("execution-stop-v1"), population_sha256=None, reference="project-owner")


class SyntheticExecutionContext:
    """Registered disposable context: no callbacks or production/test boolean."""
    __slots__ = ("__weakref__",)

    def __init__(self, database, operation_id, *, enrollment_provider, trust_provider, checkpoint_path,
                 control_path, execution_authorization, writer_authorization, authority):
        enrollment._context(enrollment_provider)
        trust.configuration(trust_provider)
        paths = [enrollment._path(enrollment_provider, p) for p in (database, checkpoint_path, control_path)]
        trust.require(len(set(paths)) == 3, "separate_execution_stores_required")
        for permission in (execution_authorization, writer_authorization):
            trust.require(getattr(permission, "environment", None) == "disposable", "disposable_execution_only")
        with connection(paths[0]) as conn:
            execution_schema.check_schema(conn)
            storage_row = conn.execute("SELECT body_json,body_sha256 FROM recognition_execution_storage WHERE singleton=1").fetchone()
            trust.require(storage_row is not None, "execution_storage_binding_required")
            storage = events._read(storage_row)
            trust.require(storage == execution_schema.storage_subject(conn, paths[2], paths[1]), "execution_storage_binding_mismatch")
            operation = operations.get_operation(conn, operation_id)
            manifest = events.get_event(conn, operation["envelope"]["event_id"])["preparation"]["manifest"]
        e = operation["envelope"]
        verify(paths[0], execution_authorization, authority, **execution_binding(e))
        verify(paths[0], writer_authorization, authority, **manifest_binding(manifest))
        trust.require(e["format"] == operations.ENROLLED_CONTRACT, "enrolled_operation_required")
        record = enrollment_provider.record(e["enrollment"]["enrollment_id"])
        trust.require(enrollment.reference(record, provider=enrollment_provider) == e["enrollment"], "enrollment_binding_mismatch")
        _contexts[self] = dict(database=paths[0], checkpoint=paths[1], control=paths[2], envelope=canonical(e),
            manifest=canonical(manifest), record=record, enrollment_provider=enrollment_provider,
            trust_provider=trust_provider, execution_authorization=execution_authorization,
            writer_authorization=writer_authorization, authority=authority, mode="execution", storage=storage)


class SyntheticRecoveryContext:
    """Separate owner recovery capability; no current writer/execute grant needed."""
    __slots__ = ("__weakref__",)

    def __init__(self, database, operation_id, *, enrollment_provider, trust_provider,
                 recovery_authorization, authority):
        enrollment._context(enrollment_provider)
        trust.configuration(trust_provider)
        path = enrollment._path(enrollment_provider, database)
        trust.require(getattr(recovery_authorization, "environment", None) == "disposable", "disposable_recovery_only")
        with connection(path) as conn:
            execution_schema.check_schema(conn)
            storage_row = conn.execute("SELECT body_json,body_sha256 FROM recognition_execution_storage WHERE singleton=1").fetchone()
            trust.require(storage_row is not None, "execution_storage_binding_required")
            storage = events._read(storage_row)
            operation = operations.get_operation(conn, operation_id)
        e = operation["envelope"]
        verify(path, recovery_authorization, authority, **execution_binding(e, "reconcile"))
        record = enrollment_provider.record(e["enrollment"]["enrollment_id"])
        trust.require(enrollment.reference(record, provider=enrollment_provider) == e["enrollment"], "enrollment_binding_mismatch")
        _contexts[self] = dict(database=path, envelope=canonical(e), record=record,
            enrollment_provider=enrollment_provider, trust_provider=trust_provider, authority=authority, mode="recovery", storage=storage)


def _context(context):
    trust.require(type(context) in (SyntheticExecutionContext, SyntheticRecoveryContext) and context in _contexts,
                  "production_execution_unavailable")
    data = _contexts[context]
    enrollment._context(data["enrollment_provider"])
    return data


@contextmanager
def _store(data, name):
    path = enrollment._path(data["enrollment_provider"], data[name])
    trust.require(asdict(target_identity(path)) == data["storage"][name], "execution_storage_identity_mismatch")
    conn = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=FULL")
        yield conn
    finally:
        conn.rollback()
        conn.close()


def _read(conn, table, operation_id):
    row = conn.execute(f"SELECT body_json,body_sha256 FROM {table} WHERE operation_id=?", (operation_id,)).fetchone()
    return events._read(row) if row else None


def _audit(conn, operation_id):
    result = []
    for row in conn.execute("SELECT body_json,body_sha256,sequence,state,kind FROM recognition_execution_audit "
                            "WHERE operation_id=? ORDER BY sequence", (operation_id,)):
        body = events._read(row)
        old = result[-1]["state"] if result else "NOT_STARTED"
        trust.require(body["operation_id"] == operation_id and body["sequence"] == row[2] == len(result)+1
            and body["state"] == row[3] and body["kind"] == row[4]
            and body["state"] in execution_schema.TRANSITIONS[old]
            and body["previous_sha256"] == (digest(result[-1]) if result else None), "execution_audit_corrupt")
        result.append(body)
    return result


def _append(conn, operation_id, state, reason, now, kind="EXECUTION"):
    history = _audit(conn, operation_id)
    trust.require(not history or trust.utc(now) >= trust.utc(history[-1]["recorded_at_utc"]), "execution_clock_rollback")
    body = dict(operation_id=operation_id, sequence=len(history)+1, state=state, kind=kind,
                reason=reason, recorded_at_utc=now, previous_sha256=digest(history[-1]) if history else None)
    events._insert(conn, "recognition_execution_audit", "operation_id,sequence,state,kind",
                   (operation_id, body["sequence"], state, kind), body)


def _stop(conn):
    history = []
    for row in conn.execute("SELECT body_json,body_sha256,sequence FROM recognition_execution_stops ORDER BY sequence"):
        item = events._read(row)
        trust.require(item["sequence"] == row[2] == len(history)+1 and type(item["active"]) is bool
            and item["previous_sha256"] == (digest(history[-1]) if history else None), "stop_history_corrupt")
        history.append(item)
    return history[-1] if history else {"active": False, "sequence": 0}


def set_emergency_stop(context, *, reason, expected_sequence, authorization, trusted_now_utc):
    return _set_stop(context, True, reason, expected_sequence, authorization, trusted_now_utc)


def clear_emergency_stop(context, *, reason, activation_sequence, authorization, trusted_now_utc):
    return _set_stop(context, False, reason, activation_sequence, authorization, trusted_now_utc)


def _set_stop(context, active, reason, expected_sequence, authorization, now):
    data = _context(context)
    trust.require(data["mode"] == "execution", "execution_control_context_required")
    trust.utc(now)
    trust.require(getattr(authorization, "environment", None) == "disposable", "disposable_administration_only")
    verify(data["control"], authorization, data["authority"], **stop_binding(active, reason, expected_sequence))
    with _store(data, "control") as conn:
        conn.execute("BEGIN IMMEDIATE")
        execution_schema.check_control(conn)
        current = _stop(conn)
        trust.require(current["sequence"] == expected_sequence, "stop_sequence_changed")
        trust.require(not current["sequence"] or trust.utc(now) >= trust.utc(current["recorded_at_utc"]), "stop_clock_rollback")
        trust.require(active or current["active"], "stop_not_active")
        body = dict(sequence=current["sequence"]+1, active=active, reason=reason, actor="project-owner",
                    recorded_at_utc=now, previous_sha256=digest(current) if current["sequence"] else None)
        events._insert(conn, "recognition_execution_stops", "sequence", (body["sequence"],), body)
        conn.commit()
        return body


def _block(control, e, reason, now):
    if not _read(control, "recognition_execution_blocks", e["operation_id"]):
        body = dict(operation_id=e["operation_id"], envelope_sha256=digest(e), enrollment=e["enrollment"],
                    reason=reason, recorded_at_utc=now)
        events._insert(control, "recognition_execution_blocks", "operation_id", (e["operation_id"],), body)


def _writer_evidence(conn, writer_id):
    permanent._verify_operation_records(conn, writer_id)
    tables = ("recognition_private_operations", "recognition_first_look_claims", "recognition_geography_snapshots",
              "recognition_geography_awards")
    result = {}
    for table in tables:
        rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table} WHERE operation_id=?", (writer_id,))]
        result[table] = sorted(rows, key=canonical)
    return digest(result)


def _seal(conn, data):
    e = trust.load(data["envelope"])
    body = _read(conn, "recognition_execution_seals", e["operation_id"])
    if body is None:
        return None
    indexed_writer = conn.execute("SELECT writer_sha256 FROM recognition_execution_seals WHERE operation_id=?",
                                  (e["operation_id"],)).fetchone()[0]
    claim = _read(conn, "recognition_execution_claims", e["operation_id"])
    trust.require(claim is not None and claim["operation_id"] == e["operation_id"] and body["claim_sha256"] == digest(claim)
        and claim["envelope_sha256"] == digest(e) and claim["enrollment"] == e["enrollment"]
        and claim["writer_sha256"] == e["writer_manifest_sha256"], "execution_claim_mismatch")
    trust.require(claim["storage_sha256"] == digest(data["storage"]), "execution_storage_claim_mismatch")
    trust.require(body["writer_sha256"] == indexed_writer == e["writer_manifest_sha256"]
        and body["evidence_sha256"] == _writer_evidence(conn, body["writer_sha256"]), "execution_evidence_mismatch")
    op = operations.get_operation(conn, e["operation_id"])
    archived = trust.verify_historical_authorization(canonical(claim["artifact_json"]),
        operation_json=data["envelope"], provider=data["trust_provider"])
    artifact_payload = trust.load(archived.canonical_json)["payload"]
    trust.require(claim["authorization"] == {"authorization_id": artifact_payload["artifact_id"],
                  "artifact_sha256": archived.sha256}, "execution_claim_authorization_mismatch")
    operations.validate_receipt(op, body["receipt"])
    trust.require(body["receipt"]["operation_id"] == e["operation_id"]
        and body["receipt"]["authorization"] == claim["authorization"], "execution_receipt_mismatch")
    trust.require(canonical(body["receipt"]) == canonical(_receipt(op, claim["authorization"], claim["claimed_at_utc"])),
                  "execution_accounting_evidence_mismatch")
    return body


def _receipt(operation, authorization, now):
    e = operation["envelope"]
    receipt = dict(format="recognition-operation-receipt-v1", synthetic_assertion_only=True,
        operation_id=e["operation_id"], event_id=e["event_id"], authorization=authorization,
        enrollment=e["enrollment"], target_identity=e["target_observation"], outcome="COMPLETED",
        authorized_count=len(e["member_ids"]), successful=[dict(member_id=m,
            outcome_reference=e["writer_manifest_sha256"] + ":" + m) for m in e["member_ids"]],
        quarantined=[], other=[], started_at_utc=now, finished_at_utc=now)
    operations.validate_receipt(operation, receipt)
    return receipt


def _project(conn, data, seal, now, kind):
    e = trust.load(data["envelope"])
    op = operations.get_operation(conn, e["operation_id"])
    if op["receipt"] is None:
        trust.require(op["executions"][-1]["state"] == "EXECUTING", "execution_projection_conflict")
        events._insert(conn, "recognition_operation_receipts", "operation_id", (e["operation_id"],), seal["receipt"])
        operations._append(conn, "executions", e["operation_id"], op["executions"], "COMPLETED",
                           "durable-target-seal-verified", {"receipt_sha256": digest(seal["receipt"])})
    else:
        trust.require(canonical(op["receipt"]) == canonical(seal["receipt"]), "execution_projection_conflict")
    _append(conn, e["operation_id"], "COMPLETED", "durable-target-seal-verified", now, kind)


def _physical(data):
    record = enrollment.verify_record(data["record"], provider=data["enrollment_provider"])
    expected = trust.load(record.canonical_json)["payload"]["target"]
    enrollment._observe(data["enrollment_provider"], data["database"], expected=expected)


def _checks(conn, data, artifact, snapshot, now):
    e = trust.load(data["envelope"])
    op = operations.get_operation(conn, e["operation_id"])
    trust.require(canonical(op["envelope"]) == data["envelope"], "operation_changed")
    trust.require(op["decisions"][-1]["state"] == "AUTHORIZED", "operation_not_authorized")
    trust.require(op["executions"][-1]["state"] in {"NOT_STARTED", "WAITING"}, "unexpected_execution_history")
    trust.require(e["family"] in {"first_look", "geography_steward"} and e["action"] == "finalize"
                  and trust.load(data["manifest"])["format"] == "private-recognition-operation-v1"
                  and e["accounting_policy"] == POLICY, "unsupported_execution_policy_or_finality")
    checked = trust.verify_historical_authorization(artifact, operation_json=data["envelope"], provider=data["trust_provider"])
    trust.verify_authorization_time(artifact, trusted_now_utc=now)
    p = trust.load(checked.canonical_json)["payload"]
    auth = dict(authorization_id=p["artifact_id"], artifact_sha256=checked.sha256)
    trust.require(op["decisions"][-1]["evidence"] == auth, "authorization_history_mismatch")
    verify(conn, data["execution_authorization"], data["authority"], **execution_binding(e))
    result = enrollment.verify_target(data["record"], target_path=data["database"], expected_reference=e["enrollment"],
        trusted_now_utc=now, provider=data["enrollment_provider"])
    if result.state == "VERIFICATION_FAILURE":
        return "WAITING_FOR_VERIFICATION", result.reason, op, auth
    trust.require(result.state == "MATCH", "enrollment:" + result.state)
    dep = dependencies.recheck(conn, e["event_id"])
    if dep["state"] == "VERIFICATION_FAILURE":
        return "WAITING_FOR_VERIFICATION", "dependency_verification_failure", op, auth
    trust.require(dep["state"] == "READY", "dependency:" + dep["state"])
    trust.require(trust.utc(now) >= trust.utc(e["created_at_utc"]), "execution_time_before_operation")
    _receipt(op, auth, now)  # Structural accounting check before admission.
    return "ADMITTED", "final_checks_passed", op, auth


def _pre_execution_projection(conn, oid, state, reason):
    op = operations.get_operation(conn, oid)
    last = op["executions"][-1]["state"]
    if last in {"NOT_STARTED", "WAITING"} and (state == "FAILED_BEFORE_COMMIT" or op["decisions"][-1]["state"] == "AUTHORIZED"):
        operations._append(conn, "executions", oid, op["executions"], state, reason, None)


def _commit_target(conn):
    conn.commit()


def admit_operation(context, **kwargs):
    """Successful admission automatically executes; no second human Execute step."""
    return execute_operation(context, **kwargs)


def execute_operation(context, *, artifact_json, snapshot_json, trusted_now_utc, fault_point=None):
    trust.require(fault_point is None or fault_point in FAULT_POINTS, "invalid_disposable_fault_point")
    try:
        data = _context(context)
        trust.require(data["mode"] == "execution", "execution_context_required")
        trust.utc(trusted_now_utc)
    except (trust.TrustError, OSError):
        return ExecutionResult("BLOCKED", "NOT_STARTED", "production_execution_unavailable")
    e = trust.load(data["envelope"])
    oid, now = e["operation_id"], trusted_now_utc
    claim_attempted = False
    with data["enrollment_provider"]._lock:
        try:
            with _store(data, "control") as control:
                control.execute("BEGIN IMMEDIATE")
                execution_schema.check_control(control)
                blocked = _read(control, "recognition_execution_blocks", oid)
                if blocked:
                    return ExecutionResult("BLOCKED", "FAILED_BEFORE_COMMIT", blocked["reason"])
                try:
                    _physical(data)
                except (trust.TrustError, FileNotFoundError):
                    _block(control, e, "target_identity_mismatch", now)
                    control.commit()
                    return ExecutionResult("BLOCKED", "FAILED_BEFORE_COMMIT", "target_identity_mismatch")
                with connection(data["database"], write=True) as conn:
                    conn.execute("PRAGMA synchronous=FULL")
                    conn.execute("BEGIN IMMEDIATE")
                    execution_schema.check_schema(conn)
                    history = _audit(conn, oid)
                    seal = _seal(conn, data)
                    if seal:
                        if history and history[-1]["state"] == "COMPLETED":
                            return ExecutionResult("ALREADY_EXECUTED", "COMPLETED", "durable_receipt_verified", digest(seal["receipt"]))
                        return ExecutionResult("RECOVERY_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED", "committed_projection_pending")
                    if history and history[-1]["state"] in RECOVERY_STATES:
                        return ExecutionResult("RECOVERY_REQUIRED", history[-1]["state"], "unfinished_durable_claim")
                    if history and history[-1]["state"] == "FAILED_BEFORE_COMMIT":
                        return ExecutionResult("BLOCKED", "FAILED_BEFORE_COMMIT", history[-1]["reason"])
                    if _read(conn, "recognition_execution_claims", oid):
                        return ExecutionResult("RECOVERY_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED", "claim_history_conflict")
                    if _stop(control)["active"]:
                        _append(conn, oid, "WAITING", "emergency_stop", now, "ADMISSION")
                        _pre_execution_projection(conn, oid, "WAITING", "emergency_stop")
                        conn.commit()
                        return ExecutionResult("BLOCKED", "WAITING", "emergency_stop")
                    try:
                        state, reason, op, auth = _checks(conn, data, artifact_json, snapshot_json, now)
                        if state != "ADMITTED":
                            _append(conn, oid, "WAITING", reason, now, "ADMISSION")
                            _pre_execution_projection(conn, oid, "WAITING", reason)
                            conn.commit()
                            return ExecutionResult(state, "WAITING", reason)
                        with _store(data, "checkpoint") as checkpoint:
                            with status._verified_status_transaction(snapshot_json, checkpoint_conn=checkpoint,
                                    trusted_now_utc=now, provider=data["trust_provider"]) as current:
                                s = trust.load(current.canonical_json)["payload"]
                                issuer = trust.load(artifact_json)["payload"]["authority_id"]
                                row = next(r for r in s["authorities"] if r["authority_id"] == issuer)
                                status_issue = None if row["state"] == "ENABLED" and row["key_state"] == "ENABLED" else "authority_revoked"
                                # Target-retained floors survive a checkpoint commit interrupted after target claim.
                                for saved in conn.execute("SELECT body_json,body_sha256 FROM recognition_execution_claims"):
                                    prior = events._read(saved)
                                    if s["sequence"] < prior["status_sequence"]:
                                        status_issue = status_issue or "target_status_sequence_rollback"
                                    if s["sequence"] == prior["status_sequence"]:
                                        if current.sha256 != prior["status_sha256"]:
                                            status_issue = status_issue or "target_status_sequence_conflict"
                                if status_issue is None:
                                    _interrupt("BEFORE_CLAIM", fault_point)
                                    claim = dict(operation_id=oid, envelope_sha256=digest(e), writer_sha256=e["writer_manifest_sha256"],
                                        authorization=auth, artifact_json=trust.load(artifact_json), enrollment=e["enrollment"],
                                        target_identity=e["target_observation"], status_sequence=s["sequence"], status_sha256=current.sha256,
                                        claimed_at_utc=now, storage_sha256=digest(data["storage"]))
                                    events._insert(conn, "recognition_execution_claims", "operation_id", (oid,), claim)
                                    _append(conn, oid, "EXECUTING", "durable_admission", now, "ADMISSION")
                                    operations._append(conn, "executions", oid, op["executions"], "EXECUTING", "durable_admission", None)
                                    claim_attempted = True
                                    conn.commit()  # Entry linearizes under stop/status/witness locks.
                            # A valid revocation snapshot advances its floor even when this operation is denied.
                            trust.require(status_issue is None, status_issue or "status_not_permitted")
                    except (trust.TrustError, AuthorizationError, Quarantined) as error:
                        conn.rollback()
                        reason = str(error)
                        temporary = reason in {"status_not_current", "status_stale", "serialized_json_required"}
                        if _read(conn, "recognition_execution_claims", oid):
                            return ExecutionResult("RECOVERY_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED", "admission_commit_uncertain")
                        conn.execute("BEGIN IMMEDIATE")
                        _append(conn, oid, "WAITING" if temporary else "FAILED_BEFORE_COMMIT", reason, now, "ADMISSION")
                        _pre_execution_projection(conn, oid, "WAITING" if temporary else "FAILED_BEFORE_COMMIT", reason)
                        conn.commit()
                        if not temporary:
                            _block(control, e, reason, now)
                            control.commit()
                        return ExecutionResult("WAITING_FOR_VERIFICATION" if temporary else "BLOCKED",
                            "WAITING" if temporary else "FAILED_BEFORE_COMMIT", reason)
                control.commit()
            _interrupt("AFTER_CLAIM", fault_point)
            return _execute_claim(data, now, fault_point)
        except (sqlite3.Error, OSError):
            if claim_attempted:
                return ExecutionResult("RECOVERY_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED", "claim_or_checkpoint_commit_uncertain")
            return ExecutionResult("WAITING_FOR_VERIFICATION", "WAITING", "infrastructure_verification_failure")
        except (trust.TrustError, Quarantined):
            return ExecutionResult("RECOVERY_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED", "execution_evidence_unverifiable")


def _execute_claim(data, now, fault_point):
    e, manifest = trust.load(data["envelope"]), trust.load(data["manifest"])
    oid = e["operation_id"]
    committing = False
    try:
        _physical(data)
        with connection(data["database"], write=True) as conn:
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("BEGIN IMMEDIATE")
            execution_schema.check_schema(conn)
            trust.require(_audit(conn, oid)[-1]["state"] == "EXECUTING", "execution_claim_fenced")
            _physical(data)
            dep = dependencies.recheck(conn, e["event_id"])
            trust.require(dep["state"] == "READY", "dependency_before_mutation:" + dep["state"])
            # No stop/revocation cancellation after durable execution entry.
            with writer_boundary._lease(conn, data["database"], manifest, data["writer_authorization"], data["authority"]) as token:
                result = permanent.finalize(data["database"], manifest, manifest_sha256=e["writer_manifest_sha256"],
                    authorization_reference=manifest["authorization_reference"], gate=RecognitionGate(issuance=True),
                    authorization=data["writer_authorization"], authority=data["authority"], execution_context=token)
            trust.require(result.get("issued") is True, "writer_outcome_preexisted")
            _interrupt("AFTER_MUTATION", fault_point)
            claim = _read(conn, "recognition_execution_claims", oid)
            receipt = _receipt(operations.get_operation(conn, oid), claim["authorization"], now)
            body = dict(writer_sha256=e["writer_manifest_sha256"], claim_sha256=digest(claim), receipt=receipt,
                        evidence_sha256=_writer_evidence(conn, e["writer_manifest_sha256"]))
            events._insert(conn, "recognition_execution_seals", "operation_id,writer_sha256", (oid, body["writer_sha256"]), body)
            committing = True
            _commit_target(conn)  # Writer effects and authoritative receipt seal are one SQLite commit.
        _interrupt("AFTER_COMMIT", fault_point)
        _physical(data)
        with connection(data["database"], write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            seal = _seal(conn, data)
            trust.require(seal is not None, "durable_execution_seal_missing")
            _project(conn, data, seal, now, "EXECUTION")
            conn.commit()
        _interrupt("AFTER_FINALIZATION", fault_point)
        return ExecutionResult("ADMITTED", "COMPLETED", "durable_execution_complete", digest(receipt))
    except Exception:
        if committing:
            try:
                _physical(data)
                with connection(data["database"], write=True) as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    if _audit(conn, oid)[-1]["state"] == "EXECUTING":
                        _append(conn, oid, "UNKNOWN_RECOVERY_REQUIRED", "commit_or_projection_uncertain", now)
                        conn.commit()
            except Exception:
                pass  # Failure to persist uncertainty never makes a claim retryable.
            return ExecutionResult("RECOVERY_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED", "commit_or_projection_uncertain")
        # No target transaction committed, but never permit a competing recovery fence to be overwritten.
        try:
            _physical(data)
            with connection(data["database"], write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                if _audit(conn, oid)[-1]["state"] == "EXECUTING":
                    _append(conn, oid, "FAILED_BEFORE_COMMIT", "writer_failed_before_commit", now)
                    op = operations.get_operation(conn, oid)
                    if op["executions"][-1]["state"] == "EXECUTING":
                        operations._append(conn, "executions", oid, op["executions"], "FAILED_BEFORE_COMMIT",
                                           "writer_failed_before_commit", None)
                    conn.commit()
        except (sqlite3.Error, OSError, trust.TrustError, Quarantined):
            return ExecutionResult("RECOVERY_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED", "failure_accounting_uncertain")
        return ExecutionResult("BLOCKED", "FAILED_BEFORE_COMMIT", "writer_failed_before_commit")


def reconcile_operation(context, *, recovery_authorization, trusted_now_utc):
    """Project a verified seal or fence an absent outcome; never rerun a writer."""
    data = _context(context)
    e, now = trust.load(data["envelope"]), trusted_now_utc
    trust.utc(now)
    trust.require(getattr(recovery_authorization, "environment", None) == "disposable", "disposable_recovery_only")
    verify(data["database"], recovery_authorization, data["authority"], **execution_binding(e, "reconcile"))
    with data["enrollment_provider"]._lock:
        try:
            _physical(data)
            with connection(data["database"], write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                execution_schema.check_schema(conn)
                history = _audit(conn, e["operation_id"])
                if not history or history[-1]["state"] == "WAITING":
                    return ExecutionResult("WAITING_FOR_VERIFICATION", "NOT_STARTED", "no_execution_claim")
                if history[-1]["state"] == "FAILED_BEFORE_COMMIT":
                    return ExecutionResult("BLOCKED", "FAILED_BEFORE_COMMIT", "previously_fenced")
                seal = _seal(conn, data)
                if seal:
                    if history[-1]["state"] != "COMPLETED":
                        _project(conn, data, seal, now, "RECOVERY")
                        conn.commit()
                    return ExecutionResult("ALREADY_EXECUTED", "COMPLETED", "reconciled_durable_execution", digest(seal["receipt"]))
                writer_id = e["writer_manifest_sha256"]
                residue = any(conn.execute(f"SELECT 1 FROM {table} WHERE operation_id=? LIMIT 1", (writer_id,)).fetchone()
                    for table in ("recognition_private_operations", "recognition_first_look_claims", "recognition_geography_awards",
                                  "recognition_geography_snapshots"))
                if residue or conn.execute("PRAGMA foreign_key_check").fetchone():
                    _append(conn, e["operation_id"], "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED", "outcomes_without_seal", now, "RECOVERY")
                    conn.commit()
                    return ExecutionResult("RECOVERY_REQUIRED", "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED", "outcomes_without_seal")
                # BEGIN IMMEDIATE fences a delayed original worker before proving absence.
                _append(conn, e["operation_id"], "FAILED_BEFORE_COMMIT", "reconciled_no_durable_effects", now, "RECOVERY")
                op = operations.get_operation(conn, e["operation_id"])
                if op["executions"][-1]["state"] == "EXECUTING":
                    operations._append(conn, "executions", e["operation_id"], op["executions"], "FAILED_BEFORE_COMMIT",
                                       "reconciled_no_durable_effects", None)
                conn.commit()
                return ExecutionResult("BLOCKED", "FAILED_BEFORE_COMMIT", "reconciled_no_durable_effects_new_operation_required")
        except (trust.TrustError, Quarantined, sqlite3.Error, OSError):
            return ExecutionResult("RECOVERY_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED", "recovery_evidence_unverifiable")
