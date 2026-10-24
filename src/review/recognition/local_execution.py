"""Local approval -> fixed historical writer bridge, production provisioning OFF.

Only newly created, registered disposable workspaces can exercise mutation.
No authority/status/enrollment/activation provider is accepted by this module.
"""

from dataclasses import asdict
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
from uuid import uuid4
from weakref import WeakKeyDictionary

from . import RecognitionGate, administration as a, admin_auth as auth, approvals
from . import execution as journal, execution_schema, operations, events, permanent, permanent_schema, writer_boundary
from .qualification import Quarantined
from .authorization import target_identity
from .rules import canonical, digest
from .trust import load


POLICY = {"reference": "atomic-historical-v1", "quarantine_categories": [], "other_categories": []}
SUPPORTED = frozenset(("first_look", "geography_steward"))
_contexts = WeakKeyDictionary()
Result = journal.ExecutionResult


class DisposableExecutionContext:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise TypeError("fresh_disposable_workspace_required")


class DisposableExecutionWorkspace:
    """Owns fresh files; cannot register an arbitrary existing target as a test."""

    def __init__(self):
        self._temp = tempfile.TemporaryDirectory(prefix="recognition-local-execution-")
        self.directory = Path(self._temp.name).resolve()
        self.target = self.directory / "target.sqlite"
        self.control = self.directory / "control.sqlite"
        for path in (self.target, self.control):
            with closing(sqlite3.connect(path)):
                pass
        self._context = None

    def cleanup(self):
        if self._context is not None:
            _contexts.pop(self._context, None)
        self._temp.cleanup()

    def install_target_storage(self):
        """Explicit disposable-only DDL, before Slice A pins the target schema."""
        with a.connect(self.target, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            operations.operation_schema.check_schema(conn)
            conn.execute("SAVEPOINT install_local_execution")
            try:
                for name, sql in {**permanent_schema.definitions(), **execution_schema.definitions()}.items():
                    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone():
                        conn.execute(sql)
                execution_schema.check_schema(conn)
                a.need(not conn.execute("PRAGMA foreign_key_check").fetchone(), "execution_foreign_key_failure")
            except BaseException:
                conn.execute("ROLLBACK TO install_local_execution")
                raise
            finally:
                conn.execute("RELEASE install_local_execution")
            conn.commit()

    def bind(self, config):
        a.need(self._context is None and config.target == self.target and config.control == self.control
               and config.key_file.parent.resolve() == self.directory, "fresh_disposable_workspace_required")
        binding = a.get_installation_control(config)
        with a.connect(config.target) as conn:
            execution_schema.check_schema(conn)
        context = object.__new__(DisposableExecutionContext)
        _contexts[context] = dict(config=config, workspace=self, installation_id=binding["installation_id"],
                                 control_identity=binding["control_identity"])
        self._context = context
        return context

    def set_readiness(self, *, permitted, now):
        """Durable disposable simulation ONLY; never changes production activation."""
        data = _context(self._context)
        a.need(type(permitted) is bool, "invalid_disposable_readiness")
        with a.transaction(data["config"], lock_target=True) as (conn, _, binding):
            a._audit(conn, "disposable_execution_readiness", "disposable-host", now,
                     dict(permitted=permitted, generation=binding["generation"], target_id=binding["target_id"]))

    def set_stop(self, *, active, now):
        data = _context(self._context)
        a.need(type(active) is bool, "invalid_stop")
        with a.transaction(data["config"]) as (conn, _, _binding):
            old = journal._stop(conn)
            body = dict(sequence=old["sequence"]+1, active=active, reason="disposable-stop-test", actor="disposable-host",
                        recorded_at_utc=now, previous_sha256=digest(old) if old["sequence"] else None)
            events._insert(conn, "recognition_execution_stops", "sequence", (body["sequence"],), body)
            a._audit(conn, "disposable_stop_changed", "disposable-host", now, body)


class DisposableProductionExecutionWorkspace(DisposableExecutionWorkspace):
    """Explicit fresh synthetic fixture for production-format writer contracts.

    Cannot adopt an existing database or be selected through HTTP/configuration.
    It NEVER provisions a real ProductionOperationContext.
    """

    def simulate_activation(self, session_token, step_token, *, reason, now):
        from . import local_readiness
        return local_readiness._transition(self._context, session_token, step_token,
            state="ACTIVATED", reason=reason, now=now)


def _production_fixture(context):
    return (type(context) is DisposableExecutionContext and context in _contexts
            and type(_contexts[context]["workspace"]) is DisposableProductionExecutionWorkspace)


def _fixture_target(database):
    path = target_identity(database).database
    return any(_production_fixture(context) and str(data["config"].target) == path for context, data in list(_contexts.items()))


def _context(context):
    from . import production_operations
    if type(context) is production_operations.ProductionOperationContext:
        return production_operations.context_data(context)
    a.need(type(context) is DisposableExecutionContext and context in _contexts, "production_execution_unavailable", 503)
    data = _contexts[context]
    config, workspace = data["config"], data["workspace"]
    a.need(workspace._context is context and workspace.directory.is_dir(), "disposable_context_expired", 503)
    for path in (config.target, config.control, config.key_file):
        a.need(not path.is_symlink() and path.resolve().parent == workspace.directory, "disposable_path_escape", 503)
    return data


def _fault(point):
    """Deterministic test seam, never a request/env callback."""


def _read(conn, table, operation_id):
    row = conn.execute(f"SELECT body_json,body_sha256 FROM {table} WHERE operation_id=?", (operation_id,)).fetchone()
    return events._read(row) if row else None


def _enabled(control, binding):
    row = control.execute("SELECT body_json FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')='disposable_execution_readiness' ORDER BY sequence DESC LIMIT 1").fetchone()
    if not row:
        return False
    state = load(row[0])["subject"]
    return state == dict(permitted=True, generation=binding["generation"], target_id=binding["target_id"])


def _verify(control, target, binding, session_token, approval_id, now, *, context=None):
    from . import production_operations
    approvals.schema.check(control)
    execution_schema.check_schema(target)
    session, _ = production_operations.actor_session(control, target, binding, session_token, now)
    value = approvals._read(control, approval_id)
    a.need(value["state"] == "APPROVED" and value["approval"]["actor_id"] == session["actor"] == binding["owner_id"], "approval_not_effective")
    expected = value["approval"]["binding"]
    snapshot = approvals._snapshot(target, expected["operation_id"], binding)
    a.need(snapshot == expected, "approved_operation_changed")
    op = operations.get_operation(target, expected["operation_id"])
    e = op["envelope"]
    a.need(e["family"] in SUPPORTED and e["action"] == "finalize", "UNSUPPORTED_OPERATION")
    a.need(e["accounting_policy"] == POLICY, "unsupported_accounting_or_quarantine")
    p = events.get_event(target, e["event_id"])["preparation"]
    manifest = p["manifest"]
    a.need(manifest["format"] == "private-recognition-operation-v1" and permanent.DEFINITIONS.get(e["family"]) == manifest["rule"], "unsupported_writer_policy")
    a.need(a.timestamp(now) >= a.timestamp(e["created_at_utc"]), "execution_clock_before_operation")
    a.need(not journal._stop(control)["active"], "emergency_stop")
    if e["format"] == operations.LOCAL_CONTRACT:
        if not _production_fixture(context):
            production_operations.activation_guard()
        from . import local_readiness
        a.need(local_readiness._state(control, binding)["state"] == "ACTIVATED", "activation_not_permitted")
        a.need(local_readiness._assess(control, target, binding, now, config=_context(context)["config"], exclude_operation_id=e["operation_id"])["activation_ready"], "local_execution_readiness_not_satisfied")
    a.need(_enabled(control, binding), "activation_not_permitted")
    # Same whole-population regeneration as the actual writer, under its lock.
    fresh = permanent._prepare(target, e["family"], manifest["inputs"], manifest["evaluation_at_utc"], manifest["authorization_reference"])
    a.need(fresh == manifest, "writer_preconditions_changed")
    return value, op, manifest


def verify_approved_operation(context, session_token, approval_id, *, now):
    """Read-only preview, never an execution capability or cached admission."""
    try:
        data = _context(context)
        with a.transaction(data["config"], lock_target=True) as (control, target, binding):
            from . import production_operations
            production_operations.bind_approval(data, approvals._read(control, approval_id), binding)
            _verify(control, target, binding, session_token, approval_id, now, context=context)
        return Result("VERIFIED", "NOT_STARTED", "preview_only_final_recheck_required")
    except (a.AdminError, Quarantined) as error:
        if str(error) == "projection_conflicts_with_evidence":
            return Result("RECONCILIATION_REQUIRED", "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED", str(error))
        if str(error) == "production_execution_unavailable":
            return Result("BLOCKED", "NOT_STARTED", str(error))
        return Result("WAITING_FOR_VERIFICATION" if getattr(error, "status", 403) == 503 else "BLOCKED", "NOT_STARTED", str(error))
    except (sqlite3.Error, OSError):
        return Result("WAITING_FOR_VERIFICATION", "WAITING", "verification_infrastructure_unavailable")


def _receipt(conn, claim, manifest, result, now):
    if claim.get("execution_scope") == "disposable-production-contract-fixture":
        from .production_receipts import build
        return build(conn, claim, manifest, result, now)
    e = claim["operation"]
    permanent._verify_operation_records(conn, e["writer_manifest_sha256"])
    a.need(result == dict(issued=True, operation_id=e["writer_manifest_sha256"], records=len(e["member_ids"])), "actual_writer_result_mismatch")
    return dict(format="recognition-local-execution-receipt-v1", execution_mode="disposable-local-bridge", operation_id=e["operation_id"],
        operation_sha256=digest(e), approval_id=claim["approval_id"], approval_sha256=claim["approval_sha256"],
        actor_id=claim["actor_id"], installation_id=claim["binding"]["installation_id"], target_id=claim["binding"]["target_id"],
        target_observation=claim["binding"]["target_observation"], restore_generation=claim["binding"]["restore_generation"],
        claim_sha256=digest(claim), writer_family=e["family"], writer_result=result, authorized_count=len(e["member_ids"]),
        successful=[dict(member_id=m, outcome_reference=e["writer_manifest_sha256"]+":"+m) for m in e["member_ids"]],
        quarantined=[], other=[], started_at_utc=claim["claimed_at_utc"], finished_at_utc=now,
        writer_evidence_sha256=journal._writer_evidence(conn, digest(manifest)))


def _seal(conn, operation_id, value):
    claim = _read(conn, "recognition_execution_claims", operation_id)
    if claim and claim.get("execution_scope") == "disposable-production-contract-fixture":
        from .production_receipts import evidence
        return evidence(conn, operation_id, value)
    seal = _read(conn, "recognition_execution_seals", operation_id)
    if not seal:
        return None
    a.need(claim and claim["format"] == "recognition-local-execution-claim-v1" and claim["operation"]["operation_id"] == operation_id
           and claim["approval_id"] == value["approval"]["approval_id"] and claim["approval_sha256"] == value["approval_sha256"]
           and claim["binding"] == value["approval"]["binding"] and digest(claim["operation"]) == claim["binding"]["operation_sha256"]
           and seal["claim_sha256"] == digest(claim) and seal["writer_sha256"] == claim["writer_sha256"], "execution_claim_or_seal_mismatch")
    op = operations.get_operation(conn, operation_id)
    a.need(op["envelope"] == claim["operation"], "sealed_operation_changed")
    manifest = events.get_event(conn, op["envelope"]["event_id"])["preparation"]["manifest"]
    receipt = seal["receipt"]
    expected = _receipt(conn, claim, manifest, dict(issued=True, operation_id=digest(manifest), records=len(op["envelope"]["member_ids"])), receipt["finished_at_utc"])
    a.need(receipt == expected and a.timestamp(receipt["finished_at_utc"]) >= a.timestamp(receipt["started_at_utc"]), "execution_receipt_evidence_mismatch")
    indexed = conn.execute("SELECT writer_sha256 FROM recognition_execution_seals WHERE operation_id=?", (operation_id,)).fetchone()[0]
    a.need(indexed == digest(manifest) == seal["writer_sha256"] and seal["evidence_sha256"] == receipt["writer_evidence_sha256"], "execution_writer_evidence_mismatch")
    a.need(claim["writer_sha256"] == op["envelope"]["writer_manifest_sha256"] == digest(manifest)
           and claim["actor_id"] == value["approval"]["actor_id"]
           and claim["operation_id"] == operation_id, "execution_claim_subject_mismatch")
    return seal


def _existing(conn, operation_id, value):
    history = journal._audit(conn, operation_id)
    claim = _read(conn, "recognition_execution_claims", operation_id)
    if not history and not claim:
        return None
    if history and history[-1]["state"] == "FAILED_BEFORE_COMMIT":
        return Result("BLOCKED", "FAILED_BEFORE_COMMIT", "terminal_failure_new_operation_required")
    seal = _seal(conn, operation_id, value)
    if seal and claim.get("execution_scope") == "disposable-production-contract-fixture":
        from .production_receipts import projection_status
        status = projection_status(conn, operation_id, seal)
        if status == "CONFLICT":
            return Result("RECONCILIATION_REQUIRED", "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED", "projection_conflicts_with_evidence")
        if status != "CURRENT":
            return Result("RECOVERY_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED", "projection_missing_never_retry_writer")
    if seal and history and history[-1]["state"] == "COMPLETED":
        return Result("ALREADY_EXECUTED", "COMPLETED", "durable_writer_evidence_verified", digest(seal["receipt"]))
    if claim:
        return Result("RECOVERY_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED", "unfinished_claim_never_retry_writer")
    if history and history[-1]["state"] == "WAITING":
        return None
    return Result("RECOVERY_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED", "execution_history_conflict")


def _commit_target(conn):
    conn.commit()


def execute_approved_operation(context, session_token, approval_id, *, now):
    """Final verification automatically invokes the fixed writer; no Execute UI."""
    try:
        data = _context(context)
        from . import production_operations
        if type(context) is production_operations.ProductionOperationContext:
            production_operations.consume_context(context)
    except a.AdminError as error:
        return Result("BLOCKED", "NOT_STARTED", str(error))
    config = data["config"]
    claimed = False
    try:
        with a.connect(config.control, write=True) as control, a.connect(config.target, write=True) as target:
            control.execute("BEGIN IMMEDIATE")
            approvals.schema.check(control)
            a._audit_head(control)
            binding = a._binding(control)
            a.need(binding["control_identity"] == data["control_identity"] == asdict(target_identity(config.control))
                   and binding["installation_id"] == data["installation_id"], "control_identity_changed")
            target.execute("BEGIN IMMEDIATE")
            a._verify(config, control, target, binding)
            production_operations.actor_session(control, target, binding, session_token, now)
            value = approvals._read(control, approval_id)
            production_operations.bind_approval(data, value, binding)
            oid = value["approval"]["binding"]["operation_id"]
            execution_schema.check_schema(target)
            claimed = bool(target.execute("SELECT 1 FROM recognition_execution_claims WHERE operation_id=?", (oid,)).fetchone())
            existing = _existing(target, oid, value)
            if existing:
                return existing
            _fault("A")
            try:
                value, op, manifest = _verify(control, target, binding, session_token, approval_id, now, context=context)
            except (a.AdminError, Quarantined) as error:
                temporary = getattr(error, "status", 403) == 503
                journal._append(target, oid, "WAITING" if temporary else "FAILED_BEFORE_COMMIT", str(error), now, "ADMISSION")
                target.commit()
                return Result("WAITING_FOR_VERIFICATION" if temporary else "BLOCKED", "WAITING" if temporary else "FAILED_BEFORE_COMMIT", str(error))
            _fault("B")
            e = op["envelope"]
            claim = dict(format="recognition-local-execution-claim-v1", claim_id=str(uuid4()), operation=e,
                operation_id=oid, writer_sha256=digest(manifest), binding=value["approval"]["binding"],
                approval_id=approval_id, approval_sha256=value["approval_sha256"], actor_id=value["approval"]["actor_id"], claimed_at_utc=now)
            if e["format"] == operations.LOCAL_CONTRACT:
                a.need(_production_fixture(context), "production_writer_provisioning_unavailable")
                claim.update(execution_scope="disposable-production-contract-fixture", approval_reason=value["approval"]["reason"])
            events._insert(target, "recognition_execution_claims", "operation_id", (oid,), claim)
            journal._append(target, oid, "EXECUTING", "local_approval_finally_verified", now, "ADMISSION")
            claimed = True  # Commit errors are uncertain, never safe retry instructions.
            _commit_target(target)
            _fault("C")
            target.execute("BEGIN IMMEDIATE")
            a._verify(config, control, target, binding)
            # A separate target transaction means ordinary target writers could
            # run after claim commit. Recheck immediately before minting a lease.
            _verify(control, target, binding, session_token, approval_id, now, context=context)
            a.need(journal._audit(target, oid)[-1]["state"] == "EXECUTING", "execution_claim_fenced")
            # One-use registry admission is produced only at this protected
            # final-check boundary, not by possession of a context/claim alone.
            data["writer_admission"] = (target, digest(manifest), digest(claim))
            with writer_boundary._local_lease(context, target, manifest, claim) as capability:
                result = permanent.finalize(config.target, manifest, manifest_sha256=digest(manifest),
                    authorization_reference=manifest["authorization_reference"], gate=RecognitionGate(issuance=True),
                    execution_context=capability)
            _fault("D")
            receipt = _receipt(target, claim, manifest, result, now)
            seal = dict(writer_sha256=digest(manifest), claim_sha256=digest(claim), receipt=receipt,
                        evidence_sha256=receipt["writer_evidence_sha256"])
            events._insert(target, "recognition_execution_seals", "operation_id,writer_sha256", (oid, digest(manifest)), seal)
            _commit_target(target)  # ALL writer effects + seal in ONE target commit.
            _fault("E")
            target.execute("BEGIN IMMEDIATE")
            a.need(_seal(target, oid, value) is not None, "committed_writer_evidence_missing")
            if claim.get("execution_scope") == "disposable-production-contract-fixture":
                from .production_receipts import project
                project(target, oid, value, now=now, kind="EXECUTION")
            else:
                journal._append(target, oid, "COMPLETED", "local_writer_seal_verified", now)
            _commit_target(target)
            _fault("F")
            control.commit()  # No target/control atomicity is claimed or needed.
        _fault("G")
        return Result("ADMITTED", "COMPLETED", "local_writer_committed", digest(receipt))
    except (a.AdminError, Quarantined) as error:
        if str(error) == "projection_conflicts_with_evidence":
            return Result("RECONCILIATION_REQUIRED", "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED", str(error))
        return Result("RECOVERY_REQUIRED" if claimed else "BLOCKED",
                      "UNKNOWN_RECOVERY_REQUIRED" if claimed else "NOT_STARTED", str(error))
    except (sqlite3.Error, OSError):
        # A claimed execution is fenced even if we cannot record the uncertainty.
        return Result("RECOVERY_REQUIRED" if claimed else "WAITING_FOR_VERIFICATION",
                      "UNKNOWN_RECOVERY_REQUIRED" if claimed else "WAITING", "execution_outcome_uncertain" if claimed else "verification_unavailable")
    except Exception:
        return Result("RECOVERY_REQUIRED" if claimed else "BLOCKED",
                      "UNKNOWN_RECOVERY_REQUIRED" if claimed else "NOT_STARTED", "execution_evidence_unverifiable")


def approve_and_execute(config, session_token, step_token, confirmation_token, *, operation_id, reason, now, context=None):
    if context is not None:
        a.need(_context(context)["config"] == config, "execution_context_target_mismatch")
    value = approvals.create_approval(config, session_token, step_token, confirmation_token,
        operation_id=operation_id, reason=reason, now=now)
    if context is None and value["approval"]["binding"]["operation_contract_format"] == operations.LOCAL_CONTRACT:
        from .production_operations import load_context
        context = load_context(config, operation_id)
    result = execute_approved_operation(context, session_token, value["approval"]["approval_id"], now=now)
    return dict(value, execution_pending=result.state != "COMPLETED", execution=asdict(result))


def reconcile_operation(context, session_token, step_token, approval_id, *, now):
    """Owner-only inspection/fencing; NEVER invokes a writer or grants a retry."""
    try:
        data = _context(context)
        with a.transaction(data["config"], lock_target=True) as (control, target, binding):
            session, _ = auth._session(control, target, binding, session_token, now)
            value = approvals._read(control, approval_id)
            oid = value["approval"]["binding"]["operation_id"]
            auth._step(control, target, binding, session, step_token, "recover", oid, now)
            execution_schema.check_schema(target)
            claim = _read(target, "recognition_execution_claims", oid)
            if not claim:
                return Result("BLOCKED", "NOT_STARTED", "no_execution_claim")
            a.need(claim["format"] == "recognition-local-execution-claim-v1"
                   and claim["approval_id"] == approval_id and claim["approval_sha256"] == value["approval_sha256"]
                   and claim["binding"] == value["approval"]["binding"]
                   and claim["binding"]["restore_generation"] == binding["generation"]
                   and claim["binding"]["target_id"] == binding["target_id"], "recovery_claim_binding_mismatch")
            seal = _seal(target, oid, value)
            history = journal._audit(target, oid)
            if seal:
                if claim.get("execution_scope") == "disposable-production-contract-fixture":
                    from .production_receipts import project
                    project(target, oid, value, now=now)
                    target.commit()
                    return Result("ALREADY_EXECUTED", "COMPLETED", "production_contract_projection_reconciled", digest(seal["receipt"]))
                if history[-1]["state"] != "COMPLETED":
                    journal._append(target, oid, "COMPLETED", "reconciled_local_writer_seal", now, "RECOVERY")
                    target.commit()
                return Result("ALREADY_EXECUTED", "COMPLETED", "durable_local_writer_verified", digest(seal["receipt"]))
            if history and history[-1]["state"] == "FAILED_BEFORE_COMMIT":
                return Result("BLOCKED", "FAILED_BEFORE_COMMIT", "previously_fenced")
            writer_id = claim["writer_sha256"]
            residue = any(target.execute(f"SELECT 1 FROM {table} WHERE operation_id=? LIMIT 1", (writer_id,)).fetchone()
                for table in ("recognition_private_operations", "recognition_first_look_claims", "recognition_geography_snapshots", "recognition_geography_awards"))
            state = "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED" if residue or target.execute("PRAGMA foreign_key_check").fetchone() else "FAILED_BEFORE_COMMIT"
            journal._append(target, oid, state, "outcomes_without_seal" if residue else "no_committed_writer_effects", now, "RECOVERY")
            target.commit()  # Target fence commits before releasing writer lock.
            return Result("RECOVERY_REQUIRED" if state != "FAILED_BEFORE_COMMIT" else "BLOCKED", state, "manual_reconciliation_required" if residue else "no_effects_new_operation_required")
    except (a.AdminError, Quarantined, sqlite3.Error, OSError, KeyError, TypeError, ValueError) as error:
        if str(error) == "projection_conflicts_with_evidence":
            return Result("RECONCILIATION_REQUIRED", "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED", str(error))
        return Result("RECOVERY_REQUIRED", "UNKNOWN_RECOVERY_REQUIRED", "recovery_evidence_unavailable")
