"""Immutable contracts and synthetic assertions, never authorization or execution.

All writes require existing disposable authority and a caller-owned transaction.
No imports into writers/Flask, no production capability, no executor or recovery.
"""

from contextlib import contextmanager
import json
import re
from uuid import uuid4

from . import dependencies, events, operation_schema
from .authorization import target_identity, verify
from .geography import _utc
from .qualification import Quarantined, require_transaction
from .rules import canonical, digest


CONTRACT = "recognition-operation-contract-v1"
ENROLLED_CONTRACT = "recognition-operation-contract-v2"
LOCAL_CONTRACT = "recognition-local-operation-v1"
LOCAL_HISTORY = "recognition-local-operation-history-v1"
LOCAL_POLICY = {"reference": "atomic-historical-v1", "quarantine_categories": [], "other_categories": []}
TERMINAL = {state for state, targets in operation_schema.EXECUTIONS.items() if not targets}
NORMAL = {"COMPLETED", "COMPLETED_WITH_QUARANTINE"}


def _require(condition, code):
    events._require(condition, code)


def _copy(value):
    return json.loads(canonical(value))


def _text(value):
    return type(value) is str and bool(value.strip())


def _sha(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def binding(action, subject):
    """Exact permission to persist synthetic contract data, not executive approval."""
    _require(action in {"create", "decision", "execution"}, "invalid_operation_action")
    return dict(family="recognition_operations", permission="contract_history", action=action,
                operation_sha256=digest(subject), policy_sha256=digest(CONTRACT),
                population_sha256=None)


@contextmanager
def _write(conn, action, subject, authorization, authority):
    require_transaction(conn)
    operation_schema.check_schema(conn)
    _require(getattr(authorization, "environment", None) == "disposable",
             "synthetic_operation_persistence_only")
    verify(conn, authorization, authority, **binding(action, subject))
    conn.execute("SAVEPOINT recognition_operation_write")
    try:
        conn.execute("UPDATE recognition_operation_contracts SET body_json=body_json WHERE 0")
        yield
        verify(conn, authorization, authority, **binding(action, subject))
    except BaseException:
        conn.execute("ROLLBACK TO recognition_operation_write")
        raise
    finally:
        conn.execute("RELEASE recognition_operation_write")


def _policy(policy):
    _require(type(policy) is dict and set(policy) == {"reference", "quarantine_categories", "other_categories"}
             and _text(policy["reference"]), "invalid_accounting_policy")
    for key in ("quarantine_categories", "other_categories"):
        values = policy[key]
        _require(type(values) is list and all(_text(v) for v in values)
                 and len(set(values)) == len(values), "invalid_accounting_policy")
    _require(not set(policy["quarantine_categories"]) & set(policy["other_categories"]),
             "ambiguous_accounting_category")


def _envelope(frozen, operation_id, policy, created, enrollment_binding=None):
    p, e = frozen["preparation"], frozen["event"]
    m = p["manifest"]
    return dict(format=CONTRACT if enrollment_binding is None else ENROLLED_CONTRACT,
                synthetic_contract_only=True, operation_id=operation_id,
                event_id=e["event_id"], event_sha256=digest(e),
                preparation_id=p["preparation_id"], preparation_sha256=digest(p),
                parent_event_id=e["parent_event_id"], dependencies_sha256=digest(p["dependencies"]),
                family=m["family"], action="finalize", writer_manifest_sha256=p["manifest_sha256"],
                target_observation=p["target_observation"],
                enrollment=enrollment_binding if enrollment_binding is not None else {"enrollment_id": None, "generation": None},
                rule=m["rule"], rule_sha256=m["rule_sha256"],
                population_sha256=p["population_sha256"],
                member_ids=[digest(c) for c in m["candidates"]],
                accounting_policy=policy, created_at_utc=created,
                frozen_at_utc=e["frozen_at_utc"], provenance=p["request"])


def _insert(conn, table, keys, values, body):
    events._insert(conn, table, keys, values, body)


def _local_envelope(frozen, operation_id, created, local_target, creation):
    body = _envelope(frozen, operation_id, LOCAL_POLICY, created)
    del body["synthetic_contract_only"], body["enrollment"]
    return dict(body, format=LOCAL_CONTRACT, operation_version=1, initial_state="PREPARED",
                local_target=local_target, creation=creation)


def _append_local(conn, kind, operation_id, history, state, reason, now, evidence=None):
    body = dict(format=LOCAL_HISTORY, operation_id=operation_id, sequence=len(history)+1,
                state=state, reason=reason, evidence=evidence, recorded_at_utc=now,
                previous_sha256=digest(history[-1]) if history else None)
    _insert(conn, "recognition_operation_" + kind, "operation_id,sequence,state",
            (operation_id, body["sequence"], state), body)


def _append(conn, kind, operation_id, history, state, reason, evidence):
    body = dict(operation_id=operation_id, sequence=len(history)+1, state=state,
                reason=reason, evidence=evidence, recorded_at_utc=events._now(),
                previous_sha256=digest(history[-1]) if history else None,
                synthetic_assertion_only=True)
    _insert(conn, "recognition_operation_" + kind, "operation_id,sequence,state",
            (operation_id, body["sequence"], state), body)


def create_operation(conn, event_id, accounting_policy, *, authorization=None, authority=None,
                     enrollment_reference=None, enrollment_provider=None, trusted_now_utc=None):
    """Freeze one contract per frozen event; an identical replay returns it unchanged."""
    policy = _copy(accounting_policy)
    _policy(policy)
    subject = dict(event_id=event_id, accounting_policy=policy)
    enrollment_reference = _copy(enrollment_reference)
    if enrollment_reference is not None:
        from . import enrollment
        enrollment.validate_reference(enrollment_reference)
        subject["enrollment"] = enrollment_reference
    with _write(conn, "create", subject, authorization, authority):
        old = conn.execute("SELECT operation_id FROM recognition_operation_contracts WHERE event_id=?",
                           (event_id,)).fetchone()
        if old:
            current = get_operation(conn, old[0])
            _require(current["envelope"]["accounting_policy"] == policy, "operation_create_conflict")
            _require(current["envelope"]["enrollment"] == (enrollment_reference if enrollment_reference is not None
                     else {"enrollment_id": None, "generation": None}), "operation_enrollment_conflict")
            return current
        frozen = events.get_event(conn, event_id)
        _require(frozen["state"] == "READY", "event_not_ready")
        dependencies.validate_binding(frozen["preparation"]["dependencies"], frozen["preparation"]["manifest"])
        _require(frozen["preparation"]["target_observation"] == _copy_target(conn), "operation_target_changed")
        if enrollment_reference is not None:
            enrollment._context(enrollment_provider)
            record = enrollment_provider.record(enrollment_reference["enrollment_id"])
            result = enrollment.verify_target(record, target_path=_copy_target(conn)["database"],
                expected_reference=enrollment_reference, trusted_now_utc=trusted_now_utc, provider=enrollment_provider)
            _require(result.state == "MATCH", "operation_enrollment_not_matching:" + result.state)
        body = _envelope(frozen, str(uuid4()), policy, events._now(), enrollment_reference)
        _require(len(set(body["member_ids"])) == len(body["member_ids"]), "duplicate_population_member")
        _insert(conn, "recognition_operation_contracts", "operation_id,event_id",
                (body["operation_id"], event_id), body)
        _append(conn, "decisions", body["operation_id"], [], "PREPARED", "contract-created", None)
        _append(conn, "executions", body["operation_id"], [], "NOT_STARTED", "contract-created", None)
        return get_operation(conn, body["operation_id"])


def _copy_target(conn):
    from dataclasses import asdict
    return asdict(target_identity(conn))


def _history(conn, kind, operation_id, *, local=False):
    graph = operation_schema.DECISIONS if kind == "decisions" else operation_schema.EXECUTIONS
    initial = "PREPARED" if kind == "decisions" else "NOT_STARTED"
    history = []
    for row in conn.execute(f"SELECT body_json,body_sha256,sequence,state FROM recognition_operation_{kind} "
                            "WHERE operation_id=? ORDER BY sequence", (operation_id,)):
        body = events._read(row)
        _require(set(body) == {"operation_id", "sequence", "state", "reason", "evidence",
                              "recorded_at_utc", "previous_sha256", "format" if local else "synthetic_assertion_only"},
                 "malformed_operation_history")
        _utc(body["recorded_at_utc"])
        _require(body["operation_id"] == operation_id and body["sequence"] == row[2] == len(history)+1
                 and body["state"] == row[3] and _text(body["reason"])
                 and (body["format"] == LOCAL_HISTORY if local else body["synthetic_assertion_only"] is True)
                 and body["previous_sha256"] == (digest(history[-1]) if history else None)
                 and (body["state"] in graph[history[-1]["state"]] if history else body["state"] == initial),
                 "invalid_operation_history")
        history.append(body)
    _require(bool(history), "operation_history_missing")
    return history


def _authorization_reference(value):
    _require(type(value) is dict and set(value) == {"authorization_id", "artifact_sha256"}
             and _text(value["authorization_id"]) and _sha(value["artifact_sha256"]),
             "authorization_reference_required")


def get_operation(conn, operation_id):
    """Detached historical assertions only; no executable capability is returned."""
    try:
        return _get_operation(conn, operation_id)
    except Quarantined:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise Quarantined("malformed_operation_contract") from error


def _get_operation(conn, operation_id):
    operation_schema.check_schema(conn)
    row = conn.execute("SELECT body_json,body_sha256,event_id FROM recognition_operation_contracts "
                       "WHERE operation_id=?", (operation_id,)).fetchone()
    body = events._read(row)
    frozen = events.get_event(conn, row[2])
    _policy(body["accounting_policy"])
    _utc(body["created_at_utc"])
    enrollment_binding = body["enrollment"] if body["format"] == ENROLLED_CONTRACT else None
    if enrollment_binding is not None:
        from .enrollment import validate_reference
        validate_reference(enrollment_binding)
    local = body["format"] == LOCAL_CONTRACT
    if local:
        from .production_operations import validate_local_target
        validate_local_target(body["local_target"])
        creation = body["creation"]
        _require(set(creation) == {"request_id", "request_sha256", "actor_id"}
                 and _text(creation["request_id"]) and _sha(creation["request_sha256"])
                 and type(creation["actor_id"]) is int, "invalid_local_creation")
        _require(body["local_target"]["target"]["observation"] == body["target_observation"]
                 and frozen["preparation"]["request"]["generation_reference"] == body["local_target"]["installation_id"]+":"+str(body["local_target"]["restore_generation"])
                 and frozen["preparation"]["request"]["preparer_id"] == str(creation["actor_id"]), "local_preparation_target_binding_mismatch")
    expected = (_local_envelope(frozen, operation_id, body["created_at_utc"], body["local_target"], body["creation"])
                if local else _envelope(frozen, operation_id, body["accounting_policy"], body["created_at_utc"], enrollment_binding))
    _require(body == expected,
             "operation_binding_mismatch")
    decisions = _history(conn, "decisions", operation_id, local=local)
    executions = _history(conn, "executions", operation_id, local=local)
    for decision in decisions:
        if decision["state"] == "AUTHORIZED":
            if local:
                ref = decision["evidence"]
                _require(type(ref) is dict and set(ref) == {"approval_id", "approval_sha256"}
                         and _text(ref["approval_id"]) and _sha(ref["approval_sha256"]), "local_approval_reference_required")
            else:
                _authorization_reference(decision["evidence"])
        else:
            _require(decision["evidence"] is None, "unexpected_decision_evidence")
    if any(x["state"] in {"WAITING", "EXECUTING"} | NORMAL for x in executions):
        _require(any(d["state"] == "AUTHORIZED" for d in decisions), "authorized_assertion_required")
    if executions[-1]["state"] == "EXECUTING":
        _require(decisions[-1]["state"] == "AUTHORIZED", "decision_execution_mismatch")
    receipt_row = conn.execute("SELECT body_json,body_sha256 FROM recognition_operation_receipts "
                               "WHERE operation_id=?", (operation_id,)).fetchone()
    receipt = events._read(receipt_row) if receipt_row else None
    result = dict(envelope=body, decisions=decisions, executions=executions, receipt=receipt)
    if local:
        result["operation_sha256"] = digest(body)
    if receipt is not None:
        validate_receipt(result, receipt)
        _require(executions[-1]["state"] == receipt["outcome"]
                 and executions[-1]["evidence"] == {"receipt_sha256": digest(receipt)},
                 "receipt_history_mismatch")
    else:
        _require(executions[-1]["state"] not in NORMAL, "completion_receipt_missing")
    for execution in executions:
        _require(execution["evidence"] == (
            {"receipt_sha256": digest(receipt)} if receipt is not None and execution is executions[-1]
            else None), "execution_evidence_mismatch")
    return result


def record_decision(conn, operation_id, state, reason, *, evidence=None,
                    event_authorization=None, event_authority=None, authorization=None, authority=None):
    """Record a synthetic decision, never validate or manufacture an approval."""
    evidence = _copy(evidence)
    subject = dict(operation_id=operation_id, state=state, reason=reason, evidence=evidence)
    with _write(conn, "decision", subject, authorization, authority):
        current = get_operation(conn, operation_id)
        last = current["decisions"][-1]
        _require(_text(reason), "decision_reason_required")
        if all(last[k] == subject[k] for k in ("state", "reason", "evidence")):
            return current
        _require(state in operation_schema.DECISIONS[last["state"]], "invalid_decision_transition")
        _require(current["executions"][-1]["state"] in {"NOT_STARTED", "WAITING"}
                 or (state == "SUPERSEDED" and current["executions"][-1]["state"] in TERMINAL),
                 "execution_history_already_started")
        if state == "AUTHORIZED":
            _authorization_reference(evidence)
            _require(events.get_event(conn, current["envelope"]["event_id"])["state"] == "READY",
                     "event_not_ready")
        else:
            _require(evidence is None, "unexpected_decision_evidence")
        if state == "SENT_BACK":
            events.record_event_state(conn, current["envelope"]["event_id"], "INVALID", reason,
                                      authorization=event_authorization, authority=event_authority)
        _append(conn, "decisions", operation_id, current["decisions"], state, reason, evidence)
        return get_operation(conn, operation_id)


def validate_receipt(operation, receipt):
    """Validate accounting assertions, not commit truth or target durability."""
    if operation["envelope"]["format"] == LOCAL_CONTRACT:
        from .production_receipts import validate
        return validate(operation, receipt)
    e = operation["envelope"]
    _require(type(receipt) is dict and set(receipt) == {
        "format", "synthetic_assertion_only", "operation_id", "event_id", "authorization",
        "enrollment", "target_identity", "outcome", "authorized_count", "successful",
        "quarantined", "other", "started_at_utc", "finished_at_utc"}, "invalid_receipt")
    auth = next((d["evidence"] for d in operation["decisions"] if d["state"] == "AUTHORIZED"), None)
    _require(auth is not None and receipt["authorization"] == auth, "receipt_authorization_mismatch")
    _require(receipt["format"] == "recognition-operation-receipt-v1"
             and receipt["synthetic_assertion_only"] is True
             and receipt["operation_id"] == e["operation_id"] and receipt["event_id"] == e["event_id"]
             and canonical(receipt["enrollment"]) == canonical(e["enrollment"])
             and receipt["target_identity"] == e["target_observation"], "receipt_binding_mismatch")
    _require(receipt["outcome"] in TERMINAL, "invalid_receipt_outcome")
    _utc(receipt["started_at_utc"])
    _utc(receipt["finished_at_utc"])
    _require(e["created_at_utc"] <= receipt["started_at_utc"] <= receipt["finished_at_utc"],
             "invalid_receipt_timestamps")
    _require(type(receipt["authorized_count"]) is int
             and receipt["authorized_count"] == len(e["member_ids"]), "receipt_population_mismatch")
    seen = []
    for group in ("successful", "quarantined", "other"):
        _require(type(receipt[group]) is list, "invalid_receipt_items")
        for item in receipt[group]:
            fields = {"member_id", "outcome_reference"} if group == "successful" else {
                "member_id", "outcome_reference", "category", "reason"}
            _require(type(item) is dict and set(item) == fields
                     and _text(item["outcome_reference"]) and item["member_id"] in e["member_ids"],
                     "invalid_receipt_item")
            if group != "successful":
                key = "quarantine_categories" if group == "quarantined" else "other_categories"
                _require(item["category"] in e["accounting_policy"][key] and _text(item["reason"]),
                         "unapproved_accounting_category")
            seen.append(item["member_id"])
    _require(len(seen) == len(set(seen)), "duplicate_receipt_member")
    if receipt["outcome"] == "FAILED_BEFORE_COMMIT":
        _require(not receipt["successful"], "failed_before_commit_has_successes")
    if receipt["outcome"] in NORMAL:
        _require(set(seen) == set(e["member_ids"]), "incomplete_receipt_accounting")
        _require(bool(receipt["quarantined"]) == (receipt["outcome"] == "COMPLETED_WITH_QUARANTINE"),
                 "quarantine_outcome_mismatch")
    return dict(authorized=len(e["member_ids"]), successful=len(receipt["successful"]),
                quarantined=len(receipt["quarantined"]), other=len(receipt["other"]),
                unaccounted=len(e["member_ids"])-len(seen))


def record_execution(conn, operation_id, state, reason, *, receipt=None, authorization=None, authority=None):
    """Append a disposable execution assertion. This function performs no execution."""
    receipt = _copy(receipt)
    subject = dict(operation_id=operation_id, state=state, reason=reason, receipt=receipt)
    with _write(conn, "execution", subject, authorization, authority):
        current = get_operation(conn, operation_id)
        last = current["executions"][-1]
        _require(_text(reason), "execution_reason_required")
        evidence = {"receipt_sha256": digest(receipt)} if receipt is not None else None
        if last["state"] == state and last["reason"] == reason and last["evidence"] == evidence:
            _require(current["receipt"] == receipt, "receipt_replay_mismatch")
            return current
        _require(state in operation_schema.EXECUTIONS[last["state"]], "invalid_execution_transition")
        if state in {"WAITING", "EXECUTING"} or state in NORMAL:
            _require(current["decisions"][-1]["state"] == "AUTHORIZED", "authorized_assertion_required")
            _require(events.get_event(conn, current["envelope"]["event_id"])["state"] == "READY",
                     "event_not_ready")
        if state in NORMAL:
            _require(receipt is not None, "completion_receipt_required")
        if receipt is not None:
            _require(state in TERMINAL and receipt["outcome"] == state, "receipt_outcome_mismatch")
            validate_receipt(current, receipt)
            _insert(conn, "recognition_operation_receipts", "operation_id", (operation_id,), receipt)
        _append(conn, "executions", operation_id, current["executions"], state, reason, evidence)
        return get_operation(conn, operation_id)
