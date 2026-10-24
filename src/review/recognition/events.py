"""Immutable preparation data, never executive authorization or award issuance.

All writes require a caller-owned transaction and existing opaque authority.
Only disposable authority can currently be provisioned. No default database,
automatic installation, artifact verifier, or production execution path exists.
"""

from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import json
from uuid import uuid4

from .authorization import target_identity, verify
from .event_schema import check_schema
from .geography import _utc
from .permanent import _prepare
from . import dependencies
from .qualification import Quarantined, require_transaction
from .rules import canonical, digest


CONTRACT = {"format": "recognition-event-v1", "states": ["READY", "STALE", "INVALID"]}
REQUEST_FIELDS = {"family", "inputs", "evaluation_at_utc", "review_reference",
                  "preparer_id", "generation_reference", "parent_event_id"}
TRANSITIONS = {"READY": {"STALE", "INVALID"}, "STALE": {"INVALID"}, "INVALID": set()}


def binding(action, subject):
    """Persistence approval only; this binding cannot authorize existing writers."""
    if action not in {"create_preparation", "freeze_preparation", "record_event_state"}:
        raise Quarantined("invalid_event_action")
    return dict(family="recognition_events", permission="preparation", action=action,
                operation_sha256=digest(subject), policy_sha256=digest(CONTRACT),
                population_sha256=None)


def _require(condition, code):
    if not condition:
        raise Quarantined(code)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def _write(conn, action, subject, authorization, authority):
    require_transaction(conn)
    check_schema(conn)
    _require(target_identity(conn) is not None, "event_file_target_required")
    verify(conn, authorization, authority, **binding(action, subject))
    conn.execute("SAVEPOINT recognition_event_write")
    try:
        # Acquire the SQLite writer lock even for a caller's deferred transaction.
        conn.execute("UPDATE recognition_preparations SET body_json=body_json WHERE 0")
        yield
        verify(conn, authorization, authority, **binding(action, subject))
    except BaseException:
        conn.execute("ROLLBACK TO recognition_event_write")
        raise
    finally:
        conn.execute("RELEASE recognition_event_write")


def _read(row):
    _require(row is not None, "event_record_missing")
    try:
        value = json.loads(row[0])
        _require(isinstance(value, dict) and canonical(value) == row[0] and digest(value) == row[1],
                 "event_record_hash_mismatch")
        return value
    except (TypeError, ValueError) as error:
        raise Quarantined("invalid_event_record") from error


def _insert(conn, table, columns, values, body):
    # Table/column identifiers are internal constants, never caller input.
    conn.execute(f"INSERT INTO {table} ({columns},body_json,body_sha256) "
                 f"VALUES({','.join('?' for _ in range(len(values) + 2))})",
                 (*values, canonical(body), digest(body)))


def _generate(conn, request):
    return _prepare(conn, request["family"], request["inputs"], request["evaluation_at_utc"],
                    request["review_reference"])


def _dependencies(manifest):
    return {key: digest(manifest[key]) for key in
            ("inputs", "report", "identity_history", "ledger", "rule")}


def create_preparation(conn, request, *, authorization=None, authority=None):
    """Generate from existing rules/data; no candidate or manifest argument exists.

    request contains exactly REQUEST_FIELDS. Repeated requests intentionally create
    distinct preparations; freeze is idempotent for each preparation identity.
    """
    request = json.loads(canonical(request))
    _require(isinstance(request, dict) and set(request) == REQUEST_FIELDS, "invalid_preparation_request")
    for field in ("preparer_id", "generation_reference", "review_reference"):
        _require(isinstance(request[field], str) and bool(request[field].strip()), "missing_" + field)
    with _write(conn, "create_preparation", request, authorization, authority):
        parent = request["parent_event_id"]
        if parent is not None:
            prior = get_event(conn, parent)["preparation"]
            _require(prior["request"]["family"] == request["family"], "revision_family_mismatch")
        manifest = _generate(conn, request)
        body = {"format": "recognition-preparation-v1", "preparation_id": str(uuid4()),
                "request": request, "generated_at_utc": _now(),
                "generator": "permanent._prepare:v1", "target_observation": asdict(target_identity(conn)),
                "manifest": manifest, "manifest_sha256": digest(manifest),
                "population_sha256": digest(manifest["candidates"]),
                "dependencies": dependencies.build(conn, manifest)}
        _insert(conn, "recognition_preparations", "preparation_id,parent_event_id",
                (body["preparation_id"], parent), body)
        return body


def _preparation(conn, preparation_id):
    row = conn.execute("SELECT body_json,body_sha256,parent_event_id FROM recognition_preparations "
                       "WHERE preparation_id=?", (preparation_id,)).fetchone()
    body = _read(row)
    try:
        manifest = body["manifest"]
        request = body["request"]
        _require(set(body) == {"format", "preparation_id", "request", "generated_at_utc", "generator",
                              "target_observation", "manifest", "manifest_sha256", "population_sha256",
                              "dependencies"} and set(request) == REQUEST_FIELDS,
                 "malformed_preparation")
        _utc(body["generated_at_utc"])
        _require(body["format"] == "recognition-preparation-v1" and
                 body["preparation_id"] == preparation_id and body["request"]["parent_event_id"] == row[2] and
                 body["manifest_sha256"] == digest(manifest) and
                 body["population_sha256"] == digest(manifest["candidates"]), "preparation_binding_mismatch")
        if body["dependencies"] != _dependencies(manifest):
            dependencies.validate_binding(body["dependencies"], manifest)
        _require(manifest["family"] == request["family"] and manifest["inputs"] == request["inputs"] and
                 manifest["evaluation_at_utc"] == request["evaluation_at_utc"] and
                 manifest["authorization_reference"] == request["review_reference"], "request_binding_mismatch")
        dependencies.validate_manifest(manifest)
    except (KeyError, TypeError) as error:
        raise Quarantined("malformed_preparation") from error
    return body


def freeze_preparation(conn, preparation_id, *, authorization=None, authority=None):
    """Recheck the generated snapshot and freeze once, atomically with READY history."""
    with _write(conn, "freeze_preparation", preparation_id, authorization, authority):
        preparation = _preparation(conn, preparation_id)
        existing = conn.execute("SELECT event_id FROM recognition_frozen_events WHERE preparation_id=?",
                                (preparation_id,)).fetchone()
        if existing:
            return get_event(conn, existing[0])
        _require(preparation["target_observation"] == asdict(target_identity(conn)), "event_target_changed")
        _require(_generate(conn, preparation["request"]) == preparation["manifest"], "preparation_stale")
        _require(dependencies.build(conn, preparation["manifest"]) == preparation["dependencies"],
                 "preparation_dependencies_stale")
        body = {"format": CONTRACT["format"], "event_id": str(uuid4()),
                "preparation_id": preparation_id, "preparation_sha256": digest(preparation),
                "parent_event_id": preparation["request"]["parent_event_id"], "frozen_at_utc": _now()}
        _insert(conn, "recognition_frozen_events", "event_id,preparation_id",
                (body["event_id"], preparation_id), body)
        _history(conn, body["event_id"], [], "READY", "snapshot-matched-at-freeze")
        return get_event(conn, body["event_id"])


def create_revision(conn, parent_event_id, request, *, authorization=None, authority=None):
    """A revision is a new preparation linked to an existing frozen event."""
    _require(parent_event_id is not None and request.get("parent_event_id") == parent_event_id,
             "revision_parent_required")
    return create_preparation(conn, request, authorization=authorization, authority=authority)


def _history(conn, event_id, history, state, reason):
    sequence = len(history) + 1
    body = dict(event_id=event_id, sequence=sequence, state=state, reason=reason,
                recorded_at_utc=_now(), previous_sha256=digest(history[-1]) if history else None)
    _insert(conn, "recognition_event_history", "event_id,sequence", (event_id, sequence), body)


def get_event(conn, event_id):
    """Return detached data, not an authority; READY is not a freshness guarantee."""
    check_schema(conn)
    row = conn.execute("SELECT body_json,body_sha256,preparation_id FROM recognition_frozen_events "
                       "WHERE event_id=?", (event_id,)).fetchone()
    body = _read(row)
    try:
        _require(set(body) == {"format", "event_id", "preparation_id", "preparation_sha256",
                              "parent_event_id", "frozen_at_utc"}, "malformed_event")
        _utc(body["frozen_at_utc"])
        preparation = _preparation(conn, row[2])
        _require(body["format"] == CONTRACT["format"] and body["event_id"] == event_id and
                 body["preparation_id"] == row[2] and body["preparation_sha256"] == digest(preparation) and
                 body["parent_event_id"] == preparation["request"]["parent_event_id"], "event_binding_mismatch")
        history = []
        for record in conn.execute("SELECT body_json,body_sha256,sequence FROM recognition_event_history "
                                   "WHERE event_id=? ORDER BY sequence", (event_id,)):
            item = _read(record)
            _require(set(item) == {"event_id", "sequence", "state", "reason", "recorded_at_utc",
                                  "previous_sha256"} and isinstance(item["reason"], str) and
                     bool(item["reason"].strip()), "malformed_event_history")
            _utc(item["recorded_at_utc"])
            _require(item["event_id"] == event_id and item["sequence"] == record[2] == len(history) + 1 and
                     item["previous_sha256"] == (digest(history[-1]) if history else None) and
                     (item["state"] in TRANSITIONS[history[-1]["state"]] if history else
                      item["state"] == "READY"), "invalid_event_history")
            history.append(item)
        _require(bool(history), "event_history_missing")
    except (KeyError, TypeError) as error:
        raise Quarantined("malformed_event") from error
    return {"event": body, "preparation": preparation, "history": history, "state": history[-1]["state"]}


def record_event_state(conn, event_id, state, reason, *, authorization=None, authority=None):
    """Append a conservative invalidation; never restore validity or issue awards."""
    _require(isinstance(reason, str) and bool(reason.strip()), "event_reason_required")
    subject = dict(event_id=event_id, state=state, reason=reason)
    with _write(conn, "record_event_state", subject, authorization, authority):
        current = get_event(conn, event_id)
        last = current["history"][-1]
        if last["state"] == state and last["reason"] == reason:
            return current
        _require(state in TRANSITIONS[current["state"]], "invalid_event_transition")
        _history(conn, event_id, current["history"], state, reason)
        return get_event(conn, event_id)
