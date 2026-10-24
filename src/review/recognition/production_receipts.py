"""Versioned execution evidence and rebuildable operation projection.

Historical seals retain full frozen population/outcomes. Projection never invokes
a writer. Actual production capability provisioning remains unavailable.
"""

from . import administration as a, events, operations, permanent, execution as journal
from .rules import canonical, digest


FORMAT = "recognition-production-execution-receipt-v1"


class ProjectionConflict(a.AdminError):
    def __init__(self):
        super().__init__("projection_conflicts_with_evidence", 409)


def _records(conn, manifest):
    writer = digest(manifest)
    result = {}
    for table in ("recognition_private_operations", "recognition_first_look_claims", "recognition_geography_snapshots", "recognition_geography_awards"):
        result[table] = sorted((dict(row) for row in conn.execute(f"SELECT * FROM {table} WHERE operation_id=?", (writer,))), key=canonical)
    for table, column, values in (
        ("recognition_private_rules", "rule_key", [manifest["rule"]["rule_key"]]),
        ("recognition_geography_members", "snapshot_id", [r["snapshot_id"] for r in result["recognition_geography_snapshots"]]),
        ("recognition_geography_witnesses", "award_id", [r["award_id"] for r in result["recognition_geography_awards"]]),
        ("recognition_geography_scope_identities", "scope_key", [r["scope_key"] for r in result["recognition_geography_snapshots"]])):
        result[table] = sorted((dict(row) for value in values for row in conn.execute(f"SELECT * FROM {table} WHERE {column}=?", (value,))), key=canonical)
    return result


def build(conn, claim, manifest, result, now):
    e = claim["operation"]
    permanent._verify_operation_records(conn, digest(manifest))
    a.need(e["format"] == operations.LOCAL_CONTRACT and e["accounting_policy"] == operations.LOCAL_POLICY
           and result == dict(issued=True, operation_id=digest(manifest), records=len(e["member_ids"])), "invalid_production_writer_accounting")
    return dict(format=FORMAT, execution_scope=claim["execution_scope"], outcome="COMPLETED",
        operation_id=e["operation_id"], operation_sha256=digest(e), event_id=e["event_id"], preparation_id=e["preparation_id"],
        approval_id=claim["approval_id"], approval_sha256=claim["approval_sha256"], actor_id=claim["actor_id"], reason=claim["approval_reason"],
        installation_id=e["local_target"]["installation_id"], target_id=e["local_target"]["target_id"],
        restore_generation=e["local_target"]["restore_generation"], target=e["local_target"]["target"], writer_family=e["family"],
        writer_manifest_sha256=digest(manifest), rule_sha256=e["rule_sha256"], claim_id=claim["claim_id"], claim_sha256=digest(claim),
        seal_id=digest(dict(operation_id=e["operation_id"], claim_sha256=digest(claim), writer_sha256=digest(manifest))),
        started_at_utc=claim["claimed_at_utc"], finished_at_utc=now, authorized_count=len(e["member_ids"]),
        frozen_population=manifest["candidates"], population_sha256=e["population_sha256"],
        successful=[dict(member_id=m, outcome_reference=digest(manifest)+":"+m) for m in e["member_ids"]], quarantined=[], other=[],
        writer_result=result, actual_records=_records(conn, manifest), writer_evidence_sha256=journal._writer_evidence(conn, digest(manifest)))


def validate(operation, receipt):
    e = operation["envelope"]
    ref = next((x["evidence"] for x in operation["decisions"] if x["state"] == "AUTHORIZED"), None)
    a.need(type(receipt) is dict and receipt["format"] == FORMAT and receipt["outcome"] == "COMPLETED"
           and receipt["operation_id"] == e["operation_id"] and receipt["operation_sha256"] == digest(e)
           and receipt["event_id"] == e["event_id"] and receipt["preparation_id"] == e["preparation_id"]
           and ref == dict(approval_id=receipt["approval_id"], approval_sha256=receipt["approval_sha256"]), "production_receipt_binding_mismatch")
    target = e["local_target"]
    a.need(receipt["installation_id"] == target["installation_id"] and receipt["target_id"] == target["target_id"]
           and receipt["restore_generation"] == target["restore_generation"] and receipt["target"] == target["target"]
           and receipt["writer_family"] == e["family"] and receipt["writer_manifest_sha256"] == e["writer_manifest_sha256"]
           and receipt["population_sha256"] == e["population_sha256"] == digest(receipt["frozen_population"])
           and [digest(c) for c in receipt["frozen_population"]] == e["member_ids"], "production_receipt_population_or_target_mismatch")
    a.need(e["accounting_policy"] == operations.LOCAL_POLICY and type(receipt["authorized_count"]) is int
           and receipt["authorized_count"] == len(e["member_ids"]) and not receipt["quarantined"] and not receipt["other"]
           and receipt["successful"] == [dict(member_id=m, outcome_reference=e["writer_manifest_sha256"]+":"+m) for m in e["member_ids"]]
           and receipt["writer_result"] == dict(issued=True, operation_id=e["writer_manifest_sha256"], records=len(e["member_ids"]))
           and a.timestamp(receipt["finished_at_utc"]) >= a.timestamp(receipt["started_at_utc"]), "production_receipt_accounting_mismatch")
    return dict(authorized=len(e["member_ids"]), successful=len(e["member_ids"]), quarantined=0, other=0, unaccounted=0)


def evidence(conn, oid, value):
    # Deliberately independent of operation_receipts and mutable/current views:
    # a broken projection must not conceal the committed historical seal.
    claim = journal._read(conn, "recognition_execution_claims", oid)
    seal = journal._read(conn, "recognition_execution_seals", oid)
    if not seal:
        return None
    a.need(claim and claim["operation_id"] == oid and claim["approval_id"] == value["approval"]["approval_id"]
           and claim["approval_sha256"] == value["approval_sha256"] and claim["binding"] == value["approval"]["binding"]
           and digest(claim["operation"]) == claim["binding"]["operation_sha256"]
           and seal["claim_sha256"] == digest(claim), "production_execution_evidence_mismatch")
    e = claim["operation"]
    row = conn.execute("SELECT body_json,body_sha256 FROM recognition_operation_contracts WHERE operation_id=?", (oid,)).fetchone()
    a.need(events._read(row) == e, "archived_operation_changed")
    frozen = events.get_event(conn, e["event_id"])
    a.need(e == operations._local_envelope(frozen, oid, e["created_at_utc"], e["local_target"], e["creation"]), "archived_operation_binding_mismatch")
    manifest = frozen["preparation"]["manifest"]
    receipt = seal["receipt"]
    expected = build(conn, claim, manifest, dict(issued=True, operation_id=digest(manifest), records=len(e["member_ids"])), receipt["finished_at_utc"])
    indexed = conn.execute("SELECT writer_sha256 FROM recognition_execution_seals WHERE operation_id=?", (oid,)).fetchone()[0]
    a.need(receipt == expected and indexed == seal["writer_sha256"] == digest(manifest) == claim["writer_sha256"]
           and receipt["writer_evidence_sha256"] == seal["evidence_sha256"], "production_execution_seal_or_records_mismatch")
    return seal


def projection_status(conn, oid, seal):
    row = conn.execute("SELECT body_json,body_sha256 FROM recognition_operation_receipts WHERE operation_id=?", (oid,)).fetchone()
    if not row:
        return "MISSING"
    try:
        if events._read(row) != seal["receipt"]:
            return "CONFLICT"
        operations.get_operation(conn, oid)
    except (ValueError, KeyError, TypeError):
        return "CONFLICT"
    return "CURRENT"


def project(conn, oid, value, *, now, kind="RECOVERY"):
    a.need(conn.in_transaction, "projection_writer_transaction_required")
    seal = evidence(conn, oid, value)
    a.need(seal is not None, "projection_requires_committed_seal")
    receipt = seal["receipt"]
    if projection_status(conn, oid, seal) == "CONFLICT":
        raise ProjectionConflict()
    decisions = operations._history(conn, "decisions", oid, local=True)
    executions = operations._history(conn, "executions", oid, local=True)
    ref = dict(approval_id=receipt["approval_id"], approval_sha256=receipt["approval_sha256"])
    if decisions[-1]["state"] == "PREPARED":
        operations._append_local(conn, "decisions", oid, decisions, "AUTHORIZED", "durable-local-approval-evidenced", now, ref)
    elif decisions[-1]["state"] != "AUTHORIZED" or decisions[-1]["evidence"] != ref:
        raise ProjectionConflict()
    if not conn.execute("SELECT 1 FROM recognition_operation_receipts WHERE operation_id=?", (oid,)).fetchone():
        events._insert(conn, "recognition_operation_receipts", "operation_id", (oid,), receipt)
    if executions[-1]["state"] == "NOT_STARTED":
        operations._append_local(conn, "executions", oid, executions, "EXECUTING", "durable-claim-projection", now)
        executions = operations._history(conn, "executions", oid, local=True)
    if executions[-1]["state"] == "EXECUTING":
        operations._append_local(conn, "executions", oid, executions, "COMPLETED", "production-receipt-projection", now, dict(receipt_sha256=digest(receipt)))
    a.need(projection_status(conn, oid, seal) == "CURRENT", "projection_did_not_converge")
    history = journal._audit(conn, oid)
    if history[-1]["state"] != "COMPLETED":
        journal._append(conn, oid, "COMPLETED", "production-receipt-projection-current", now, kind)
    return receipt


def effective_recognition(conn, oid, value):
    """Original effective view; future explicit correction overlays remain separate."""
    seal = evidence(conn, oid, value)
    a.need(seal is not None, "recognition_evidence_missing")
    r = seal["receipt"]
    return dict(operation_id=oid, evidence_sha256=digest(r), corrections_applied=[],
                family=r["writer_family"], awards=r["frozen_population"])


def recovery_binding(control, target, oid):
    if not target.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_execution_claims'").fetchone():
        return None
    claim = journal._read(target, "recognition_execution_claims", oid)
    if not claim or claim.get("execution_scope") != "disposable-production-contract-fixture" or not journal._read(target, "recognition_execution_seals", oid):
        return None
    from . import approvals
    value = approvals._read(control, claim["approval_id"])
    seal = evidence(target, oid, value)
    return digest(claim["operation"]), digest(dict(recovery_evidence_sha256=digest(seal),
        decisions=operations._history(target, "decisions", oid, local=True),
        executions=operations._history(target, "executions", oid, local=True),
        event_state=events.get_event(target, claim["operation"]["event_id"])["state"]))
