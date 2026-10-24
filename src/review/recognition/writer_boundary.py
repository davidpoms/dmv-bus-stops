"""Narrow transaction capability, not a production authority provisioner."""

from contextlib import contextmanager
from weakref import WeakKeyDictionary

from .authorization import AuthorizationError, target_identity, verify, manifest_binding
from .rules import digest


class ExecutionCapability:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise TypeError("execution_capability_requires_coordinator")


_leases = WeakKeyDictionary()
_local_leases = WeakKeyDictionary()


class LocalExecutionCapability:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise TypeError("local_execution_capability_requires_coordinator")


@contextmanager
def _local_lease(context, conn, manifest, claim):
    # Only a registered fresh disposable workspace can currently reach this
    # boundary. There is deliberately no production context factory.
    from .local_execution import _context
    data = _context(context)
    if "operation_id" in data:
        raise AuthorizationError("production_writer_provisioning_unavailable")
    admission = data.pop("writer_admission", None)
    if admission != (conn, digest(manifest), digest(claim)):
        raise AuthorizationError("protected_final_verification_required")
    if (not conn.in_transaction or target_identity(conn) != target_identity(data["config"].target)
            or claim["writer_sha256"] != digest(manifest)):
        raise AuthorizationError("local_execution_claim_mismatch")
    row = conn.execute("SELECT body_json,body_sha256 FROM recognition_execution_claims WHERE operation_id=?", (claim["operation_id"],)).fetchone()
    from .events import _read
    from .execution import _audit
    history = _audit(conn, claim["operation_id"])
    if (row is None or _read(row) != claim or not history or history[-1]["state"] != "EXECUTING"
            or conn.execute("SELECT 1 FROM recognition_execution_seals WHERE operation_id=?", (claim["operation_id"],)).fetchone()):
        raise AuthorizationError("local_execution_claim_fenced")
    token = object.__new__(LocalExecutionCapability)
    _local_leases[token] = dict(conn=conn, target=target_identity(conn), manifest_sha256=digest(manifest),
        claim_sha256=digest(claim), context=context, consumed=False,
        operation_id=claim["operation_id"], operation_sha256=digest(claim["operation"]),
        family=claim["operation"]["family"], installation_id=claim["binding"]["installation_id"],
        target_id=claim["binding"]["target_id"], restore_generation=claim["binding"]["restore_generation"],
        final_verification_sha256=digest(dict(claim_sha256=digest(claim), approval_sha256=claim["approval_sha256"],
                                            operation_sha256=digest(claim["operation"]))))
    try:
        yield token
    finally:
        _local_leases.pop(token, None)


def verify_local(token, database, manifest, *, conn=None):
    if type(token) is not LocalExecutionCapability:
        return False
    from .local_execution import _context
    if token not in _local_leases:
        raise AuthorizationError("local_execution_capability_expired")
    lease = _local_leases[token]
    _context(lease["context"])
    actual = lease["conn"]
    if (not actual.in_transaction or target_identity(database) != lease["target"]
            or target_identity(actual) != lease["target"] or digest(manifest) != lease["manifest_sha256"]
            or (conn is not None and actual is not conn)):
        raise AuthorizationError("local_execution_capability_binding_mismatch")
    row = actual.execute("SELECT body_json,body_sha256 FROM recognition_execution_claims WHERE body_sha256=?", (lease["claim_sha256"],)).fetchone()
    from .events import _read
    if row is None or digest(_read(row)) != lease["claim_sha256"]:
        raise AuthorizationError("local_execution_claim_missing")
    return True


def production_guard(authorization):
    # Deliberately independent of ordinary authority verification. Production
    # capability provisioning does not exist, even if a verifier is monkeypatched.
    if getattr(authorization, "environment", None) == "production":
        raise AuthorizationError("production_execution_context_unavailable")


@contextmanager
def _lease(conn, database, manifest, authorization, authority):
    if getattr(authorization, "environment", None) != "disposable":
        raise AuthorizationError("disposable_execution_only")
    verify(conn, authorization, authority, **manifest_binding(manifest))
    token = object.__new__(ExecutionCapability)
    _leases[token] = (conn, target_identity(database), digest(manifest), False)
    try:
        yield token
    finally:
        _leases.pop(token, None)


def acquire(token, database, manifest):
    if type(token) is LocalExecutionCapability:
        verify_local(token, database, manifest)
        lease = _local_leases[token]
        if lease["consumed"]:
            raise AuthorizationError("local_execution_capability_consumed")
        lease["consumed"] = True
        return lease["conn"]
    if type(token) is not ExecutionCapability or token not in _leases:
        raise AuthorizationError("coordinator_execution_capability_required")
    conn, target, manifest_sha, consumed = _leases[token]
    if (consumed or not conn.in_transaction or target_identity(conn) != target
            or target_identity(database) != target or digest(manifest) != manifest_sha):
        raise AuthorizationError("execution_capability_binding_mismatch")
    _leases[token] = (conn, target, manifest_sha, True)
    return conn
