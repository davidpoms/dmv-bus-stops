"""Local production-format persistence and restartable admission descriptors.

No production writer provisioning or activation is enabled here. The only
coordinator is Slice C; descriptors are not executable writer capabilities.
"""

from dataclasses import asdict
from uuid import UUID, uuid4
from weakref import WeakKeyDictionary

from . import administration as a, admin_auth as auth, events, dependencies, operations
from . import event_schema, operation_schema, permanent_schema, execution_schema
from .rules import canonical, digest


FAMILIES = frozenset(("first_look", "geography_steward"))
REQUEST_FIELDS = {"request_id", "family", "inputs", "evaluation_at_utc", "review_reference", "parent_operation_id"}
_contexts = WeakKeyDictionary()
_sessions = WeakKeyDictionary()


def local_target(binding):
    return dict(format="recognition-local-operation-target-v1", installation_id=binding["installation_id"],
                target_id=binding["target_id"], restore_generation=binding["generation"], target=binding["target"])


def validate_local_target(value):
    a.need(type(value) is dict and set(value) == {"format", "installation_id", "target_id", "restore_generation", "target"}
           and value["format"] == "recognition-local-operation-target-v1"
           and type(value["restore_generation"]) is int and value["restore_generation"] > 0, "invalid_local_operation_target")
    for key in ("installation_id", "target_id"):
        a.need(type(value[key]) is str and str(UUID(value[key])) == value[key], "invalid_local_operation_identity")
    target = value["target"]
    a.need(set(target) == {"observation", "schema_sha256"} and operations._sha(target["schema_sha256"])
           and set(target["observation"]) == {"hostname", "database", "device", "inode"}, "invalid_local_target_observation")


def install_target(conn):
    """Explicit trusted-deployment DDL; caller owns transaction, no startup path."""
    a.need(conn.in_transaction and conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1, "operation_migration_transaction_required")
    from .schema import TABLES as explorer_tables
    for name, body in explorer_tables.items():
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()
        a.need(row is not None and " ".join(row[0].split()) == " ".join(f"CREATE TABLE {name} ({body})".split()), "existing_explorer_schema_required")
    conn.execute("SAVEPOINT install_production_operations")
    try:
        for name, sql in {**event_schema.definitions(), **operation_schema.definitions(),
                          **permanent_schema.definitions(), **execution_schema.definitions()}.items():
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone():
                conn.execute(sql)
        execution_schema.check_schema(conn)
        a.need(not conn.execute("PRAGMA foreign_key_check").fetchone(), "operation_migration_foreign_key_failure")
    except BaseException:
        conn.execute("ROLLBACK TO install_production_operations")
        raise
    finally:
        conn.execute("RELEASE install_production_operations")


def _request(value):
    a.need(type(value) is dict and set(value) == REQUEST_FIELDS, "invalid_operation_creation_request", 400)
    a.need(type(value["family"]) is str and value["family"] in FAMILIES, "UNSUPPORTED_OPERATION", 400)
    a.need(type(value["inputs"]) is dict and type(value["review_reference"]) is str
           and 1 <= len(value["review_reference"].strip()) <= 2000, "invalid_operation_inputs", 400)
    try:
        valid_id = type(value["request_id"]) is str and str(UUID(value["request_id"])) == value["request_id"]
    except ValueError:
        valid_id = False
    a.need(valid_id, "invalid_creation_request_id", 400)
    a.timestamp(value["evaluation_at_utc"])
    a.need(value["parent_operation_id"] is None or type(value["parent_operation_id"]) is str, "invalid_parent_operation", 400)
    try:
        return operations._copy(value)
    except (TypeError, ValueError):
        raise a.AdminError("invalid_operation_creation_data", 400) from None


def _creation_audit(control, body, actor, now):
    old = control.execute("SELECT 1 FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')='production_operation_created' AND json_extract(body_json,'$.subject.operation_id')=?", (body["operation_id"],)).fetchone()
    if not old:
        a._audit(control, "production_operation_created", actor, now,
                 dict(operation_id=body["operation_id"], operation_sha256=digest(body), request_id=body["creation"]["request_id"]))


def create_operation(config, session_token, request, *, now):
    request = _request(request)
    with a.transaction(config, lock_target=True) as (control, target, binding):
        session, _ = auth._session(control, target, binding, session_token, now)
        execution_schema.check_schema(target)
        rows = target.execute("SELECT operation_id FROM recognition_operation_contracts WHERE json_extract(body_json,'$.format')=? AND json_extract(body_json,'$.creation.request_id')=?",
                              (operations.LOCAL_CONTRACT, request["request_id"])).fetchall()
        a.need(len(rows) <= 1, "duplicate_creation_request", 409)
        if rows:
            old = operations.get_operation(target, rows[0][0])
            a.need(old["envelope"]["creation"] == dict(request_id=request["request_id"], request_sha256=digest(request), actor_id=session["actor"])
                   and old["envelope"]["local_target"] == local_target(binding), "operation_creation_replay_conflict", 409)
            _creation_audit(control, old["envelope"], session["actor"], now)
            return old
        parent = None
        if request["parent_operation_id"]:
            parent = operations.get_operation(target, request["parent_operation_id"])
            a.need(parent["envelope"]["format"] == operations.LOCAL_CONTRACT
                   and parent["envelope"]["family"] == request["family"]
                   and parent["envelope"]["local_target"] == local_target(binding), "invalid_revision_parent")
            a.need(parent["decisions"][-1]["state"] == "PREPARED"
                   and not target.execute("SELECT 1 FROM recognition_execution_claims WHERE operation_id=?", (request["parent_operation_id"],)).fetchone(), "revision_parent_already_claimed_or_terminal")
        source = dict(family=request["family"], inputs=request["inputs"], evaluation_at_utc=request["evaluation_at_utc"],
            review_reference=request["review_reference"], preparer_id=str(session["actor"]),
            generation_reference=binding["installation_id"]+":"+str(binding["generation"]),
            parent_event_id=parent["envelope"]["event_id"] if parent else None)
        try:
            manifest = events._generate(target, source)
        except (TypeError, KeyError, ValueError):
            raise a.AdminError("invalid_operation_preparation", 400) from None
        p = dict(format="recognition-preparation-v1", preparation_id=str(uuid4()), request=source,
            generated_at_utc=now, generator="permanent._prepare:v1", target_observation=operations._copy_target(target),
            manifest=manifest, manifest_sha256=digest(manifest), population_sha256=digest(manifest["candidates"]),
            dependencies=dependencies.build(target, manifest))
        events._insert(target, "recognition_preparations", "preparation_id,parent_event_id", (p["preparation_id"], source["parent_event_id"]), p)
        e = dict(format="recognition-event-v1", event_id=str(uuid4()), preparation_id=p["preparation_id"],
                 preparation_sha256=digest(p), parent_event_id=source["parent_event_id"], frozen_at_utc=now)
        events._insert(target, "recognition_frozen_events", "event_id,preparation_id", (e["event_id"], p["preparation_id"]), e)
        # Freeze the generated population in this same writer snapshot; no caller
        # manifest/population, synthetic authorization or provider can be supplied.
        history = dict(event_id=e["event_id"], sequence=1, state="READY", reason="local-owner-snapshot-frozen",
                       recorded_at_utc=now, previous_sha256=None)
        events._insert(target, "recognition_event_history", "event_id,sequence", (e["event_id"], 1), history)
        body = operations._local_envelope(events.get_event(target, e["event_id"]), str(uuid4()), now, local_target(binding),
            dict(request_id=request["request_id"], request_sha256=digest(request), actor_id=session["actor"]))
        a.need(len(set(body["member_ids"])) == len(body["member_ids"]), "duplicate_population_member")
        events._insert(target, "recognition_operation_contracts", "operation_id,event_id", (body["operation_id"], e["event_id"]), body)
        operations._append_local(target, "decisions", body["operation_id"], [], "PREPARED", "local-contract-created", now)
        operations._append_local(target, "executions", body["operation_id"], [], "NOT_STARTED", "local-contract-created", now)
        if parent:
            operations._append_local(target, "decisions", request["parent_operation_id"], parent["decisions"], "SUPERSEDED", "local-revision-created", now)
        result = operations.get_operation(target, body["operation_id"])
        target.commit()  # Target graph is atomic; control audit is a separate commit.
        _creation_audit(control, body, session["actor"], now)
        return result


class ProductionOperationContext:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise TypeError("server_operation_context_loader_required")


class ApprovalContinuation:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise TypeError("server_approval_continuation_required")


def load_context(config, operation_id):
    """Restartable, one-use ADMISSION descriptor, not a writer permission grant."""
    with a.transaction(config, lock_target=True) as (_, target, binding):
        op = operations.get_operation(target, operation_id)
        a.need(op["envelope"]["format"] == operations.LOCAL_CONTRACT
               and op["envelope"]["local_target"] == local_target(binding), "production_operation_target_mismatch")
        return _register_context(config, op["envelope"], binding)


def _register_context(config, envelope, binding):
    context = object.__new__(ProductionOperationContext)
    _contexts[context] = dict(config=config, installation_id=binding["installation_id"],
        control_identity=binding["control_identity"], operation_id=envelope["operation_id"], operation_sha256=digest(envelope),
        family=envelope["family"], local_target=local_target(binding), consumed=False)
    return context


def load_recovery_context(config, operation_id):
    """Reconstruct inspection context from a valid seal despite broken projection.

    This grants no recovery or writer permission. The coordinator still requires
    the current owner's session and exact recovery-scoped recent step-up.
    """
    from . import approvals, production_receipts
    with a.transaction(config, lock_target=True) as (control, target, binding):
        claim = production_receipts.journal._read(target, "recognition_execution_claims", operation_id)
        a.need(claim is not None, "recovery_requires_execution_claim")
        value = approvals._read(control, claim["approval_id"])
        a.need(production_receipts.evidence(target, operation_id, value) is not None
               and claim["operation"]["local_target"] == local_target(binding), "recovery_requires_valid_current_target_evidence")
        return _register_context(config, claim["operation"], binding)


def context_data(context):
    a.need(type(context) is ProductionOperationContext and context in _contexts, "server_operation_context_required")
    return _contexts[context]


def consume_context(context):
    data = context_data(context)
    a.need(not data["consumed"], "operation_context_consumed")
    data["consumed"] = True


def bind_approval(data, value, binding):
    if "operation_id" in data:
        a.need(value["approval"]["binding"]["operation_id"] == data["operation_id"]
               and value["approval"]["binding"]["operation_sha256"] == data["operation_sha256"]
               and data["local_target"] == local_target(binding), "execution_context_operation_or_target_mismatch")


def continuation(context, approval_id):
    context_data(context)
    reference = object.__new__(ApprovalContinuation)
    _sessions[reference] = (context, approval_id)
    return reference


def actor_session(control, target, binding, reference, now):
    if type(reference) is not ApprovalContinuation:
        return auth._session(control, target, binding, reference, now)
    a.need(reference in _sessions, "approval_continuation_expired")
    context, aid = _sessions[reference]
    from . import approvals
    value = approvals._read(control, aid)
    data = context_data(context)
    bind_approval(data, value, binding)
    a.need(value["state"] == "APPROVED" and value["approval"]["actor_id"] == binding["owner_id"], "approval_continuation_not_effective")
    return auth._session_hash(control, target, binding, value["approval"]["session_sha256"], now)


def activation_guard(control=None, target=None, binding=None):
    """Trusted local ceremony evidence under the coordinator's existing locks."""
    a.need(control is not None and target is not None and binding is not None
           and control.in_transaction and target.in_transaction, "production_activation_deployment_blocked", 503)
    from .local_readiness import require_activated
    return require_activated(control, binding)


def inspect_operation(config, operation_id):
    from . import approvals, local_execution as coordinator
    with a.transaction(config, lock_target=True) as (control, target, _binding):
        op = operations.get_operation(target, operation_id)
        row = control.execute("SELECT approval_id FROM recognition_approvals WHERE operation_id=?", (operation_id,)).fetchone()
        state = "PREPARED"
        aid = row[0] if row else None
        if aid:
            value = approvals._read(control, aid)
            state = "APPROVED_WAITING" if value["state"] == "APPROVED" else value["state"]
            existing = coordinator._existing(target, operation_id, value)
            if existing:
                state = "COMPLETED" if existing.admission == "ALREADY_EXECUTED" else existing.state
        return dict(operation_id=operation_id, operation_sha256=digest(op["envelope"]), format=op["envelope"]["format"],
                    approval_id=aid, state=state, production_execution="BLOCKED")


def discover_pending(config, *, limit=100):
    a.need(type(limit) is int and 1 <= limit <= 1000, "invalid_worker_limit")
    from . import approvals
    with a.transaction(config, lock_target=True) as (control, target, _binding):
        found = []
        for row in control.execute("SELECT approval_id,operation_id FROM recognition_approvals ORDER BY approval_id"):
            value = approvals._read(control, row[0])
            if value["state"] != "APPROVED":
                continue
            op = operations.get_operation(target, row[1])
            if op["envelope"]["format"] != operations.LOCAL_CONTRACT:
                continue
            from .local_execution import _existing
            if _existing(target, row[1], value) is not None:
                continue
            found.append(dict(approval_id=row[0], operation_id=row[1]))
            if len(found) == limit:
                break
        return found


def continue_pending(config, *, now, limit=100):
    """Bounded trusted worker entry; discovery never grants admission/recovery."""
    from .local_execution import execute_approved_operation
    results = []
    for item in discover_pending(config, limit=limit):
        try:
            context = load_context(config, item["operation_id"])
            result = execute_approved_operation(context, continuation(context, item["approval_id"]), item["approval_id"], now=now)
            results.append(dict(item, execution=asdict(result)))
        except (a.AdminError, ValueError, OSError) as error:
            results.append(dict(item, execution=dict(admission="BLOCKED", state="NOT_STARTED", reason=str(error))))
    return results
