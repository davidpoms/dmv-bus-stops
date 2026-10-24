"""Snapshot-scoped dependency observations; never approval or execution.

The global review inventory/reconciliation boundaries below are intentional:
they are existing preparation prerequisites, not a database-wide fingerprint.
"""

from dataclasses import asdict
import json
import sqlite3

from . import first_looks, geography, permanent
from .authorization import target_identity
from .geography import _scope
from .qualification import Quarantined, qualify, require_transaction
from .rules import canonical, digest, load_rule


FORMAT = "recognition-dependencies-v1"
BOUNDARY = {
    "reviews": "all-assignment-ids-and-qualification-fields;all-community-review-observations-v1",
    "ledger": "all-immutable-completions-and-referenced-qualification-rules-v1",
    "identity": "complete-physical-identity-history-v1",
    "existence": "referenced-reviewers-and-stops;geography-supplied-members-v1",
    "geography": "exact-supplied-snapshot-and-member-active-status;no-label-discovery-v1",
    "permanent": "first-look-candidate-stops-or-geography-supplied-scope-identities-v1",
    "mode": "historical-first-look-or-geography-catch-up;no-live-finality-v1",
}
IDENTITY = {
    "physical_stop_identity_events": {"id", "event_type"},
    "physical_stop_identity_edges": {"event_id", "predecessor_physical_stop_id", "successor_physical_stop_id"},
    "physical_stop_identity_state": {"physical_stop_id", "identity_status"},
}
REQUIRED = {
    "stop_review_assignments": {"id", "stop_id", "reviewer_id", "status", "completed_at"},
    "stop_observations": {"id", "assignment_id", "reviewer_id", "physical_stop_id", "source"},
    "community_reviewers": {"id"}, "physical_stops": {"id"},
    "recognition_completions": {"assignment_id", "observation_id", "reviewer_id", "physical_stop_id",
                                "qualification_rule_key", "completed_at_utc", "timestamp_provenance"},
    "recognition_rule_versions": {"rule_key", "family", "definition_json", "definition_sha256"},
    **IDENTITY,
}
_UNSUPPLIED = object()


class InvalidDependency(Quarantined):
    """A bounded dependency code, never a raw SQLite/path/payload diagnostic."""


def _require(condition, code):
    if not condition:
        raise InvalidDependency(code)


def _rows(conn, sql, params=()):
    return sorted((dict(row) for row in conn.execute(sql, params)), key=canonical)


def _schema(conn, table, columns):
    actual = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    _require(columns <= actual, "missing_or_unsupported_schema:" + table)


def validate_manifest(manifest):
    """Check archived content without equating a current rule change to corruption."""
    _require(manifest["format"] == "private-recognition-operation-v1" and
             manifest["family"] in {"first_look", "geography_steward"}, "unsupported_event_family")
    _require(manifest["rule_sha256"] == digest(manifest["rule"]), "corrupted_rule")
    report = manifest["report"]
    _require(report["report_sha256"] == digest({k: v for k, v in report.items() if k != "report_sha256"}),
             "corrupted_report")
    _require(isinstance(manifest["candidates"], list), "corrupted_population")
    _require(manifest["rule"]["family"] == manifest["family"], "corrupted_rule_family")
    # Historical integrity is deliberately separate from running today's candidate
    # mathematics against yesterday's report. build() validates current generation;
    # recheck() compares the captured policy before granting snapshot-only READY.


def _snapshot(manifest, supplied=_UNSUPPLIED):
    if manifest["family"] != "geography_steward":
        _require(supplied is _UNSUPPLIED, "unexpected_scope_snapshot")
        return None
    snapshot = json.loads(canonical(manifest["inputs"]["scope_snapshot"] if supplied is _UNSUPPLIED else supplied))
    _require(isinstance(snapshot, dict) and snapshot.get("format") == "geography-scope-snapshot-v1" and
             isinstance(snapshot.get("scopes"), list) and bool(snapshot["scopes"]), "missing_scope_snapshot")
    _require(snapshot.get("snapshot_sha256") == digest({k: v for k, v in snapshot.items() if k != "snapshot_sha256"}),
             "corrupted_scope_snapshot")
    identities, keys = set(), set()
    for scope in snapshot["scopes"]:
        _, members, issues = _scope(scope, manifest["evaluation_at_utc"])
        # A predicate approved in the archived rule remains readable after the
        # current policy changes. _policy comparison will classify that as STALE.
        if scope.get("active_membership_predicate") == manifest["rule"].get("active"):
            issues = [issue for issue in issues if issue != "invalid_active_membership_predicate"]
        _require(not issues, "invalid_scope_certification_or_membership")
        _require(scope["certification"].get("independent") is True and
                 permanent.text(scope.get("identity_review_reference")) and permanent.text(scope.get("display_label")) and
                 scope.get("quality_findings") == [] and len(members) == len(scope["members"]),
                 "missing_scope_prerequisite")
        identity = (scope["dimension"], scope["canonical_geography_id"])
        _require(scope["scope_key"] not in keys and identity not in identities, "duplicate_scope_identity")
        keys.add(scope["scope_key"])
        identities.add(identity)
    return snapshot


def _policy(manifest):
    rule = permanent.DEFINITIONS.get(manifest["family"])
    _require(isinstance(rule, dict) and permanent.text(rule.get("rule_key")) and
             rule.get("family") == manifest["family"], "unsupported_rule")
    return dict(definition=rule,
                ordering=first_looks.ORDERING if manifest["family"] == "first_look" else None,
                geography_thresholds=geography.DEFAULT_THRESHOLDS if manifest["family"] == "geography_steward" else None,
                permanent_thresholds=permanent.DEFAULT_THRESHOLDS if manifest["family"] == "geography_steward" else None,
                active_predicate=geography.ACTIVE if manifest["family"] == "geography_steward" else None)


def _permanent_records(conn, manifest, tables):
    result = {}
    if manifest["family"] == "first_look":
        stops = {item["physical_stop_id"] for item in manifest["candidates"]}
        selections = {"recognition_first_look_claims": ("physical_stop_id", stops)}
    else:
        scopes = manifest["inputs"]["scope_snapshot"]["scopes"]
        keys = {scope["scope_key"] for scope in scopes}
        identities = {(scope["dimension"], scope["canonical_geography_id"]) for scope in scopes}
        selections = {"recognition_geography_scope_identities": ("scope_key", keys),
                      "recognition_geography_snapshots": ("scope_key", keys),
                      "recognition_geography_awards": ("scope_key", keys)}
    for table, (key, values) in selections.items():
        result[table] = []
        if table in tables:
            _schema(conn, table, {key})
            rows = _rows(conn, f"SELECT * FROM {table}")
            result[table] = [row for row in rows if row[key] in values or
                             (table == "recognition_geography_scope_identities" and
                              (row["dimension"], row["canonical_geography_id"]) in identities)]
    if manifest["family"] == "geography_steward":
        for table, key, parent in (
                ("recognition_geography_members", "snapshot_id", "recognition_geography_snapshots"),
                ("recognition_geography_witnesses", "award_id", "recognition_geography_awards")):
            ids = {row[key] for row in result[parent]}
            result[table] = []
            if table in tables:
                _schema(conn, table, {key})
                result[table] = [row for row in _rows(conn, f"SELECT * FROM {table}") if row[key] in ids]
    return result


def _observe(conn, manifest):
    for table, columns in REQUIRED.items():
        _schema(conn, table, columns)
    assignments = _rows(conn, "SELECT id,stop_id,reviewer_id,status,completed_at FROM stop_review_assignments")
    observations = _rows(conn, "SELECT id,assignment_id,reviewer_id,physical_stop_id,source "
                         "FROM stop_observations WHERE source='community_review'")
    ledger = _rows(conn, "SELECT * FROM recognition_completions")
    rules = {}
    for key in sorted({row["qualification_rule_key"] for row in ledger}):
        try:
            rules[key] = load_rule(conn, key)
        except ValueError:
            raise InvalidDependency("missing_or_unsupported_qualification_rule") from None
    stops = {row["stop_id"] for row in assignments} | {row["physical_stop_id"] for row in observations + ledger}
    owners = {row["reviewer_id"] for row in assignments + observations + ledger}
    snapshot = _snapshot(manifest)
    active = []
    if snapshot:
        members = {m["physical_stop_id"] for s in snapshot["scopes"] for m in s["members"]}
        stops |= members
        _schema(conn, "stop_gtfs_status", {"physical_stop_id", "current_gtfs"})
        active = [row for row in _rows(conn, "SELECT physical_stop_id,current_gtfs FROM stop_gtfs_status")
                  if row["physical_stop_id"] in members]
    existing_stops = {row[0] for row in conn.execute("SELECT id FROM physical_stops")}
    existing_owners = {row[0] for row in conn.execute("SELECT id FROM community_reviewers")}
    facts = manifest["report"]["qualified" if manifest["family"] == "first_look" else "qualified_ledger_evidence"]
    required_stops = {fact["physical_stop_id"] for fact in facts}
    if snapshot:
        required_stops |= members
        _require(all(any(row["physical_stop_id"] == member for row in active) for member in members),
                 "missing_active_status")
        _require(all(sum(row["physical_stop_id"] == member for row in active) == 1 for member in members) and
                 all(type(row["current_gtfs"]) is int and row["current_gtfs"] in (0, 1) for row in active),
                 "malformed_active_status")
    _require(required_stops <= existing_stops and {fact["reviewer_id"] for fact in facts} <= existing_owners,
             "missing_required_identity")
    # Removal of an assignment is a population change. An extant assignment that
    # loses evidence required by its frozen qualification has an absent prerequisite.
    assignment_ids = {row["id"] for row in assignments}
    observed_ids = {row["assignment_id"] for row in observations}
    ledger_ids = {row["assignment_id"] for row in ledger}
    required_ids = {fact["assignment_id"] for fact in facts} & assignment_ids
    _require(required_ids <= observed_ids, "missing_required_community_evidence")
    _require(required_ids <= ledger_ids, "missing_required_completion")
    old_facts = {fact["assignment_id"]: fact for fact in facts}
    for assignment_id in sorted(required_ids):
        provenance = manifest["inputs"].get("sqlite_utc_provenance")
        if manifest["family"] == "geography_steward":
            prefix = "sqlite_current_timestamp_utc:"
            old_provenance = old_facts[assignment_id]["timestamp_provenance"]
            if old_provenance.startswith(prefix):
                provenance = old_provenance[len(prefix):]
        try:
            qualify(conn, assignment_id, sqlite_utc_provenance=provenance)
        except Quarantined as error:
            # A valid status transition changes population membership; malformed
            # timestamps or ambiguous/mismatched evidence are invalid prerequisites.
            if str(error) != "assignment_not_completed":
                raise InvalidDependency("invalid_required_qualification:" + str(error)) from None
    try:
        identity = permanent._identity(conn)
    except Quarantined:
        raise InvalidDependency("invalid_identity_history") from None
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return dict(assignment_inventory=sorted(assignment_ids), review_evidence=dict(assignments=assignments,
                observations=observations), completions=ledger, qualification_rules=rules,
                existence=dict(stops=sorted(stops & existing_stops), reviewers=sorted(owners & existing_owners)),
                identity=identity, current_active=active, policy=_policy(manifest),
                permanent_records=_permanent_records(conn, manifest, tables), scope_snapshot=snapshot)


def build(conn, manifest):
    """Bind declared query boundaries and actual observations in the same transaction."""
    require_transaction(conn)
    validate_manifest(manifest)
    permanent._validate_manifest(manifest)
    body = dict(format=FORMAT, family=manifest["family"], manifest_sha256=digest(manifest),
                boundary=BOUNDARY, observations=_observe(conn, manifest))
    return json.loads(canonical({**body, "sha256": digest(body)}))


def validate_binding(dependencies, manifest):
    _require(isinstance(dependencies, dict) and set(dependencies) == {
        "format", "family", "manifest_sha256", "boundary", "observations", "sha256"}, "dependency_manifest_required")
    _require(dependencies["format"] == FORMAT and dependencies["boundary"] == BOUNDARY,
             "unsupported_dependency_boundary")
    _require(dependencies["family"] == manifest["family"] and dependencies["manifest_sha256"] == digest(manifest) and
             dependencies["sha256"] == digest({k: v for k, v in dependencies.items() if k != "sha256"}),
             "corrupted_dependency_manifest")
    _require(set(dependencies["observations"]) == {"assignment_inventory", "review_evidence", "completions",
             "qualification_rules", "existence", "identity", "current_active", "policy", "permanent_records",
             "scope_snapshot"}, "corrupted_dependency_observations")


def _result(state, *reasons):
    return dict(state=state, reasons=sorted(set(reasons)))


def recheck(conn, event_id, *, current_scope_snapshot=_UNSUPPLIED):
    """Read-only result for the caller's SQLite snapshot, never a commit guarantee.

    An optional replacement Geography snapshot is untrusted comparison material,
    not certification. No current external snapshot registry exists in this slice.
    """
    from .events import get_event
    try:
        if not conn.in_transaction:
            return _result("VERIFICATION_FAILURE", "transaction_required")
        frozen = get_event(conn, event_id)
        preparation = frozen["preparation"]
        manifest = preparation["manifest"]
        dependencies = preparation["dependencies"]
        validate_binding(dependencies, manifest)
        if frozen["state"] == "INVALID":
            return _result("INVALID", "previously_invalid")
        _require(preparation["target_observation"] == asdict(target_identity(conn)), "target_observation_mismatch")
        current = _observe(conn, manifest)
        current["scope_snapshot"] = _snapshot(manifest, current_scope_snapshot)
        changes = [key + "_changed" for key, value in current.items()
                   if value != dependencies["observations"][key]]
        if frozen["state"] == "STALE":
            return _result("STALE", "previously_stale", *changes)
        return _result("STALE", *changes) if changes else _result("READY")
    except InvalidDependency as error:
        return _result("INVALID", str(error))
    except (Quarantined, KeyError, TypeError, ValueError):
        return _result("INVALID", "malformed_event_or_prerequisite")
    except sqlite3.DatabaseError as error:
        code = getattr(error, "sqlite_errorcode", 0) & 255
        if code in (sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB):
            return _result("INVALID", "corrupted_database")
        return _result("VERIFICATION_FAILURE", "dependency_read_failed")
    except OSError:
        return _result("VERIFICATION_FAILURE", "target_read_failed")


def recording_subject(event_id, result):
    """Existing state-recording approval subject; grants no authority."""
    _require(result["state"] in {"STALE", "INVALID"}, "no_invalidation_to_record")
    return dict(event_id=event_id, state=result["state"], reason=canonical({"dependencies": result["reasons"]}))


def record_validation(conn, event_id, expected, *, authorization=None, authority=None,
                      current_scope_snapshot=_UNSUPPLIED):
    """Recheck under the writer lock before using existing append-only history.

    Approval must bind the exact expected state/reasons. A changed result aborts;
    a read failure never becomes a durable validity decision. Corrupt events may
    be reported INVALID but cannot be written through an untrustworthy history.
    """
    from . import events
    expected = json.loads(canonical(expected))
    subject = recording_subject(event_id, expected)
    with events._write(conn, "record_event_state", subject, authorization, authority):
        actual = recheck(conn, event_id, current_scope_snapshot=current_scope_snapshot)
        _require(actual == expected, "validation_result_changed")
        current = events.get_event(conn, event_id)
        if current["state"] == actual["state"]:
            return current
        return events.record_event_state(conn, **subject, authorization=authorization, authority=authority)
