"""Local administrative approval records, never writer authorization/capabilities.

All approval effects live in the control store. The target is locked but never
modified. Trusted host/database administrators remain outside this threat model.
"""

from uuid import uuid4

from . import administration as a, admin_auth as auth, approval_schema as schema
from . import dependencies, events, operations
from .qualification import Quarantined
from .rules import canonical, digest


FORMAT = "recognition-local-approval-v1"


def install(config, *, operator, reason, now):
    """Explicit trusted-host migration, never invoked by a web/startup path."""
    a.need(type(operator) is str and bool(operator.strip()) and type(reason) is str and bool(reason.strip()), "approval_install_ceremony_required")
    with a.transaction(config, lock_target=True) as (conn, _, _binding):
        schema.install(conn)
        a._audit(conn, "approval_schema_installed", operator, now, dict(reason=reason))


def _snapshot(target, operation_id, binding):
    # get_operation verifies the envelope, immutable history, frozen preparation,
    # population and accounting policy using the original Slice 3 contract.
    op = operations.get_operation(target, operation_id)
    e = op["envelope"]
    frozen = events.get_event(target, e["event_id"])
    p = frozen["preparation"]
    if e["format"] == operations.LOCAL_CONTRACT:
        from .production_operations import local_target
        a.need(e["local_target"] == local_target(binding), "production_operation_generation_or_target_changed")
    a.need(op["decisions"][-1]["state"] == "PREPARED" and op["executions"][-1]["state"] == "NOT_STARTED"
           and op["receipt"] is None and frozen["state"] == "READY", "operation_not_approvable")
    a.need(e["target_observation"] == binding["target"]["observation"], "operation_target_mismatch")
    a.need(e["member_ids"] == [digest(c) for c in p["manifest"]["candidates"]]
           and len(set(e["member_ids"])) == len(e["member_ids"]), "invalid_operation_accounting")
    dependency_state = dependencies.recheck(target, e["event_id"])["state"]
    a.need(dependency_state != "VERIFICATION_FAILURE", "approval_dependency_verification_unavailable", 503)
    a.need(dependency_state == "READY", "approval_dependencies_not_ready")
    return dict(operation_id=operation_id, operation_sha256=digest(e), event_id=e["event_id"],
        event_sha256=e["event_sha256"], preparation_id=e["preparation_id"], preparation_sha256=e["preparation_sha256"],
        # This is the existing operation generation, not a new identity system.
        operation_generation=p["request"]["generation_reference"],
        population_sha256=e["population_sha256"], accounting_policy_sha256=digest(e["accounting_policy"]),
        installation_id=binding["installation_id"], target_id=binding["target_id"],
        target_observation=binding["target"], restore_generation=binding["generation"],
        operation_state_sha256=auth._operation(target, operation_id)[1],
        operation_state=dict(decision="PREPARED", execution="NOT_STARTED", event="READY"),
        operation_contract_format=e["format"], synthetic_contract_only=e.get("synthetic_contract_only", False))


def _read(conn, approval_id):
    row = conn.execute("SELECT * FROM recognition_approvals WHERE approval_id=?", (approval_id,)).fetchone()
    a.need(row is not None, "approval_not_found", 404)
    body = events._read((row["body_json"], row["body_sha256"]))
    a.need(body["format"] == FORMAT and body["approval_id"] == approval_id and body["state"] == "APPROVED"
           and body["binding"]["operation_id"] == row["operation_id"]
           and body["confirmation_sha256"] == row["confirmation_sha256"], "approval_integrity_failure", 503)
    history = []
    for record in conn.execute("SELECT * FROM recognition_approval_history WHERE approval_id=? ORDER BY sequence", (approval_id,)):
        item = events._read((record["body_json"], record["body_sha256"]))
        a.need(item["approval_id"] == approval_id and item["approval_sha256"] == digest(body)
               and item["binding"] == body["binding"] and item["confirmation_sha256"] == body["confirmation_sha256"]
               and item["sequence"] == record["sequence"] == len(history)+1
               and item["state"] == record["state"]
               and item["previous_sha256"] == (digest(history[-1]) if history else None)
               and item["prior_state"] == (history[-1]["state"] if history else "PENDING")
               and (item["state"] in {"INVALIDATED", "SUPERSEDED"} and history[-1]["state"] == "APPROVED"
                    if history else item["state"] == "APPROVED"), "approval_history_integrity_failure", 503)
        history.append(item)
    a.need(bool(history), "approval_history_missing", 503)
    return dict(approval=body, approval_sha256=digest(body), history=history, state=history[-1]["state"],
                execution_pending=True, production_authorization="BLOCKED", production_execution="BLOCKED")


def _append(conn, body, history, state, actor, now, reason):
    item = dict(format="recognition-local-approval-history-v1", approval_id=body["approval_id"],
        approval_sha256=digest(body), binding=body["binding"], confirmation_sha256=body["confirmation_sha256"],
        action="approve" if not history else state.lower(), actor_id=actor, at_utc=now, reason=reason,
        prior_state=history[-1]["state"] if history else "PENDING", state=state,
        sequence=len(history)+1, previous_sha256=digest(history[-1]) if history else None)
    conn.execute("INSERT INTO recognition_approval_history VALUES(?,?,?,?,?)",
                 (body["approval_id"], item["sequence"], state, canonical(item), digest(item)))


def _invalidate_all(conn, actor, now, reason):
    for row in conn.execute("SELECT approval_id FROM recognition_approvals").fetchall():
        value = _read(conn, row[0])
        if value["state"] == "APPROVED":
            _append(conn, value["approval"], value["history"], "INVALIDATED", actor, now, reason)


def _reconcile(conn, target, binding, value, actor, now):
    if value["state"] != "APPROVED":
        return value
    # A verified committed outcome is history, not a pending approval whose
    # dependency snapshot should still exclude its OWN newly written awards.
    if target.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_execution_claims'").fetchone():
        oid = value["approval"]["binding"]["operation_id"]
        row = target.execute("SELECT body_json,body_sha256 FROM recognition_execution_claims WHERE operation_id=?", (oid,)).fetchone()
        if row and events._read(row).get("format") == "recognition-local-execution-claim-v1":
            from . import local_execution
            seal = local_execution._seal(target, oid, value)
            if seal:
                history = local_execution.journal._audit(target, oid)
                return dict(value, execution_pending=not (history and history[-1]["state"] == "COMPLETED"),
                            execution_state=history[-1]["state"] if history else "UNKNOWN_RECOVERY_REQUIRED")
    try:
        matches = _snapshot(target, value["approval"]["binding"]["operation_id"], binding) == value["approval"]["binding"]
    except a.AdminError as error:
        if error.status == 503:
            raise
        matches = False
    except Quarantined:
        matches = False
    if not matches:
        _append(conn, value["approval"], value["history"], "INVALIDATED", actor, now, "operation-or-dependency-binding-changed")
        a._audit(conn, "approval_invalidated", actor, now, dict(approval_id=value["approval"]["approval_id"]))
        return _read(conn, value["approval"]["approval_id"])
    return value


def _fault(point):
    """Deterministic test seam; never configured through HTTP/environment."""


def create_approval(config, session_token, step_token, confirmation_token, *, operation_id, reason, now):
    a.need(type(reason) is str and 1 <= len(reason.strip()) <= 2000, "approval_reason_required", 400)
    with a.transaction(config, lock_target=True) as (conn, target, binding):
        schema.check(conn)
        _fault("A")
        session, _ = auth._session(conn, target, binding, session_token, now)
        step = auth._step(conn, target, binding, session, step_token, "approve", operation_id, now)
        snapshot = _snapshot(target, operation_id, binding)
        confirmation_sha = a.token_hash(confirmation_token)
        row = conn.execute("SELECT * FROM recognition_admin_confirmations WHERE token_hash=?", (confirmation_sha,)).fetchone()
        a.need(row is not None and not row["used"] and row["session_hash"] == session["token_hash"]
               and row["actor"] == session["actor"] and row["generation"] == binding["generation"]
               and row["operation_id"] == operation_id and row["operation_sha256"] == snapshot["operation_sha256"]
               and row["state_sha256"] == snapshot["operation_state_sha256"]
               and a.timestamp(now) < row["expires"] and row["expires"] <= step["expires"], "invalid_or_consumed_confirmation")
        a.need(not conn.execute("SELECT 1 FROM recognition_approvals WHERE operation_id=?", (operation_id,)).fetchone(), "operation_already_has_approval", 409)
        _fault("B")
        changed = conn.execute("UPDATE recognition_admin_confirmations SET used=1 WHERE token_hash=? AND used=0", (confirmation_sha,))
        a.need(changed.rowcount == 1, "confirmation_conflict", 409)
        _fault("C")
        body = dict(format=FORMAT, approval_id=str(uuid4()), binding=snapshot,
            actor_id=session["actor"], session_sha256=session["token_hash"], confirmation_sha256=confirmation_sha,
            approved_at_utc=now, state="APPROVED", reason=reason, predecessor_sha256=None,
            execution_authority=False)
        conn.execute("INSERT INTO recognition_approvals VALUES(?,?,?,?,?)", (body["approval_id"], operation_id, confirmation_sha, canonical(body), digest(body)))
        _fault("D")
        _append(conn, body, [], "APPROVED", session["actor"], now, reason)
        a._audit(conn, "operation_approved_execution_pending", session["actor"], now,
                 dict(approval_id=body["approval_id"], approval_sha256=digest(body), confirmation_sha256=confirmation_sha))
        result = _read(conn, body["approval_id"])
        _fault("E")
    _fault("F")  # Lost acknowledgement: authenticated list/get recovers the record.
    return result


approve_operation = create_approval


def get_approval(config, session_token, approval_id, *, now):
    with a.transaction(config, lock_target=True) as (conn, target, binding):
        schema.check(conn)
        session, _ = auth._session(conn, target, binding, session_token, now)
        return _reconcile(conn, target, binding, _read(conn, approval_id), session["actor"], now)


def list_operation_approvals(config, session_token, operation_id, *, now):
    with a.transaction(config, lock_target=True) as (conn, target, binding):
        schema.check(conn)
        session, _ = auth._session(conn, target, binding, session_token, now)
        return [_reconcile(conn, target, binding, _read(conn, row[0]), session["actor"], now)
                for row in conn.execute("SELECT approval_id FROM recognition_approvals WHERE operation_id=?", (operation_id,)).fetchall()]


def invalidate_approval(config, session_token, step_token, approval_id, *, reason, now, superseded=False):
    a.need(type(reason) is str and bool(reason.strip()) and len(reason) <= 2000, "invalidation_reason_required")
    with a.transaction(config, lock_target=True) as (conn, target, binding):
        schema.check(conn)
        session, _ = auth._session(conn, target, binding, session_token, now)
        value = _read(conn, approval_id)
        auth._step(conn, target, binding, session, step_token, "approve", value["approval"]["binding"]["operation_id"], now)
        a.need(value["state"] == "APPROVED", "approval_already_terminal", 409)
        _append(conn, value["approval"], value["history"], "SUPERSEDED" if superseded else "INVALIDATED", session["actor"], now, reason)
        a._audit(conn, "approval_manually_invalidated", session["actor"], now, dict(approval_id=approval_id, reason=reason))
        return _read(conn, approval_id)
