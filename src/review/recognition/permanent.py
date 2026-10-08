"""Controlled historical sealing, separate from Explorer and automatic review flows.

Preparation is read-only. Finalization defaults off, owns one atomic transaction,
and re-prepares the complete reviewed population under BEGIN IMMEDIATE.
"""

import json
from datetime import datetime, timezone

from . import RecognitionGate
from .first_looks import build_report
from .geography import DEFAULT_THRESHOLDS, _utc, build_geography_report
from .permanent_schema import check_schema
from .qualification import Quarantined, require_transaction
from .rules import canonical, digest, load_rule
from .schema import connection


DEFINITIONS = {
    "first_look": {"rule_key": "first_look:v1", "family": "first_look",
                   "ordering": ["completed_at_utc", "numeric_assignment_id"],
                   "qualification": "completed-single-matching-community-observation-v1",
                   "claim": "one-per-physical-stop", "identity_transfer": False,
                   "mode": "reviewed-historical-sealing", "late_discoveries": "append-only-discrepancy"},
    "geography_steward": {"rule_key": "geography_steward:v1", "family": "geography_steward",
                          "thresholds": DEFAULT_THRESHOLDS,
                          "tiers": ["tier_1", "tier_2", "tier_3", "tier_4"],
                          "mode": "one-time-present-day-catch-up",
                          "earned_at": "explicit-evaluation-instant",
                          "active": "stop_gtfs_status.current_gtfs = 1"},
}


def require(condition, code):
    if not condition:
        raise Quarantined(code)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def _identity(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    names = ("physical_stop_identity_events", "physical_stop_identity_edges", "physical_stop_identity_state")
    require(set(names) <= tables, "identity_history_incomplete")
    result = {name: sorted([dict(r) for r in conn.execute(f"SELECT * FROM {name}")], key=canonical)
              for name in names}
    linked = {r["event_id"] for r in result[names[1]]}
    require(all(r["id"] in linked for r in result[names[0]]), "unattributed_identity_event")
    return result


def _ledger(conn):
    rows = [dict(r) for r in conn.execute("SELECT * FROM recognition_completions ORDER BY assignment_id")]
    for key in sorted({r["qualification_rule_key"] for r in rows}):
        load_rule(conn, key)
    return rows


def _candidates(family, report, evaluation):
    """Use report mathematics; no progress calculation or new qualifier."""
    result = []
    if family == "first_look":
        require(not report["reasons"], "historical_population_unreviewed")
        for stop in report["stops"]:
            winner = stop["provisional_winner"]
            if winner is not None:
                require(not stop["reasons"], "unresolved_first_look")
                facts = sorted(stop["qualifying_completions"], key=lambda f: (f["completed_at_utc"], f["assignment_id"]))
                require(bool(facts) and winner == facts[0] and all(
                    f["physical_stop_id"] == stop["physical_stop_id"] and
                    f["completed_at_utc"] < report["cutoff_utc"] for f in facts), "first_look_ordering_mismatch")
                result.append({"family": family, **winner})
    else:
        require(report["uses_design_thresholds"], "unapproved_thresholds")
        require(not report["unresolved"], "unresolved_geography")
        scopes = {s["scope_key"]: s for s in report["scopes"]}
        for row in report["reviewer_scopes"]:
            scope_result = scopes[row["scope_key"]]
            members = scope_result["member_physical_stop_ids"]
            expected = {}
            for fact in sorted(report["qualified_ledger_evidence"], key=lambda f: (f["completed_at_utc"], f["assignment_id"])):
                if fact["reviewer_id"] == row["reviewer_id"] and fact["physical_stop_id"] in members:
                    expected.setdefault(fact["physical_stop_id"], fact)
            require(row["witnesses"] == list(expected.values()) and row["N"] == len(expected) and
                    row["D"] == len(members), "geography_arithmetic_mismatch")
            band = "small" if row["D"] < 100 else "large"
            tiers = [{"percentage": p, "required_count": max(DEFAULT_THRESHOLDS[band + "_minimum"], (row["D"] * p + 99) // 100)}
                     for p in DEFAULT_THRESHOLDS[band + "_percentages"]] if row["D"] >= 10 else []
            require(row["required_counts"] == tiers and row["candidate_tiers"] == [t for t in tiers if row["N"] >= t["required_count"]],
                    "geography_tier_math_mismatch")
            for index, tier in enumerate(row["required_counts"], 1):
                if tier not in row["candidate_tiers"]:
                    continue
                scope = scopes[row["scope_key"]]["snapshot_scope"]
                result.append({"family": family, "reviewer_id": row["reviewer_id"],
                               "scope_key": row["scope_key"], "tier_key": f"tier_{index}",
                               "snapshot_id": digest(scope), "earned_at_utc": evaluation,
                               "numerator": row["N"], "denominator": row["D"],
                               "size_band": "small" if row["D"] < 100 else "large",
                               "percentage": tier["percentage"], "required_count": tier["required_count"],
                               "witnesses": row["witnesses"]})
    return sorted(result, key=canonical)


def _prepare(conn, family, inputs, evaluation, authorization_reference):
    require(family in DEFINITIONS, "unsupported_permanent_family")
    require(text(authorization_reference), "authorization_reference_required")
    _utc(evaluation)
    require(_utc(inputs["cutoff_utc"]) <= evaluation, "evaluation_before_cutoff")
    require(isinstance(inputs.get("reconciliation"), dict), "reviewed_reconciliation_required")
    identity = _identity(conn)
    ledger = _ledger(conn)
    if family == "first_look":
        report = build_report(conn, **inputs)
        # All qualifying competitors, not merely proposed winners, must have
        # immutable evidence. This service never captures missing completions.
        by_id = {r["assignment_id"]: r for r in ledger}
        for fact in report["qualified"]:
            require(fact["assignment_id"] in by_id and all(
                by_id[fact["assignment_id"]][k] == v for k, v in fact.items()),
                "competitor_completion_not_captured")
    else:
        require(inputs["cutoff_utc"] == evaluation, "catch_up_requires_evaluation_cutoff")
        require("thresholds" not in inputs, "unapproved_threshold_override")
        report = build_geography_report(conn, **inputs)
        for item in report["scopes"]:
            scope = item["snapshot_scope"]
            require(text(scope.get("display_label")), "scope_display_label_required")
            require(text(scope.get("identity_review_reference")), "scope_identity_review_required")
            require(isinstance(scope.get("quality_findings"), list) and not scope["quality_findings"],
                    "unresolved_scope_quality")
            require(scope["certification"].get("independent") is True, "independent_certification_required")
            members = scope["members"]
            require(len(members) == len(item["member_physical_stop_ids"]), "exact_active_members_required")
            for member in members:
                rows = conn.execute("SELECT current_gtfs FROM stop_gtfs_status WHERE physical_stop_id=?",
                                    (member["physical_stop_id"],)).fetchall()
                require(len(rows) == 1 and rows[0][0] == 1, "current_active_membership_changed")
    candidates = _candidates(family, report, evaluation)
    manifest = {"format": "private-recognition-operation-v1", "family": family,
                "rule": DEFINITIONS[family], "rule_sha256": digest(DEFINITIONS[family]),
                "inputs": inputs, "evaluation_at_utc": evaluation,
                "authorization_reference": authorization_reference,
                "report": report, "identity_history": identity, "ledger": ledger,
                "candidates": candidates}
    return json.loads(canonical(manifest))


def prepare(database, *, family, inputs, evaluation_at_utc, authorization_reference):
    """Return an unapproved private manifest for independent review; no writes."""
    inputs = json.loads(canonical(inputs))
    with connection(database) as conn:
        conn.execute("BEGIN")
        return _prepare(conn, family, inputs, evaluation_at_utc, authorization_reference)


def _validate_manifest(manifest):
    if manifest.get("format") == "live-first-look-operation-v1":
        from .live_first_looks import validate_operation_manifest
        validate_operation_manifest(manifest)
        return
    require(manifest.get("format") == "private-recognition-operation-v1", "invalid_manifest")
    family = manifest.get("family")
    require(family in DEFINITIONS and manifest["rule"] == DEFINITIONS[family] and
            manifest["rule_sha256"] == digest(DEFINITIONS[family]), "rule_mismatch")
    report = manifest["report"]
    require(report["report_sha256"] == digest({k: v for k, v in report.items() if k != "report_sha256"}),
            "report_hash_mismatch")
    require(manifest["candidates"] == _candidates(family, report, manifest["evaluation_at_utc"]),
            "candidate_mismatch")


def _operation(conn, operation_id):
    row = conn.execute("SELECT * FROM recognition_private_operations WHERE operation_id=?", (operation_id,)).fetchone()
    require(row is not None, "missing_operation")
    manifest = json.loads(row["manifest_json"])
    require(row["manifest_json"] == canonical(manifest) and
            digest(manifest) == operation_id == row["manifest_sha256"], "operation_hash_mismatch")
    _validate_manifest(manifest)
    require(row["authorization_reference"] == manifest["authorization_reference"] and
            row["rule_key"] == manifest["rule"]["rule_key"], "operation_context_mismatch")
    _utc(row["sealed_at_utc"])
    rule = conn.execute("SELECT * FROM recognition_private_rules WHERE rule_key=?", (row["rule_key"],)).fetchone()
    require(rule is not None and rule["family"] == manifest["family"] and
            rule["definition_json"] == canonical(manifest["rule"]) and
            rule["definition_sha256"] == manifest["rule_sha256"], "stored_rule_mismatch")
    return manifest


def _check_facts(conn, facts):
    for fact in facts:
        row = conn.execute("SELECT * FROM recognition_completions WHERE assignment_id=?", (fact["assignment_id"],)).fetchone()
        require(row is not None and all(row[k] == v for k, v in fact.items() if k != "family"),
                "immutable_witness_mismatch")
        load_rule(conn, row["qualification_rule_key"])


def check_claim_integrity(conn, physical_stop_id):
    row = conn.execute("SELECT * FROM recognition_first_look_claims WHERE physical_stop_id=?", (physical_stop_id,)).fetchone()
    require(row is not None, "missing_first_look_claim")
    manifest = _operation(conn, row["operation_id"])
    require(manifest["family"] == "first_look", "claim_family_mismatch")
    candidates = [c for c in manifest["candidates"] if c["physical_stop_id"] == physical_stop_id]
    require(len(candidates) == 1, "claim_candidate_missing")
    fact = candidates[0]
    require(row["evidence_json"] == canonical(fact) and row["evidence_sha256"] == digest(fact) and
            row["reviewer_id"] == fact["reviewer_id"] and row["assignment_id"] == fact["assignment_id"] and
            row["earned_at_utc"] == fact["completed_at_utc"], "claim_evidence_mismatch")
    competitors = next(s for s in manifest["report"]["stops"] if s["physical_stop_id"] == physical_stop_id)
    _check_facts(conn, competitors["qualifying_completions"])
    return fact


def check_geography_integrity(conn, award_id):
    row = conn.execute("SELECT * FROM recognition_geography_awards WHERE award_id=?", (award_id,)).fetchone()
    require(row is not None, "missing_geography_award")
    manifest = _operation(conn, row["operation_id"])
    require(manifest["family"] == "geography_steward", "award_family_mismatch")
    candidates = [c for c in manifest["candidates"] if digest(c) == award_id]
    require(len(candidates) == 1, "award_candidate_missing")
    candidate = candidates[0]
    require(row["evidence_json"] == canonical(candidate) and row["evidence_sha256"] == digest(candidate),
            "geography_evidence_mismatch")
    for key in ("reviewer_id", "scope_key", "tier_key", "snapshot_id", "earned_at_utc",
                "numerator", "denominator", "percentage", "size_band"):
        require(row[key] == candidate[key], "geography_context_mismatch")
    snapshot = conn.execute("SELECT * FROM recognition_geography_snapshots WHERE snapshot_id=?", (row["snapshot_id"],)).fetchone()
    require(snapshot is not None and snapshot["operation_id"] == row["operation_id"] and
            snapshot["scope_key"] == row["scope_key"], "snapshot_context_mismatch")
    scope = json.loads(snapshot["scope_json"])
    require(snapshot["scope_json"] == canonical(scope) and digest(scope) == snapshot["scope_sha256"] == row["snapshot_id"],
            "snapshot_hash_mismatch")
    require(scope in manifest["inputs"]["scope_snapshot"]["scopes"], "snapshot_manifest_mismatch")
    identity = conn.execute("SELECT * FROM recognition_geography_scope_identities WHERE scope_key=?", (row["scope_key"],)).fetchone()
    require(identity is not None and all(identity[k] == scope[k] for k in identity.keys()), "scope_identity_mismatch")
    members = [r[0] for r in conn.execute("SELECT physical_stop_id FROM recognition_geography_members WHERE snapshot_id=? ORDER BY physical_stop_id", (row["snapshot_id"],))]
    require(members == sorted(m["physical_stop_id"] for m in scope["members"]) and len(members) == row["denominator"],
            "snapshot_members_mismatch")
    witnesses = candidate["witnesses"]
    actual = [r[0] for r in conn.execute("SELECT assignment_id FROM recognition_geography_witnesses WHERE award_id=? ORDER BY assignment_id", (award_id,))]
    require(actual == sorted(f["assignment_id"] for f in witnesses), "geography_witness_set_mismatch")
    require(len({f["physical_stop_id"] for f in witnesses}) == row["numerator"] and
            all(f["physical_stop_id"] in members and f["reviewer_id"] == row["reviewer_id"] for f in witnesses),
            "geography_witness_identity_mismatch")
    _check_facts(conn, witnesses)
    return candidate


def _insert_operation(conn, manifest):
    """Shared immutable operation storage; caller owns transaction/authorization."""
    require_transaction(conn)
    _validate_manifest(manifest)
    rule = manifest["rule"]
    old = conn.execute("SELECT * FROM recognition_private_rules WHERE rule_key=?", (rule["rule_key"],)).fetchone()
    if old:
        require(old["definition_json"] == canonical(rule) and old["definition_sha256"] == digest(rule), "stored_rule_mismatch")
    else:
        conn.execute("INSERT INTO recognition_private_rules VALUES(?,?,?,?)",
                     (rule["rule_key"], manifest["family"], canonical(rule), digest(rule)))
    sealed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    require(sealed_at >= manifest["evaluation_at_utc"], "future_evaluation_not_authorized")
    operation_id = digest(manifest)
    conn.execute("INSERT INTO recognition_private_operations VALUES(?,?,?,?,?,?)",
                 (operation_id, rule["rule_key"], canonical(manifest), operation_id,
                  manifest["authorization_reference"], sealed_at))
    return operation_id


def _insert_first_look_claim(conn, candidate, operation_id):
    """Shared uniqueness-protected claim insert, never opens/commits a connection."""
    require_transaction(conn)
    require(conn.execute("SELECT 1 FROM recognition_first_look_claims WHERE physical_stop_id=?",
                         (candidate["physical_stop_id"],)).fetchone() is None, "existing_claim_requires_discrepancy")
    conn.execute("INSERT INTO recognition_first_look_claims VALUES(?,?,?,?,?,?,?)",
                 (candidate["physical_stop_id"], candidate["reviewer_id"], candidate["assignment_id"],
                  operation_id, candidate["completed_at_utc"], canonical(candidate), digest(candidate)))


def finalize(database, manifest, *, manifest_sha256, authorization_reference=None,
             gate=RecognitionGate()):
    """Explicit one-operation transaction. No leasing, Explorer writes or capture."""
    if not gate.issuance:
        return {"issued": False, "reason": "issuance_disabled"}
    require(not gate.capture, "capture_must_remain_disabled")
    manifest = json.loads(canonical(manifest))
    require(manifest.get("format") == "private-recognition-operation-v1", "historical_manifest_required")
    operation_id = digest(manifest)
    require(operation_id == manifest_sha256, "manifest_hash_mismatch")
    require(text(authorization_reference) and authorization_reference == manifest["authorization_reference"],
            "explicit_authorization_required")
    _validate_manifest(manifest)
    with connection(database, write=True) as conn:
        conn.execute("BEGIN IMMEDIATE")
        check_schema(conn)
        existing = conn.execute("SELECT 1 FROM recognition_private_operations WHERE operation_id=?", (operation_id,)).fetchone()
        if existing:
            _verify_operation_records(conn, operation_id)
            return {"issued": False, "idempotent": True, "operation_id": operation_id,
                    "records": len(manifest["candidates"])}
        # Every qualifier, competitor, identity event, member and candidate is
        # regenerated inside the lock, before any new-family write.
        fresh = _prepare(conn, manifest["family"], manifest["inputs"], manifest["evaluation_at_utc"], authorization_reference)
        require(fresh == manifest, "reviewed_source_changed")
        _insert_operation(conn, manifest)
        if manifest["family"] == "first_look":
            for candidate in manifest["candidates"]:
                _insert_first_look_claim(conn, candidate, operation_id)
        else:
            for item in manifest["report"]["scopes"]:
                scope = item["snapshot_scope"]
                # Initial launch is one catch-up per scope. A later snapshot or
                # denominator shrink needs a new reviewed implementation/policy.
                require(conn.execute("SELECT 1 FROM recognition_geography_scope_identities WHERE scope_key=?",
                                     (scope["scope_key"],)).fetchone() is None, "scope_catch_up_already_sealed")
                conn.execute("INSERT INTO recognition_geography_scope_identities VALUES(?,?,?,?)",
                             tuple(scope[k] for k in ("scope_key", "dimension", "canonical_geography_id", "display_label")))
                conn.execute("INSERT INTO recognition_geography_snapshots VALUES(?,?,?,?,?)",
                             (digest(scope), scope["scope_key"], operation_id, canonical(scope), digest(scope)))
                conn.executemany("INSERT INTO recognition_geography_members VALUES(?,?)",
                                 [(digest(scope), n) for n in item["member_physical_stop_ids"]])
            for candidate in manifest["candidates"]:
                conn.execute("INSERT INTO recognition_geography_awards VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (digest(candidate), candidate["reviewer_id"], candidate["scope_key"], candidate["tier_key"],
                              candidate["snapshot_id"], operation_id, candidate["earned_at_utc"], candidate["numerator"],
                              candidate["denominator"], candidate["percentage"], candidate["size_band"], canonical(candidate), digest(candidate)))
                conn.executemany("INSERT INTO recognition_geography_witnesses VALUES(?,?)",
                                 [(digest(candidate), f["assignment_id"]) for f in candidate["witnesses"]])
        _verify_operation_records(conn, operation_id)
        require(conn.execute("PRAGMA foreign_key_check").fetchone() is None, "foreign_key_check_failed")
        conn.commit()
    return {"issued": True, "operation_id": operation_id, "records": len(manifest["candidates"])}


def _verify_operation_records(conn, operation_id):
    manifest = _operation(conn, operation_id)
    if manifest["family"] == "first_look":
        actual = [r[0] for r in conn.execute("SELECT physical_stop_id FROM recognition_first_look_claims WHERE operation_id=? ORDER BY physical_stop_id", (operation_id,))]
        require(actual == sorted(c["physical_stop_id"] for c in manifest["candidates"]), "operation_claim_set_mismatch")
        for stop in actual:
            check_claim_integrity(conn, stop)
    else:
        snapshots = [dict(r) for r in conn.execute("SELECT * FROM recognition_geography_snapshots WHERE operation_id=? ORDER BY snapshot_id", (operation_id,))]
        scopes = manifest["inputs"]["scope_snapshot"]["scopes"]
        require([r["snapshot_id"] for r in snapshots] == sorted(digest(s) for s in scopes), "operation_snapshot_set_mismatch")
        for snapshot in snapshots:
            scope = next(s for s in scopes if digest(s) == snapshot["snapshot_id"])
            require(snapshot["scope_json"] == canonical(scope) and snapshot["scope_sha256"] == digest(scope) and
                    snapshot["scope_key"] == scope["scope_key"], "operation_snapshot_mismatch")
            members = [r[0] for r in conn.execute("SELECT physical_stop_id FROM recognition_geography_members WHERE snapshot_id=? ORDER BY physical_stop_id", (snapshot["snapshot_id"],))]
            require(members == sorted(m["physical_stop_id"] for m in scope["members"]), "snapshot_members_mismatch")
            identity = conn.execute("SELECT * FROM recognition_geography_scope_identities WHERE scope_key=?", (scope["scope_key"],)).fetchone()
            require(identity is not None and all(identity[k] == scope[k] for k in identity.keys()), "scope_identity_mismatch")
        actual = [r[0] for r in conn.execute("SELECT award_id FROM recognition_geography_awards WHERE operation_id=? ORDER BY award_id", (operation_id,))]
        require(actual == sorted(digest(c) for c in manifest["candidates"]), "operation_award_set_mismatch")
        for award in actual:
            check_geography_integrity(conn, award)


def append_discrepancy(database, *, physical_stop_id, evidence, review_reference,
                       reviewed_at_utc, gate=RecognitionGate()):
    if not gate.issuance:
        return {"recorded": False, "reason": "issuance_disabled"}
    require(not gate.capture and text(review_reference), "discrepancy_authorization_required")
    _utc(reviewed_at_utc)
    require(isinstance(evidence, dict) and text(evidence.get("reason")), "discrepancy_evidence_required")
    body = {"physical_stop_id": physical_stop_id, "evidence": evidence,
            "review_reference": review_reference, "reviewed_at_utc": reviewed_at_utc}
    key = digest(body)
    with connection(database, write=True) as conn:
        conn.execute("BEGIN IMMEDIATE")
        check_schema(conn)
        check_claim_integrity(conn, physical_stop_id)
        old = conn.execute("SELECT * FROM recognition_first_look_discrepancies WHERE discrepancy_id=?", (key,)).fetchone()
        if old is None:
            conn.execute("INSERT INTO recognition_first_look_discrepancies VALUES(?,?,?,?,?,?)",
                         (key, physical_stop_id, reviewed_at_utc, review_reference, canonical(body), key))
        else:
            require(old["evidence_json"] == canonical(body) and old["evidence_sha256"] == key,
                    "discrepancy_hash_mismatch")
        conn.commit()
    return {"recorded": True, "discrepancy_id": key}
