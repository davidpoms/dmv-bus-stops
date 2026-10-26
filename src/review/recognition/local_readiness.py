"""Simplified local readiness; assessment never activates/provisions production."""

import sqlite3
import secrets

from . import administration as a, admin_auth as auth, approvals, execution as journal, execution_schema
from . import events, operations, production_operations, local_execution, writer_boundary, permanent
from .rules import canonical, digest
from .qualification import Quarantined


STATES = {"NOT_ACTIVATED", "ACTIVATED", "SUSPENDED", "DEACTIVATED", "RECOVERY_REQUIRED"}
TRANSITIONS = {state: STATES - {state, "NOT_ACTIVATED"} for state in STATES}
TRANSITIONS["RECOVERY_REQUIRED"] = {"DEACTIVATED"}
REHEARSAL_CHECKS = frozenset(("sqlite_locking", "concurrent_workers", "filesystem_permissions", "control_persistence",
    "backup_creation", "backup_restoration", "background_jobs", "restart_behavior", "process_lifecycle",
    "secret_protection", "no_startup_activation", "writer_lock"))


def definitions():
    table = "recognition_local_activation"
    result = {table: f"CREATE TABLE {table} (sequence INTEGER PRIMARY KEY CHECK(sequence>=1), body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL)"}
    for verb in ("UPDATE", "DELETE"):
        name = table+"_immutable_"+verb.lower()
        result[name] = f"CREATE TRIGGER {name} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_local_activation'); END"
    result[table+"_immutable_replace"] = f"CREATE TRIGGER {table}_immutable_replace BEFORE INSERT ON {table} WHEN EXISTS(SELECT 1 FROM {table} WHERE sequence=NEW.sequence) BEGIN SELECT RAISE(ABORT,'immutable_local_activation'); END"
    result[table+"_sequence"] = f"CREATE TRIGGER {table}_sequence BEFORE INSERT ON {table} WHEN NEW.sequence != COALESCE((SELECT MAX(sequence) FROM {table}),0)+1 BEGIN SELECT RAISE(ABORT,'local_activation_sequence_conflict'); END"
    return result


def _state(control, binding):
    a.need(control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_local_activation'").fetchone(), "local_readiness_install_required", 503)
    history = []
    for row in control.execute("SELECT body_json,body_sha256,sequence FROM recognition_local_activation ORDER BY sequence"):
        body = events._read(row)
        a.need(body["sequence"] == row[2] == len(history)+1 and body["state"] in STATES
               and body["previous_sha256"] == (digest(history[-1]) if history else None), "local_activation_history_invalid", 503)
        if history:
            previous = history[-1]
            prior = previous["state"] if previous["target"] == body["target"] else "NOT_ACTIVATED"
            a.need(body["state"] in TRANSITIONS[prior] and a.timestamp(body["at_utc"]) >= a.timestamp(previous["at_utc"]), "invalid_local_activation_transition", 503)
        else:
            a.need(body["state"] == "NOT_ACTIVATED", "activation_requires_explicit_genesis", 503)
        history.append(body)
    a.need(bool(history), "local_activation_state_missing", 503)
    current = history[-1]
    if current["target"] != production_operations.local_target(binding):
        return dict(state="NOT_ACTIVATED", sequence=current["sequence"], restored_generation=True)
    return current


def _append(control, binding, state, actor, reason, now, *, readiness=None, scope="local-production-blocked", confirmation=None):
    row = control.execute("SELECT body_json,body_sha256,sequence FROM recognition_local_activation ORDER BY sequence DESC LIMIT 1").fetchone()
    body = dict(format="recognition-local-activation-v1", sequence=row[2]+1 if row else 1, state=state,
        target=production_operations.local_target(binding), actor_id=actor, reason=reason, at_utc=now,
        readiness_sha256=digest(readiness) if readiness else None, scope=scope, previous_sha256=row[1] if row else None)
    if confirmation is not None:
        body.update(confirmation_sha256=confirmation["token_hash"], ceremony_sha256=confirmation["state_sha256"])
    control.execute("INSERT INTO recognition_local_activation VALUES(?,?,?)", (body["sequence"], canonical(body), digest(body)))
    a._audit(control, "local_activation_state_recorded", actor, now, body)
    return body


def install(config, *, operator, reason, now):
    a.need(type(operator) is str and bool(operator.strip()) and type(reason) is str and bool(reason.strip()), "readiness_install_ceremony_required")
    with a.transaction(config, lock_target=True) as (control, _, binding):
        approvals.schema.check(control)
        control.execute("SAVEPOINT install_local_readiness")
        try:
            for name, sql in definitions().items():
                if not control.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone():
                    control.execute(sql)
            a.schema.check_control(control)
            if not control.execute("SELECT 1 FROM recognition_local_activation").fetchone():
                _append(control, binding, "NOT_ACTIVATED", operator, reason, now)
            if not journal._stop(control)["sequence"]:
                body = dict(sequence=1, active=False, reason="local-readiness-explicit-install", actor=operator, recorded_at_utc=now, previous_sha256=None)
                events._insert(control, "recognition_execution_stops", "sequence", (1,), body)
        except BaseException:
            control.execute("ROLLBACK TO install_local_readiness")
            raise
        finally:
            control.execute("RELEASE install_local_readiness")


def record_deployment_rehearsal(config, *, operator, reason, evidence, now):
    """Trusted host's explicit later rehearsal observations; no external access."""
    a.need(type(operator) is str and bool(operator.strip()) and type(reason) is str and bool(reason.strip()), "deployment_observation_ceremony_required")
    a.need(type(evidence) is dict and set(evidence) == REHEARSAL_CHECKS and all(operations._sha(v) for v in evidence.values()), "deployment_rehearsal_evidence_required")
    with a.transaction(config, lock_target=True) as (control, _, binding):
        a._audit(control, "local_deployment_rehearsal_recorded", operator, now,
                 dict(target=production_operations.local_target(binding), evidence=evidence, reason=reason,
                      backup=dict(frequency="daily", retention_days=30, restore_verified=True)))


def _assess(control, target, binding, now, *, config, exclude_operation_id=None):
    issues, prerequisites, recovery = [], sorted(REHEARSAL_CHECKS), []
    state = _state(control, binding)
    activated = state["state"] == "ACTIVATED" and state.get("scope") == "trusted-local-production"
    if activated:
        require_activated(control, binding)
    execution_schema.check_schema(target)
    approvals.schema.check(control)
    auth._owner(control, target, binding, now)
    auth._cipher(config)  # Existing protected host key; never generated or returned.
    mfa = control.execute("SELECT state,seed_ciphertext FROM recognition_admin_mfa WHERE actor=?", (binding["owner_id"],)).fetchone()
    if not mfa or mfa[0] != "ENROLLED" or not mfa[1]:
        issues.append("owner_mfa_not_enrolled")
    stop = journal._stop(control)
    if not stop["sequence"]:
        issues.append("emergency_stop_state_missing")
    if stop["active"]:
        issues.append("emergency_stop_active")
    if state["state"] == "RECOVERY_REQUIRED":
        issues.append("installation_"+state["state"].lower())
    a.need(callable(permanent.finalize) and callable(writer_boundary.acquire) and callable(local_execution.reconcile_operation), "writer_or_recovery_implementation_missing")
    claimed_ids = {row[0] for row in target.execute("SELECT operation_id FROM recognition_execution_claims")}
    for oid in claimed_ids:
        if oid == exclude_operation_id:
            continue
        approved = control.execute("SELECT approval_id FROM recognition_approvals WHERE operation_id=?", (oid,)).fetchone()
        if not approved:
            recovery.append(oid)
            continue
        value = approvals._read(control, approved[0])
        try:
            result = local_execution._existing(target, oid, value)
            if not result or result.state not in {"COMPLETED", "FAILED_BEFORE_COMMIT"}:
                recovery.append(oid)
        except (ValueError, KeyError, TypeError):
            recovery.append(oid)
    pending = []
    for row in target.execute("SELECT operation_id FROM recognition_operation_contracts ORDER BY operation_id"):
        if row[0] in claimed_ids:
            continue
        approval = control.execute("SELECT approval_id FROM recognition_approvals WHERE operation_id=?", (row[0],)).fetchone()
        if approval and approvals._read(control, approval[0])["state"] != "APPROVED":
            continue  # Historical invalidated approvals are not pending work.
        op = operations.get_operation(target, row[0])
        e = op["envelope"]
        if op["decisions"][-1]["state"] == "PREPARED":
            from . import dependencies
            dependency = dependencies.recheck(target, e["event_id"])
            pending.append(dict(operation_sha256=digest(e), decisions=op["decisions"], executions=op["executions"], dependency=dependency,
                                approval=approvals._read(control, approval[0]) if approval else None))
            if dependency["state"] != "READY":
                issues.append("pending_operation_dependencies_not_ready:"+row[0])
            if approval and dependency["state"] == "READY":
                value = approvals._read(control, approval[0])
                try:
                    a.need(approvals._snapshot(target, row[0], binding) == value["approval"]["binding"], "pending_approval_binding_changed")
                except (a.AdminError, Quarantined):
                    issues.append("pending_approval_binding_changed:"+row[0])
            if e["format"] != operations.LOCAL_CONTRACT:
                issues.append("incompatible_pending_operation:"+row[0])
            elif e["local_target"] != production_operations.local_target(binding):
                issues.append("pending_operation_generation_mismatch:"+row[0])
    observation = control.execute("SELECT body_json FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')='local_deployment_rehearsal_recorded' ORDER BY sequence DESC LIMIT 1").fetchone()
    if observation:
        from .trust import load
        record = load(observation[0])
        if record["subject"]["target"] == production_operations.local_target(binding) and 0 <= a.timestamp(now)-a.timestamp(record["at_utc"]) < 86400:
            prerequisites = []
    status = "RECOVERY_REQUIRED" if recovery else "BLOCKED" if issues else "READY_FOR_DEPLOYMENT" if prerequisites else "READY_FOR_ACTIVATION"
    return dict(format="recognition-local-readiness-v1", status=status, target=production_operations.local_target(binding),
        activation_state=state["state"], issues=sorted(set(issues)), unresolved_recovery=sorted(recovery), deployment_prerequisites=prerequisites,
        code_ready=not issues and not recovery, deployment_verified=not prerequisites and not local_execution._fixture_target(target),
        rehearsal_evidence_present=not prerequisites, activation_ready=not issues and not recovery and not prerequisites,
        admission_state_sha256=digest(dict(pending=pending, stop=stop, deployment_observation=record if observation else None)),
        deployment_status="REHEARSAL_REQUIRED" if prerequisites else "DISPOSABLE_REHEARSAL_ONLY" if local_execution._fixture_target(target) else "DEPLOYMENT_OBSERVATIONS_VERIFIED",
        production_authorization="PER_OPERATION_APPROVAL_REQUIRED" if activated else "BLOCKED",
        production_execution="FINAL_ADMISSION_REQUIRED" if activated and not issues and not recovery and not prerequisites else "BLOCKED",
        production_activation="ACTIVATED" if activated else "BLOCKED",
        backup_requirement=dict(frequency="daily", retention_days=30, verified_restore_required=True),
        assessment_at_utc=now, scope="disposable-contract-assessment" if local_execution._fixture_target(target) else "local-deployment-observation-not-authority")


def _blocked(issue):
    return dict(status="BLOCKED", issues=[issue], code_ready=False, deployment_verified=False, activation_ready=False,
                production_authorization="BLOCKED", production_execution="BLOCKED", production_activation="BLOCKED")


def assess(config, *, now, selected_provider=None):
    # Provider selection is rejected, not adapted or substituted. It is never a
    # Flask request/configuration option and cannot grant authority.
    if selected_provider is not None:
        return _blocked("external_or_test_provider_not_permitted")
    try:
        with a.transaction(config, lock_target=True) as (control, target, binding):
            return _assess(control, target, binding, now, config=config)
    except (a.AdminError, Quarantined) as error:
        return _blocked(str(error))
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError):
        return _blocked("installation_schema_identity_or_administration_unavailable")


def _assessment_binding(readiness):
    # The clock controls freshness but is not itself the reviewed subject.
    return {key: value for key, value in readiness.items() if key != "assessment_at_utc"}


def _ceremony(binding, old, readiness):
    return digest(dict(action="activate", target=production_operations.local_target(binding),
                       current_state=old, readiness=_assessment_binding(readiness)))


def begin_activation_confirmation(config, session_token, step_token, *, now):
    """One-use activation DATA in the existing confirmation store; no activation."""
    with a.transaction(config, lock_target=True) as (control, target, binding):
        now = local_execution._utc_now()
        session, _ = auth._session(control, target, binding, session_token, now)
        step = auth._step(control, target, binding, session, step_token, "activate", None, now)
        readiness = _assess(control, target, binding, now, config=config)
        old = _state(control, binding)
        a.need(readiness["activation_ready"] and "ACTIVATED" in TRANSITIONS[old["state"]], "activation_not_ready")
        raw = secrets.token_urlsafe(32)
        control.execute("INSERT INTO recognition_admin_confirmations VALUES(?,?,?,?,?,?,?,?,0)",
            (a.token_hash(raw), session["token_hash"], session["actor"], "activation:"+binding["installation_id"],
             digest(production_operations.local_target(binding)), _ceremony(binding, old, readiness), binding["generation"], step["expires"]))
        a._audit(control, "activation_confirmation_begun", session["actor"], now,
                 dict(confirmation_sha256=a.token_hash(raw), readiness_sha256=digest(_assessment_binding(readiness))))
        return dict(confirmation_token=raw, readiness=readiness)


def require_activated(control, binding):
    """A state name/boolean alone is never production authority."""
    state = _state(control, binding)
    a.need(state["state"] == "ACTIVATED" and state.get("scope") == "trusted-local-production",
           "production_activation_deployment_blocked", 503)
    row = control.execute("SELECT * FROM recognition_admin_confirmations WHERE token_hash=?", (state.get("confirmation_sha256"),)).fetchone()
    a.need(row is not None and row["used"] == 1 and row["actor"] == state["actor_id"] == binding["owner_id"]
           and row["generation"] == binding["generation"] and row["operation_id"] == "activation:"+binding["installation_id"]
           and row["operation_sha256"] == digest(production_operations.local_target(binding))
           and row["state_sha256"] == state.get("ceremony_sha256"), "production_activation_ceremony_required")
    return state


def change_state(config, session_token, step_token, *, state, reason, now, confirmation_token=None):
    return _transition(config, session_token, step_token, state=state, reason=reason, now=now, confirmation_token=confirmation_token)


def _transition(config_or_fixture, session_token, step_token, *, state, reason, now, confirmation_token=None):
    fixture = local_execution._production_fixture(config_or_fixture)
    config = local_execution._context(config_or_fixture)["config"] if fixture else config_or_fixture
    a.need(type(state) is str and state in {"ACTIVATED", "SUSPENDED", "DEACTIVATED"} and type(reason) is str and 1 <= len(reason.strip()) <= 2000, "explicit_activation_action_required", 400)
    with a.transaction(config, lock_target=True) as (control, target, binding):
        if not fixture and state == "ACTIVATED" and confirmation_token is not None:
            now = local_execution._utc_now()
        session, _ = auth._session(control, target, binding, session_token, now)
        action = {"ACTIVATED": "activate", "SUSPENDED": "suspend", "DEACTIVATED": "deactivate"}[state]
        step = auth._step(control, target, binding, session, step_token, action, None, now)
        old = _state(control, binding)
        readiness = _assess(control, target, binding, now, config=config)
        a.need(state in TRANSITIONS[old["state"]], "invalid_local_activation_transition")
        confirmation = None
        if state == "ACTIVATED":
            a.need(readiness["activation_ready"], "local_activation_readiness_not_satisfied")
            if not fixture:
                if confirmation_token is None:
                    a._audit(control, "production_activation_attempt_blocked", session["actor"], now, dict(reason="activation_confirmation_required"))
                    return dict(state=old["state"], result="BLOCKED", reason="activation_confirmation_required")
                confirmation = control.execute("SELECT * FROM recognition_admin_confirmations WHERE token_hash=?", (a.token_hash(confirmation_token),)).fetchone()
                a.need(confirmation is not None and not confirmation["used"]
                       and confirmation["session_hash"] == session["token_hash"] and confirmation["actor"] == session["actor"]
                       and confirmation["operation_id"] == "activation:"+binding["installation_id"]
                       and confirmation["operation_sha256"] == digest(production_operations.local_target(binding))
                       and confirmation["state_sha256"] == _ceremony(binding, old, readiness)
                       and confirmation["generation"] == binding["generation"]
                       and a.timestamp(now) < confirmation["expires"] <= step["expires"], "invalid_or_stale_activation_confirmation")
                changed = control.execute("UPDATE recognition_admin_confirmations SET used=1 WHERE token_hash=? AND used=0", (confirmation["token_hash"],))
                a.need(changed.rowcount == 1, "activation_confirmation_conflict", 409)
        a.need(state != old["state"], "activation_state_unchanged")
        return _append(control, binding, state, session["actor"], reason, now, readiness=_assessment_binding(readiness), confirmation=confirmation,
                       scope="disposable-production-contract-fixture" if fixture else "trusted-local-production")
