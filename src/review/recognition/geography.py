"""Offline Geography Steward projections; no certification, capture or issuance."""

import json
import re

from src.amenities.status_synthesis import canonical_dc_ward
from .qualification import Quarantined, permanent_time, qualify
from .rules import canonical, digest, load_rule
from .report_connection import report_connection as connection


FORMAT = "geography-adjudication-report-v1"
DIMENSIONS = ("dc_anc", "dc_ward", "municipality", "county", "state")
SUPPORTED_DIMENSIONS = (*DIMENSIONS, "census_place")
ACTIVE = "stop_gtfs_status.current_gtfs = 1"
DEFAULT_THRESHOLDS = {"minimum_population": 10, "large_population": 100,
                      "small_minimum": 5, "large_minimum": 10,
                      "small_percentages": [25, 50, 75, 100],
                      "large_percentages": [10, 25, 50, 75]}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _utc(value):
    """Report boundaries are explicit whole-second UTC, not naive/offset dates."""
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("canonical_utc_required")
    normalized, _ = permanent_time(value)
    if normalized != value:
        raise ValueError("canonical_utc_required")
    return normalized


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def _thresholds(value):
    result = json.loads(canonical(DEFAULT_THRESHOLDS if value is None else value))
    if set(result) != set(DEFAULT_THRESHOLDS):
        raise ValueError("invalid_thresholds")
    for key in ("minimum_population", "large_population", "small_minimum", "large_minimum"):
        if type(result[key]) is not int or result[key] <= 0:
            raise ValueError("invalid_thresholds")
    if result["minimum_population"] >= result["large_population"]:
        raise ValueError("invalid_thresholds")
    for key in ("small_percentages", "large_percentages"):
        items = result[key]
        if (not isinstance(items, list) or not items
                or any(type(n) is not int or not 1 <= n <= 100 for n in items)
                or sorted(set(items)) != items):
            raise ValueError("invalid_thresholds")
    return result


def _scope(scope, cutoff):
    issues = []
    if not isinstance(scope, dict):
        return {}, [], ["invalid_scope_structure"]
    for field in ("scope_key", "canonical_geography_id", "scope_version"):
        if not _text(scope.get(field)):
            issues.append("missing_" + field)
    if _text(scope.get("canonical_geography_id")) and ":" not in scope["canonical_geography_id"]:
        issues.append("geography_identity_not_namespaced")
    if scope.get("dimension") not in SUPPORTED_DIMENSIONS:
        issues.append("unsupported_dimension")
    for field in ("captured_at_utc", "effective_at_utc"):
        try:
            if _utc(scope.get(field)) > cutoff:
                issues.append("snapshot_after_evaluation_cutoff")
        except ValueError:
            issues.append("invalid_" + field)
    for field in ("source_provenance", "boundary_provenance"):
        provenance = scope.get(field)
        if (not isinstance(provenance, dict) or not _text(provenance.get("reference"))
                or not _hash(provenance.get("sha256"))):
            issues.append("missing_or_invalid_" + field)
    certification = scope.get("certification")
    if (not isinstance(certification, dict) or certification.get("approved") is not True
            or not _text(certification.get("reference"))):
        issues.append("scope_not_certified")
    if scope.get("active_membership_predicate") != ACTIVE:
        issues.append("invalid_active_membership_predicate")
    members = scope.get("members")
    if not isinstance(members, list):
        return scope, [], sorted(set(issues + ["missing_members"]))
    if scope.get("membership_sha256") != digest(members):
        issues.append("membership_hash_mismatch")
    seen = {}
    for member in members:
        if (not isinstance(member, dict) or set(member) != {"physical_stop_id", "current_gtfs"}
                or type(member["physical_stop_id"]) is not int or member["physical_stop_id"] <= 0
                or type(member["current_gtfs"]) is not int):
            issues.append("invalid_member")
            continue
        stop, active = member["physical_stop_id"], member["current_gtfs"]
        if stop in seen and seen[stop] != active:
            issues.append("ambiguous_member_status")
        seen[stop] = active
    return scope, sorted(stop for stop, active in seen.items() if active == 1), sorted(set(issues))


def _discover(conn, tables):
    """Current labels are discoverable candidates, NEVER certified scope inputs."""
    if "stop_jurisdiction" not in tables:
        return [], ["current_geography_unavailable"]
    columns = {r[1] for r in conn.execute("PRAGMA table_info(stop_jurisdiction)")}
    if not {"stop_id", *DIMENSIONS} <= columns:
        return [], ["current_geography_columns_missing"]
    groups = {}
    missing = {dimension: 0 for dimension in DIMENSIONS}
    for row in conn.execute("SELECT DISTINCT stop_id,state,county,municipality,dc_ward,dc_anc FROM stop_jurisdiction ORDER BY stop_id,state,county,municipality,dc_ward,dc_anc"):
        for dimension in DIMENSIONS:
            label = row[dimension]
            if not _text(label):
                missing[dimension] += 1
                continue
            if dimension == "dc_ward":
                label = canonical_dc_ward(label)
            # State/ward/ANC scopes must not fragment by overlapping counties.
            county_context = (row["county"] or "") if dimension == "municipality" else ""
            key = (dimension, row["state"] or "", county_context, label)
            groups.setdefault(key, set()).add(row["stop_id"])
    candidates = [{"dimension": key[0], "state": key[1], "county_context": key[2],
                   "label": key[3], "physical_stop_ids": sorted(ids), "certified": False}
                  for key, ids in sorted(groups.items())]
    return candidates, {"null_or_blank_rows_by_dimension": missing,
                        "note": "Missing ANC/ward outside DC need not be an error; labels are not historical identity."}


def build_geography_report(database, *, scope_snapshot, cutoff_utc,
                           sqlite_utc_provenance=None, reconciliation=None,
                           previous_report=None, thresholds=None):
    """Return canonical-serializable private evidence. Never asserts issuance readiness.

    Snapshot envelope: format, scopes, snapshot_sha256 (digest of other fields).
    Reconciliation, if supplied: reference and source_sha256 from a reviewed
    prior inspection. A hash/reference is not external certification proof.
    """
    cutoff = _utc(cutoff_utc)
    config = _thresholds(thresholds)
    if sqlite_utc_provenance is not None and not _text(sqlite_utc_provenance):
        raise ValueError("invalid_timestamp_provenance_reference")
    if reconciliation is not None and (not isinstance(reconciliation, dict)
            or set(reconciliation) != {"reference", "source_sha256"}
            or not _text(reconciliation["reference"]) or not _hash(reconciliation["source_sha256"])):
        raise ValueError("invalid_reconciliation")
    if previous_report is not None:
        if (not isinstance(previous_report, dict) or previous_report.get("format") != FORMAT
                or previous_report.get("report_sha256") != digest({k: v for k, v in previous_report.items() if k != "report_sha256"})):
            raise ValueError("invalid_previous_report")
    # Materialize supplied JSON without retaining mutable caller-owned objects.
    snapshot = json.loads(canonical(scope_snapshot))
    global_issues = []
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("scopes"), list):
        scopes = []
        global_issues.append("invalid_scope_snapshot")
    else:
        scopes = snapshot["scopes"]
        if snapshot.get("format") != "geography-scope-snapshot-v1":
            global_issues.append("unsupported_snapshot_format")
        if snapshot.get("snapshot_sha256") != digest({k: v for k, v in snapshot.items() if k != "snapshot_sha256"}):
            global_issues.append("snapshot_hash_mismatch")
    if not scopes:
        global_issues.append("no_explicit_scopes")
    qualified, uncaptured, exclusions, source = [], [], [], []
    with connection(database) as conn:
        if not conn.in_transaction:
            conn.execute("BEGIN")
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        owners = [r[0] for r in conn.execute("SELECT id FROM community_reviewers ORDER BY id")]
        physical_ids = {r[0] for r in conn.execute("SELECT id FROM physical_stops")}
        ledger = {r["assignment_id"]: dict(r) for r in conn.execute("SELECT * FROM recognition_completions ORDER BY assignment_id")} if "recognition_completions" in tables else {}
        if "recognition_completions" not in tables:
            global_issues.append("recognition_completions_missing")
        assignments = {r["id"]: dict(r) for r in conn.execute("SELECT id,stop_id,reviewer_id,status,completed_at FROM stop_review_assignments ORDER BY id")}
        for assignment_id in sorted(assignments.keys() | ledger.keys()):
            assignment, old = assignments.get(assignment_id), ledger.get(assignment_id)
            observations = [dict(r) for r in conn.execute("SELECT id,assignment_id,reviewer_id,physical_stop_id,source FROM stop_observations WHERE assignment_id=? AND source='community_review' ORDER BY id", (assignment_id,))]
            source.append({"assignment": assignment, "observations": observations, "ledger": old})
            try:
                provenance = sqlite_utc_provenance
                if old and isinstance(old.get("timestamp_provenance"), str):
                    prefix = "sqlite_current_timestamp_utc:"
                    if old["timestamp_provenance"].startswith(prefix):
                        provenance = old["timestamp_provenance"][len(prefix):]
                fact = qualify(conn, assignment_id, sqlite_utc_provenance=provenance)
                if old:
                    if any(old.get(k) != value for k, value in fact.items()):
                        raise Quarantined("source_ledger_discrepancy")
                    load_rule(conn, old["qualification_rule_key"])
                if fact["completed_at_utc"] >= cutoff:
                    raise Quarantined("at_or_after_cutoff")
                (qualified if old else uncaptured).append(fact)
            except ValueError as error:
                basis = assignment or {"stop_id": old["physical_stop_id"], "reviewer_id": old["reviewer_id"]}
                exclusions.append({"assignment_id": assignment_id, "physical_stop_id": basis["stop_id"],
                                   "reviewer_id": basis["reviewer_id"], "reason": str(error),
                                   "ledger_conflict": old is not None})
        orphans = [dict(r) for r in conn.execute("SELECT o.id,o.assignment_id,o.physical_stop_id,o.reviewer_id FROM stop_observations o LEFT JOIN stop_review_assignments a ON a.id=o.assignment_id WHERE o.source='community_review' AND a.id IS NULL ORDER BY o.id")]
        identities = {}
        for table in ("physical_stop_identity_edges", "physical_stop_identity_events", "physical_stop_identity_state"):
            identities[table] = sorted((dict(r) for r in conn.execute(f"SELECT * FROM {table}")), key=canonical) if table in tables else None
        discovered, discovery_quality = _discover(conn, tables)
    source_hash = digest({"source": source, "orphans": orphans})
    if reconciliation is None:
        global_issues.append("historical_reconciliation_missing")
    elif reconciliation["source_sha256"].lower() != source_hash:
        global_issues.append("historical_reconciliation_mismatch")
    if orphans:
        global_issues.append("orphan_community_evidence")
    if any(e["ledger_conflict"] and e["reason"] != "at_or_after_cutoff" for e in exclusions):
        # A changed source owner/stop must also block the original ledger owner,
        # not only the owner currently named by the mutated source assignment.
        global_issues.append("source_ledger_discrepancies_present")
    if any(value is None for value in identities.values()):
        global_issues.append("identity_history_incomplete")
    affected = {e[k] for e in identities["physical_stop_identity_edges"] or []
                for k in ("predecessor_physical_stop_id", "successor_physical_stop_id")}
    affected.update(s["physical_stop_id"] for s in identities["physical_stop_identity_state"] or []
                    if s["identity_status"] != "current")
    # Events without attributable edges cannot be silently ignored (e.g. movement).
    edge_events = {e["event_id"] for e in identities["physical_stop_identity_edges"] or []}
    if any(e["id"] not in edge_events for e in identities["physical_stop_identity_events"] or []):
        global_issues.append("unattributed_identity_event")
    changes = []
    if previous_report:
        for key, current in (("source_sha256", source_hash), ("identity_sha256", digest(identities)),
                             ("cutoff_utc", cutoff), ("thresholds", config)):
            if previous_report.get(key) != current:
                changes.append(key + "_changed")
        if previous_report.get("changes") or any(
                any(reason in ("scope_snapshot_changed", "membership_changed", "denominator_changed",
                               "denominator_shrank", "scope_added", "prior_changes_require_review")
                    for reason in s["quality_blockers"]) for s in previous_report["scopes"]):
            changes.append("prior_changes_require_review")
    results, scope_results, seen_keys, seen_identities = [], [], set(), set()
    for raw in sorted(scopes, key=canonical):
        scope, member_ids, issues = _scope(raw, cutoff)
        key = scope.get("scope_key")
        identity = canonical([scope.get("dimension"), scope.get("canonical_geography_id")])
        # Entire envelope is ambiguous if a scope or canonical identity occurs twice.
        key_token = canonical(key)
        if key_token in seen_keys or identity in seen_identities:
            global_issues.append("duplicate_scope_identity")
        seen_keys.add(key_token)
        seen_identities.add(identity)
        if set(member_ids) - physical_ids:
            issues.append("missing_physical_identity")
        if set(member_ids) & affected:
            issues.append("physical_identity_changed")
        denominator = len(member_ids)
        if previous_report:
            prior = next((s for s in previous_report["scopes"] if s["scope_key"] == key), None)
            if prior:
                if prior["snapshot_scope"] != scope:
                    issues.append("scope_snapshot_changed")
                if prior["member_physical_stop_ids"] != member_ids:
                    issues.append("membership_changed")
                if prior["D"] != denominator:
                    issues.append("denominator_changed")
                if prior["D"] > denominator:
                    issues.append("denominator_shrank")
            else:
                issues.append("scope_added")
        eligible = denominator >= config["minimum_population"]
        band = "small" if denominator < config["large_population"] else "large"
        tiers = [{"percentage": p, "required_count": max(config[band + "_minimum"], (denominator * p + 99) // 100)}
                 for p in config[band + "_percentages"]] if eligible else []
        scope_results.append({"scope_key": key, "snapshot_scope": scope, "D": denominator,
                              "member_physical_stop_ids": member_ids, "eligible": eligible,
                              "required_counts": tiers, "quality_blockers": sorted(set(issues))})
        for owner in owners:
            candidates = sorted((f for f in qualified if f["reviewer_id"] == owner and f["physical_stop_id"] in member_ids),
                                key=lambda f: (f["completed_at_utc"], f["assignment_id"]))
            witnesses = {}
            for fact in candidates:
                witnesses.setdefault(fact["physical_stop_id"], fact)
            pending = [f for f in uncaptured if f["reviewer_id"] == owner and f["physical_stop_id"] in member_ids]
            rejected = [e for e in exclusions if e["reviewer_id"] == owner and e["physical_stop_id"] in member_ids]
            blockers = list(issues)
            if pending:
                blockers.append("uncaptured_qualifying_evidence")
            if any(e["reason"] != "at_or_after_cutoff" and (e["ledger_conflict"] or e["reason"] != "assignment_not_completed") for e in rejected):
                blockers.append("rejected_completion_evidence")
            crossed = [t for t in tiers if len(witnesses) >= t["required_count"]]
            results.append({"reviewer_id": owner, "scope_key": key, "D": denominator, "N": len(witnesses),
                            "counted_physical_stop_ids": sorted(witnesses), "witnesses": list(witnesses.values()),
                            "required_counts": tiers, "candidate_tiers": crossed,
                            "uncaptured_evidence": pending, "exclusions": rejected,
                            "quality_blockers": blockers, "eligible": eligible})
    if previous_report:
        removed = set(canonical(s["scope_key"]) for s in previous_report["scopes"]) - seen_keys
        if removed:
            changes.append("scopes_removed")
    for scope in scope_results:
        scope["quality_blockers"] = sorted(set(scope["quality_blockers"] + global_issues + changes))
        scope["unresolved"] = bool(scope["quality_blockers"])
    for row in results:
        row["quality_blockers"] = sorted(set(row["quality_blockers"] + global_issues + changes))
        row["unresolved"] = bool(row["quality_blockers"])
        row["coverage_satisfied"] = None if row["unresolved"] else bool(row["candidate_tiers"])
        row["issuance_ready"] = False
        row["issuance_blockers"] = ["report_only_no_permanent_geography_support", "trigger_and_earned_date_policy_unapproved", "tier_identity_unapproved"]
    report = {"format": FORMAT, "family": "geography_steward", "cutoff_utc": cutoff, "cutoff_exclusive": True,
              "scope_snapshot": snapshot, "thresholds": config, "thresholds_sha256": digest(config),
              "uses_design_thresholds": config == DEFAULT_THRESHOLDS,
              "source": source, "source_sha256": source_hash, "identity_history": identities,
              "identity_sha256": digest(identities), "qualified_ledger_evidence": qualified,
              "uncaptured_evidence": uncaptured, "exclusions": exclusions, "orphan_observations": orphans,
              "discovered_current_scopes": discovered, "discovery_quality": discovery_quality,
              "reconciliation": reconciliation, "previous_report_sha256": previous_report["report_sha256"] if previous_report else None,
              "changes": sorted(changes), "quality_blockers": sorted(set(global_issues)),
              "scopes": scope_results, "reviewer_scopes": results,
              "unresolved": bool(global_issues or changes or any(r["unresolved"] for r in results) or any(s["unresolved"] for s in scope_results)),
              "issuance_ready": False,
              "limitations": ["Supplied certification/provenance references are assertions; hashes do not independently certify boundaries.",
                              "Current geography discovery is not historical membership and never supplies a denominator.",
                              "Coverage is evaluated against the supplied snapshot, never backdated to a review using current geography.",
                              "This report creates no awards, claims, captures or jobs and evaluates no existing award for removal."]}
    report = json.loads(canonical(report))
    report["report_sha256"] = digest(report)
    return report
