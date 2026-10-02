"""One reviewed 55-completion/four-award cohort; verification-only by default."""

import argparse
import json
import socket
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.active.rehearse_recognition_capture import (
    fingerprint_value, check_schema, file_hash, offline_file, read_manifest, require,
)
from src.review.recognition import RecognitionGate
from src.review.recognition.backfill import source_plan
from src.review.recognition.integrity import check_award_integrity
from src.review.recognition.processing import lease_jobs, prepare_evaluation, finalize_job
from src.review.recognition.rules import RULE_KEY, canonical, digest
from src.review.recognition.schema import connection

# Provisioned in a separate operator review. No CLI or environment override.
# Intentionally absent from the checkout until a real target has been reviewed.
BINDING_PATH = ROOT / "ops" / "recognition-production-binding.json"


def target_binding(target, manifest_sha256, source_sha256):
    binding = json.loads(BINDING_PATH.read_text(encoding="utf-8"))
    require(isinstance(binding, dict) and set(binding) == {"environment", "hostname", "database", "device", "inode",
                             "manifest_sha256", "snapshot_sha256", "review_reference"}, "invalid_target_binding")
    require(all(isinstance(binding[k], str) and binding[k].strip() for k in
                ("environment", "hostname", "database", "manifest_sha256", "snapshot_sha256", "review_reference"))
            and type(binding["device"]) is int and type(binding["inode"]) is int, "invalid_target_binding")
    stat = target.stat()
    require(binding["environment"] == "production" and binding["hostname"] == socket.getfqdn()
            and Path(binding["database"]).is_absolute()
            and str(target) == binding["database"]
            and stat.st_dev == binding["device"] and stat.st_ino == binding["inode"]
            and stat.st_ino != 0 and bool(binding["review_reference"])
            and target.name.lower() != "recognition-working.db", "unauthorized_production_target")
    require(binding["manifest_sha256"] == manifest_sha256.lower(), "binding_manifest_hash_mismatch")
    require(binding["snapshot_sha256"] == source_sha256.lower(), "binding_source_hash_mismatch")
    return binding


def announce(event, binding, **details):
    print(canonical(dict(event=event, target=binding["database"], environment=binding["environment"],
                         hostname=binding["hostname"], **details)), file=sys.stderr, flush=True)


def cohort_fingerprint(conn, manifest):
    """Pin complete historical rows, never unrelated application tables/rows."""
    ids = [item["assignment"]["id"] for item in manifest["source"]]
    result = {}

    def rows(table, column, values):
        values = sorted(set(v for v in values if v is not None))
        placeholders = ",".join("?" for _ in values)
        found = list(conn.execute(f"SELECT * FROM {table} WHERE {column} IN ({placeholders}) ORDER BY id LIMIT 1001", values))
        require(len(found) <= 1000, "historical_record_limit")
        result[table] = digest([{key: fingerprint_value(row[key]) for key in row.keys()} for row in found])
        return found

    assignments = rows("stop_review_assignments", "id", ids)
    observations = rows("stop_observations", "assignment_id", ids)
    rows("community_reviewers", "id", [r["reviewer_id"] for r in assignments] +
         [r["reviewer_id"] for r in observations])
    rows("physical_stops", "id", [r["stop_id"] for r in assignments] +
         [r["physical_stop_id"] for r in observations])
    return result


def schema_identity(conn):
    return tuple(tuple(r) for r in conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"))


def full_checks(conn):
    check_schema(conn, additional_written_tables={"recognition_awards", "recognition_award_witnesses"})
    require([r[0] for r in conn.execute("PRAGMA integrity_check")] == ["ok"], "integrity_check_failed")


def validate_state(conn, manifest):
    """Bounded source/evidence checks, including exact retry state, before writes."""
    cohort = manifest["cohort"]
    current = source_plan(conn, RULE_KEY, after_assignment=141, through_assignment=210,
                          limit=cohort["limit"], sqlite_utc_provenance=manifest["sqlite_utc_provenance"])
    require(all(current[k] == manifest[k] for k in current), "reviewed_manifest_mismatch")
    completions = list(conn.execute("SELECT * FROM recognition_completions ORDER BY ledger_sequence LIMIT 56"))
    require(len(completions) == 55, "unexpected_completion_set")
    for sequence, (row, fact) in enumerate(zip(completions, manifest["qualified"]), 1):
        require(all(row[k] == v for k, v in fact.items()) and row["ledger_sequence"] == sequence
                and row["qualification_rule_key"] == RULE_KEY and row["origin"] == "backfill",
                "completion_evidence_mismatch")
    runs = list(conn.execute("SELECT * FROM recognition_runs LIMIT 2"))
    capture_manifest = dict(manifest, candidates=[])
    require(len(runs) == 1 and runs[0]["kind"] == "backfill" and runs[0]["state"] == "complete"
            and runs[0]["finished_at_utc"] is not None
            and runs[0]["manifest_json"] == canonical(capture_manifest)
            and runs[0]["manifest_sha256"] == digest(capture_manifest)
            and runs[0]["run_id"] == digest(capture_manifest), "capture_manifest_mismatch")
    jobs = [dict(r) for r in conn.execute("SELECT * FROM recognition_jobs ORDER BY assignment_id LIMIT 56")]
    require([j["assignment_id"] for j in jobs] == [f["assignment_id"] for f in manifest["qualified"]],
            "unexpected_job_set")
    for job in jobs:
        require(job["rule_key"] == RULE_KEY and job["state"] in ("pending", "done")
                and job["attempts"] == (1 if job["state"] == "done" else 0)
                and job["lease_token"] is None and job["lease_until_utc"] is None
                and job["last_error_code"] is None, "unexpected_job_state")
    # Awards must correspond exactly to owners whose jobs this operation completed.
    done_owners = {f["reviewer_id"] for f, j in zip(manifest["qualified"], jobs) if j["state"] == "done"}
    expected = {digest(tuple(c[k] for k in ("reviewer_id", "family", "scope_key", "tier_key"))): c
                for c in manifest["candidates"] if c["reviewer_id"] in done_owners}
    awards = [dict(r) for r in conn.execute("SELECT * FROM recognition_awards ORDER BY award_id LIMIT 5")]
    require({a["award_id"] for a in awards} == set(expected), "unexpected_award_set")
    for award in awards:
        candidate = expected[award["award_id"]]
        require(all(award[k] == candidate[k] for k in candidate if k != "evidence")
                and award["origin"] == "backfill"
                and award["evidence_json"] == canonical(candidate["evidence"]), "award_evidence_mismatch")
        check_award_integrity(conn, award["award_id"])
        award["witness_count"] = conn.execute(
            "SELECT COUNT(*) FROM recognition_award_witnesses WHERE award_id=?", (award["award_id"],)).fetchone()[0]
    return jobs, awards


def issue(production_db, source_snapshot, manifest_path, *, manifest_sha256, source_sha256,
          expected_excluded, issue_production=False, recover_production=False):
    require(not (issue_production and recover_production), "recovery_cannot_issue")
    source = offline_file(source_snapshot)
    target = Path(production_db).resolve(strict=True)
    require(not source.samefile(target), "source_target_alias")
    binding = target_binding(target, manifest_sha256, source_sha256)
    announce("target-verification", binding)
    require(file_hash(source) == source_sha256.lower(), "source_hash_mismatch")
    manifest = read_manifest(manifest_path, manifest_sha256, 55, expected_excluded, expected_candidates=4)
    require(manifest["cohort"]["after_assignment"] == 141
            and manifest["cohort"]["through_assignment"] == 210, "historical_cohort_required")
    if recover_production:
        require(not any(Path(str(target) + suffix).exists() for suffix in ("-wal", "-shm")),
                "wal_recovery_not_supported")
        with target.open("rb") as stream:
            header = stream.read(20)
        require(header[:16] == b"SQLite format 3\x00" and header[18:20] == b"\x01\x01",
                "rollback_journal_database_required")
        announce("recovery-authorization-boundary", binding)
        require(target_binding(target, manifest_sha256, source_sha256) == binding, "target_binding_changed")
        # Explicit recovery-only write permission; SQLite owns journal recovery.
        # No DML, migration, manual journal removal, capture, lease or issuance.
        with connection(target, write=True) as conn:
            conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
        # Close recovery connection before fresh, read-only checks below.
    offline_file(target)
    with connection(source) as conn:
        conn.execute("BEGIN")
        source_data = cohort_fingerprint(conn, manifest)
    with connection(target) as conn:
        conn.execute("BEGIN")
        full_checks(conn)
        schema = schema_identity(conn)
        jobs, before = validate_state(conn, manifest)
        require(cohort_fingerprint(conn, manifest) == source_data, "historical_cohort_changed")
    owners = sorted({f["reviewer_id"] for f in manifest["qualified"]})
    prepared = {owner: prepare_evaluation(target, owner, RULE_KEY) for owner in owners}
    actual = [c for owner in owners for c in json.loads(prepared[owner].candidates_json)]
    require(canonical(actual) == canonical(manifest["candidates"]), "unexpected_candidate_set")
    gate = RecognitionGate(capture=False, issuance=issue_production)
    if issue_production:
        announce("issuance-authorization-boundary", binding, manifest_sha256=manifest_sha256,
                 snapshot_sha256=source_sha256, expected_candidates=actual, expected_jobs=55)
        for fact, job in zip(manifest["qualified"], jobs):
            if job["state"] == "done":
                continue
            require(file_hash(source) == source_sha256.lower(), "source_snapshot_changed")
            require(target_binding(target, manifest_sha256, source_sha256) == binding, "target_binding_changed")
            with connection(target, write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                require(schema_identity(conn) == schema, "schema_changed")
                current_jobs, _ = validate_state(conn, manifest)
                require(current_jobs == jobs, "concurrent_job_change")
                # Precommit comparison is rollback protection, not merely a postcheck.
                require(cohort_fingerprint(conn, manifest) == source_data, "historical_cohort_changed")
                leased = lease_jobs(conn, RULE_KEY, gate=gate, limit=1)
                require(len(leased) == 1 and leased[0]["assignment_id"] == fact["assignment_id"],
                        "unexpected_leased_job")
                finalize_job(conn, fact["assignment_id"], leased[0]["lease_token"], RULE_KEY,
                             prepared[fact["reviewer_id"]], gate=gate)
                jobs, committed_awards = validate_state(conn, manifest)
                conn.commit()
            announce("job-committed", binding, assignment_id=fact["assignment_id"],
                     awards_total=len(committed_awards), jobs_done=sum(j["state"] == "done" for j in jobs))
    with connection(target) as conn:
        conn.execute("BEGIN")
        full_checks(conn)
        jobs, awards = validate_state(conn, manifest)
        require(cohort_fingerprint(conn, manifest) == source_data, "historical_cohort_changed")
    require(file_hash(source) == source_sha256.lower(), "source_snapshot_changed")
    if issue_production:
        require(len(awards) == 4 and all(j["state"] == "done" for j in jobs), "issuance_incomplete")
    return {"mode": "issue-production" if issue_production else "recover-production" if recover_production else "verify-only",
            "rule_key": RULE_KEY, "target": str(target), "environment": binding["environment"],
            "hostname": binding["hostname"], "binding_sha256": digest(binding),
            "expected_candidates": actual, "expected_jobs": 55,
            "manifest_sha256": manifest_sha256, "source_sha256": source_sha256,
            "awards_issued": len(awards) - len(before), "awards_total": len(awards),
            "awards": [{k: a[k] for k in ("award_id", "reviewer_id", "earned_at_utc", "witness_count")}
                       for a in awards],
            "jobs": [{k: j[k] for k in ("assignment_id", "state", "attempts")} for j in jobs],
            "integrity_check": "ok", "capture_enabled": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-db", type=Path, required=True)
    parser.add_argument("--source-snapshot", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--expected-excluded", type=int, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--issue-production", action="store_true")
    mode.add_argument("--recover-production", action="store_true",
                      help="Authorize SQLite journal recovery only, with application/writers stopped")
    args = parser.parse_args(argv)
    try:
        result = issue(args.production_db, args.source_snapshot, args.manifest,
                       manifest_sha256=args.manifest_sha256, source_sha256=args.source_sha256,
                       expected_excluded=args.expected_excluded, issue_production=args.issue_production,
                       recover_production=args.recover_production)
    except (ValueError, OSError, sqlite3.Error) as error:
        progress = {"status": "unavailable; retain preceding job-committed events"}
        try:
            target = Path(args.production_db).resolve(strict=True)
            target_binding(target, args.manifest_sha256, args.source_sha256)
            offline_file(target)  # Failure reporting never attempts recovery.
            with connection(target) as conn:
                conn.execute("BEGIN")
                progress = {"validated": False, "awards_total": conn.execute(
                    "SELECT COUNT(*) FROM recognition_awards").fetchone()[0],
                    "jobs": [dict(r) for r in conn.execute(
                        "SELECT state,attempts,COUNT(*) AS count FROM recognition_jobs GROUP BY state,attempts")]}
        except (ValueError, OSError, sqlite3.Error):
            pass
        parser.exit(1, canonical({"error": str(error), "partial_progress": progress}) + "\n")
    print(canonical(result))


if __name__ == "__main__":
    main()
