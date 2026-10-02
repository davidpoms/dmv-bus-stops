"""Private, bounded backfill planning; no command in this slice enables writes."""

from . import DISABLED
from .processing import bounded, ledger_candidates, materialize_ledger, record_run
from .qualification import Quarantined, capture, qualify
from .rules import digest, load_rule
from .schema import connection


def source_plan(conn, rule_key, *, through_assignment, after_assignment=0, limit=100,
               sqlite_utc_provenance=None):
    """Bounded source validation only; no candidate/history calculation.

    Caller holds a consistent transaction. Cutoff is assignment ID, not award
    time. This same validation is safe in the future bounded capture transaction.
    """
    bounded(limit)
    if not 0 <= after_assignment <= through_assignment:
        raise ValueError("invalid_cohort_bounds")
    rule = load_rule(conn, rule_key)
    rows = conn.execute("""SELECT id,stop_id,reviewer_id,status,completed_at FROM stop_review_assignments
        WHERE id>? AND id<=? ORDER BY id LIMIT ?""", (after_assignment, through_assignment, limit + 1)).fetchall()
    more = len(rows) > limit
    rows = rows[:limit]
    source, qualified, excluded = [], [], []
    for row in rows:
        observations = [dict(r) for r in conn.execute("""SELECT id,assignment_id,reviewer_id,physical_stop_id,source
            FROM stop_observations WHERE assignment_id=? AND source='community_review' ORDER BY id""", (row["id"],))]
        source.append({"assignment": dict(row), "community_observations": observations})
        try:
            fact = qualify(conn, row["id"], sqlite_utc_provenance=sqlite_utc_provenance)
            old = conn.execute("SELECT * FROM recognition_completions WHERE assignment_id=?", (row["id"],)).fetchone()
            if old and (any(old[k] != v for k, v in fact.items()) or old["qualification_rule_key"] != rule_key):
                raise Quarantined("immutable_completion_conflict")
            qualified.append(fact)
        except Quarantined as error:
            excluded.append({"assignment_id": row["id"], "reason": str(error),
                             "original_completed_at": row["completed_at"]})
    return {
        "format": "recognition-backfill-plan-v1", "algorithm": "global-explorer-foundation-v1",
        "rule_key": rule_key, "rule_sha256": digest(rule),
        "cohort": {"after_assignment": after_assignment, "through_assignment": through_assignment,
                   "limit": limit, "next_after_assignment": rows[-1]["id"] if rows else after_assignment,
                   "has_more": more},
        "sqlite_utc_provenance": sqlite_utc_provenance,
        "source_sha256": digest(source), "source": source,
        "qualified": qualified, "excluded": excluded,
    }


def plan_batch(plan, snapshot):
    """Finish candidate calculation only after the read connection is closed."""
    owners = {c["reviewer_id"] for c in plan["qualified"]}
    plan["candidate_basis"] = "existing_immutable_ledger_only"
    plan["candidates"] = ledger_candidates(snapshot, owners)
    return plan


def dry_run(database, rule_key, **cohort):
    with connection(database) as conn:
        conn.execute("BEGIN")
        plan = source_plan(conn, rule_key, **cohort)
        bounds = (plan["cohort"]["after_assignment"], plan["cohort"]["next_after_assignment"])
        snapshot = materialize_ledger(conn, rule_key, assignment_bounds=bounds)
    return plan_batch(plan, snapshot)


def capture_batch(database, manifest, *, gate=DISABLED):
    """Future explicit write boundary. Default returns before opening database.

    Requires the exact reviewed dry-run inputs still to match. Atomic per batch,
    restartable through manifest cursor, never repairs source evidence or awards.
    No CLI exposes this gate in Phase 2A.
    """
    if not gate.capture:
        return None
    cohort = manifest["cohort"]
    with connection(database, write=True) as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = source_plan(conn, manifest["rule_key"],
                             through_assignment=cohort["through_assignment"],
                             after_assignment=cohort["after_assignment"], limit=cohort["limit"],
                             sqlite_utc_provenance=manifest["sqlite_utc_provenance"])
        # Ledger candidates may have grown since a previous successful capture.
        # They are not source inputs and are never issued by this operation.
        source_keys = ("format", "algorithm", "rule_key", "rule_sha256", "cohort",
                       "sqlite_utc_provenance", "source_sha256", "source", "qualified", "excluded")
        if any(current[key] != manifest[key] for key in source_keys):
            raise Quarantined("backfill_input_changed")
        for fact in manifest["qualified"]:
            capture(conn, fact["assignment_id"], manifest["rule_key"], gate=gate, origin="backfill",
                    sqlite_utc_provenance=manifest["sqlite_utc_provenance"])
        run_id = record_run(conn, manifest, gate=gate)
        conn.commit()
        return run_id
