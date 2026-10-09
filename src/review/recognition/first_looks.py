"""Read-only historical First Look inspection; never seals claims or awards."""

from datetime import datetime
import json

from .qualification import Quarantined, permanent_time, qualify
from .rules import canonical, digest
from .report_connection import report_connection as connection


ORDERING = {"version": "first-look-report-v1",
            "keys": ["parsed_completed_at_utc", "numeric_assignment_id"],
            "qualification": "completed-single-matching-community-observation-v1"}


def _order(fact):
    return (datetime.fromisoformat(fact["completed_at_utc"].replace("Z", "+00:00")),
            fact["assignment_id"])


def build_report(database, *, cutoff_utc, sqlite_utc_provenance=None,
                 reconciliation=None, previous_report=None):
    """Scan ALL owners; cutoff is exclusive and must have an explicit offset.

    Optional reconciliation is a reviewed assertion, not proof manufactured by
    this function: reference, clock_review_reference, identity_review_reference,
    and expected_assignment_ids (every assignment present, including exclusions).
    Without it no winner is asserted. A prior report must be retained privately;
    its checksum detects accidental changes, not malicious replacement.
    """
    cutoff, _ = permanent_time(cutoff_utc)
    if sqlite_utc_provenance is not None and (
            not isinstance(sqlite_utc_provenance, str) or not sqlite_utc_provenance.strip()):
        raise ValueError("invalid_timestamp_provenance_reference")
    if reconciliation is not None:
        keys = {"reference", "clock_review_reference", "identity_review_reference", "expected_assignment_ids"}
        if (not isinstance(reconciliation, dict) or set(reconciliation) != keys
                or any(not isinstance(reconciliation[k], str) or not reconciliation[k].strip()
                       for k in keys - {"expected_assignment_ids"})
                or not isinstance(reconciliation["expected_assignment_ids"], list)
                or any(type(n) is not int for n in reconciliation["expected_assignment_ids"])
                or len(set(reconciliation["expected_assignment_ids"])) != len(reconciliation["expected_assignment_ids"])):
            raise ValueError("invalid_reconciliation")
    if previous_report is not None:
        body = {k: v for k, v in previous_report.items() if k != "report_sha256"}
        if (previous_report.get("report_sha256") != digest(body)
                or body.get("ordering") != ORDERING or body.get("cutoff_utc") != cutoff):
            raise ValueError("incompatible_previous_report")

    qualified, excluded, source, identity_edges, ledger_conflicts = [], [], [], [], set()
    with connection(database) as conn:
        if not conn.in_transaction:
            conn.execute("BEGIN")
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assignments = conn.execute("SELECT id,stop_id,reviewer_id,status,completed_at FROM stop_review_assignments ORDER BY id").fetchall()
        for row in assignments:
            observations = [dict(r) for r in conn.execute(
                "SELECT id,assignment_id,reviewer_id,physical_stop_id,source FROM stop_observations "
                "WHERE assignment_id=? AND source='community_review' ORDER BY id", (row["id"],))]
            source.append({"assignment": dict(row), "observations": observations})
            try:
                fact = qualify(conn, row["id"], sqlite_utc_provenance=sqlite_utc_provenance)
                if "recognition_completions" in tables:
                    old = conn.execute("SELECT * FROM recognition_completions WHERE assignment_id=?", (row["id"],)).fetchone()
                    if old and any(old[k] != fact[k] for k in fact):
                        ledger_conflicts.add(row["stop_id"])
                if fact["completed_at_utc"] >= cutoff:
                    raise Quarantined("at_or_after_cutoff")
                qualified.append(fact)
            except Quarantined as error:
                excluded.append({"assignment_id": row["id"], "physical_stop_id": row["stop_id"],
                                 "original_completed_at": row["completed_at"], "reason": str(error)})
        orphans = [dict(r) for r in conn.execute(
            "SELECT o.id,o.assignment_id,o.physical_stop_id FROM stop_observations o "
            "LEFT JOIN stop_review_assignments a ON a.id=o.assignment_id "
            "WHERE o.source='community_review' AND a.id IS NULL ORDER BY o.id")]
        if "physical_stop_identity_edges" in tables:
            identity_edges = [dict(r) for r in conn.execute(
                "SELECT * FROM physical_stop_identity_edges ORDER BY event_id,predecessor_physical_stop_id,successor_physical_stop_id")]
        identity_states = [dict(r) for r in conn.execute(
            "SELECT * FROM physical_stop_identity_state ORDER BY physical_stop_id")] if "physical_stop_identity_state" in tables else []
        identity_events = [dict(r) for r in conn.execute(
            "SELECT * FROM physical_stop_identity_events ORDER BY id")] if "physical_stop_identity_events" in tables else []

    reasons = []
    ids = [r["assignment"]["id"] for r in source]
    if reconciliation is None:
        reasons.extend(["historical_coverage_unreviewed", "clock_regressions_unreviewed", "identity_history_unreviewed"])
    elif sorted(reconciliation["expected_assignment_ids"]) != ids:
        reasons.append("historical_population_mismatch")
    if orphans:
        reasons.append("missing_assignment_competitors")
    changed_stops, late_stops = set(), set()
    prior_issues = {}
    if previous_report is not None:
        # Reporting again is not a resolution of a previously recorded anomaly.
        prior_issues = {s["physical_stop_id"]: [r for r in s["reasons"] if r in {
            "late_discovered_earlier_completion", "corrected_or_removed_evidence",
            "immutable_completion_conflict", "physical_identity_changed"}]
            for s in previous_report["stops"]}
        old_source = {s["assignment"]["id"]: s for s in previous_report["source"]}
        new_source = {s["assignment"]["id"]: s for s in source}
        for assignment in old_source.keys() | new_source.keys():
            old, new = old_source.get(assignment), new_source.get(assignment)
            if old is not None and old != new:
                changed_stops.add(old["assignment"]["stop_id"])
                if new:
                    changed_stops.add(new["assignment"]["stop_id"])
        old_candidates = {s["physical_stop_id"]: s["earliest_candidate"] for s in previous_report["stops"]}
        for fact in qualified:
            old = old_candidates.get(fact["physical_stop_id"])
            if fact["assignment_id"] not in old_source and old and _order(fact) < _order(old):
                late_stops.add(fact["physical_stop_id"])
    events = {e["id"]: e for e in identity_events}
    states = {s["physical_stop_id"]: s["identity_status"] for s in identity_states}
    affected, resolved_split_successors = set(), set()
    for edge in identity_edges:
        predecessor, successor = edge["predecessor_physical_stop_id"], edge["successor_physical_stop_id"]
        event = events.get(edge["event_id"], {})
        affected.add(predecessor)
        if (edge.get("relationship_type") == "split_successor"
                and event.get("event_type") == "split"
                and event.get("reason_code") == "facility_bay_split"
                and states.get(successor) == "current"):
            # Only direct evidence on this current successor is attributable.
            # This never copies predecessor facts or clears other lineage issues.
            resolved_split_successors.add(successor)
        else:
            affected.add(successor)
    affected.update(s["physical_stop_id"] for s in identity_states if s["identity_status"] != "current")
    resolved_split_successors.difference_update(affected)
    stops = []
    stop_ids = {f["physical_stop_id"] for f in qualified} | {e["physical_stop_id"] for e in excluded} | changed_stops
    for stop in sorted(stop_ids, key=lambda n: (n is None, n or 0)):
        facts = sorted((f for f in qualified if f["physical_stop_id"] == stop), key=_order)
        rejections = [e for e in excluded if e["physical_stop_id"] == stop]
        issues = list(reasons) + prior_issues.get(stop, [])
        if any(e["reason"] not in ("assignment_not_completed", "at_or_after_cutoff") for e in rejections):
            issues.append("rejected_competitor_requires_review")
        for population, code in ((affected, "physical_identity_changed"), (changed_stops, "corrected_or_removed_evidence"),
                                 (late_stops, "late_discovered_earlier_completion"), (ledger_conflicts, "immutable_completion_conflict")):
            if stop in population:
                issues.append(code)
        candidate = facts[0] if facts else None
        stops.append({"physical_stop_id": stop, "earliest_candidate": candidate,
                      "provisional_winner": candidate if candidate and not issues else None,
                      "qualifying_completions": facts, "excluded": rejections,
                      "status": "requires_adjudication" if issues else "complete_projection",
                      "reasons": sorted(set(issues))})
    report = {"format": "first-look-adjudication-report-v1", "ordering": ORDERING,
              "cutoff_utc": cutoff, "cutoff_exclusive": True, "snapshot_scan_complete": True,
              "permanent_claims_created": False, "reconciliation": reconciliation,
              "previous_report_sha256": previous_report["report_sha256"] if previous_report else None,
              "status": "requires_adjudication" if reasons or any(s["reasons"] for s in stops) else "complete_projection",
              "reasons": sorted(reasons), "source": source, "qualified": sorted(qualified, key=_order),
              "excluded": excluded, "orphan_observations": orphans, "identity_edges": identity_edges,
              "identity_states": identity_states, "identity_events": identity_events,
              "resolved_split_successors": sorted(resolved_split_successors), "stops": stops,
              "limitations": ["Review references are operator assertions, not independently verified attestations.",
                              "Absent history and unrecorded clock regressions cannot be inferred from this copy.",
                              "Without a retained prior report, late discovery and source corrections may be undetectable.",
                              "Observation time, progress and submission first_review are not winner evidence.",
                              "A complete projection is not authorization to seal a permanent claim."]}
    # Normalize caller-owned input and guarantee the report is JSON serializable.
    report = json.loads(canonical(report))
    report["report_sha256"] = digest(report)
    return report
