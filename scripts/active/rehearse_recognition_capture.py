"""Explicit offline disposable-copy capture rehearsal; verification-only by default."""

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.review.recognition import RecognitionGate
from src.review.recognition.backfill import capture_batch, source_plan
from src.review.recognition.rules import RULE_KEY, canonical, digest, initial_definition, load_rule
from src.review.recognition.schema import TABLES, connection, install


def file_hash(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def offline_file(path):
    path = Path(path).resolve(strict=True)
    require(path.is_file(), "existing_file_required")
    require(not any(Path(str(path) + suffix).exists()
                    for suffix in ("-wal", "-shm", "-journal")), "offline_copy_required")
    with path.open("rb") as stream:
        header = stream.read(20)
    require(header[:16] == b"SQLite format 3\x00" and header[18:20] == b"\x01\x01",
            "standalone_rollback_journal_copy_required")
    return path


def fingerprint_value(value):
    """Lossless encoding of SQLite's five value types, including NUL text."""
    if value is None:
        return ["null"]
    if isinstance(value, bytes):
        return ["blob", value.hex()]
    if isinstance(value, str):
        return ["text", value]
    if isinstance(value, int):
        return ["integer", str(value)]
    if isinstance(value, float):
        return ["real", value.hex()]
    raise ValueError("unsupported_sqlite_value")


def application_fingerprint(conn):
    """Compare all non-recognition tables without logging private row contents."""
    result = {}
    for name, sql in conn.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"):
        if name.startswith("recognition_") or name.startswith("sqlite_"):
            continue
        quoted = '"' + name.replace('"', '""') + '"'
        columns = [r[1] for r in conn.execute("PRAGMA table_info(" + quoted + ")")]
        expressions = ['"' + col.replace('"', '""') + '"' for col in columns]
        hashes = sorted(digest([fingerprint_value(value) for value in row]) for row in conn.execute(
            "SELECT " + ",".join(expressions) + " FROM " + quoted))
        result[name] = (sql, len(hashes), digest(hashes))
    return result


def authoritative_triggers(conn):
    """Derive SQL from the real installer in memory only; never migrate target."""
    reference = sqlite3.connect(":memory:")
    try:
        reference.execute("PRAGMA foreign_keys=ON")
        reference.execute("BEGIN")
        for table in ("community_reviewers", "physical_stops", "stop_review_assignments", "stop_observations"):
            row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            require(row is not None, "initialized_source_schema_required")
            reference.execute(row[0])
        install(reference)
        return {name: (table, sql) for name, table, sql in reference.execute(
            "SELECT name,tbl_name,sql FROM sqlite_master WHERE type='trigger'")}
    finally:
        reference.close()


def check_schema(conn, *, additional_written_tables=()):
    for name, body in TABLES.items():
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
        require(row is not None and " ".join(row[0].split()) ==
                " ".join(f"CREATE TABLE {name} ({body})".split()), "initialized_schema_required")
    triggers = {name: (table, sql) for name, table, sql in conn.execute(
        "SELECT name,tbl_name,sql FROM sqlite_master WHERE type='trigger'")}
    expected = authoritative_triggers(conn)
    require(expected.keys() <= triggers.keys(), "recognition_protection_missing")
    # Exact stored SQL comparison deliberately rejects even formatting drift;
    # whitespace normalization could hide changes inside SQL string literals.
    require(all(triggers[name] == definition for name, definition in expected.items()),
            "recognition_protection_mismatch")
    written_tables = {"recognition_completions", "recognition_jobs", "recognition_runs"}
    written_tables.update(additional_written_tables)
    require(not any(name not in expected and table in written_tables
                    for name, (table, _sql) in triggers.items()), "unexpected_capture_trigger")
    require(load_rule(conn, RULE_KEY) == initial_definition(), "initial_rule_required")
    require(conn.execute("PRAGMA foreign_key_check").fetchone() is None, "foreign_key_check_failed")


def check_state(conn, manifest, *, allow_empty):
    counts = {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
              for name in TABLES if name not in {"recognition_rule_versions", "recognition_scopes"}}
    if allow_empty and not any(counts.values()):
        return "empty"
    n = len(manifest["qualified"])
    require(counts == {"recognition_completions": n, "recognition_jobs": n,
                       "recognition_awards": 0, "recognition_award_witnesses": 0,
                       "recognition_runs": 1}, "unexpected_recognition_state")
    for sequence, fact in enumerate(manifest["qualified"], 1):
        row = conn.execute("SELECT * FROM recognition_completions WHERE assignment_id=?",
                           (fact["assignment_id"],)).fetchone()
        require(row is not None and all(row[k] == v for k, v in fact.items())
                and row["origin"] == "backfill" and row["qualification_rule_key"] == RULE_KEY
                and row["ledger_sequence"] == sequence, "completion_state_mismatch")
    require(conn.execute("""SELECT COUNT(*) FROM recognition_jobs j
        JOIN recognition_completions c USING(assignment_id)
        WHERE j.rule_key=? AND j.state='pending' AND j.attempts=0
          AND j.lease_token IS NULL AND j.lease_until_utc IS NULL AND j.last_error_code IS NULL""",
                         (RULE_KEY,)).fetchone()[0] == n, "job_state_mismatch")
    run = conn.execute("SELECT * FROM recognition_runs WHERE run_id=?", (digest(manifest),)).fetchone()
    require(run is not None and run["kind"] == "backfill" and run["state"] == "complete"
            and run["finished_at_utc"] is not None and run["manifest_json"] == canonical(manifest)
            and run["manifest_sha256"] == digest(manifest), "run_state_mismatch")
    return "captured"


def read_manifest(path, expected_hash, expected_qualified, expected_excluded, *, expected_candidates=0):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected_hash.lower(), "manifest_hash_mismatch")
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate_manifest_key")
            result[key] = value
        return result
    manifest = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_pairs)
    keys = {"format", "algorithm", "rule_key", "rule_sha256", "cohort",
            "sqlite_utc_provenance", "source_sha256", "source", "qualified", "excluded",
            "candidate_basis", "candidates"}
    require(isinstance(manifest, dict) and set(manifest) == keys, "invalid_manifest_structure")
    require(manifest["rule_key"] == RULE_KEY and manifest["rule_sha256"] == digest(initial_definition()),
            "manifest_rule_mismatch")
    require(manifest["candidate_basis"] == "existing_immutable_ledger_only"
            and isinstance(manifest["candidates"], list)
            and len(manifest["candidates"]) == expected_candidates, "unexpected_manifest_candidates")
    cohort = manifest["cohort"]
    require(isinstance(cohort, dict) and set(cohort) == {
        "after_assignment", "through_assignment", "limit", "next_after_assignment", "has_more"},
        "invalid_cohort")
    require(all(type(cohort[k]) is int for k in ("after_assignment", "through_assignment", "limit", "next_after_assignment"))
            and 0 <= cohort["after_assignment"] <= cohort["next_after_assignment"] <= cohort["through_assignment"]
            and 1 <= cohort["limit"] <= 1000 and cohort["has_more"] is False, "single_batch_cohort_required")
    require(type(expected_qualified) is int and 1 <= expected_qualified <= 1000
            and type(expected_excluded) is int and 0 <= expected_excluded <= 1000, "invalid_expected_counts")
    require(isinstance(manifest["qualified"], list) and len(manifest["qualified"]) == expected_qualified
            and isinstance(manifest["excluded"], list) and len(manifest["excluded"]) == expected_excluded
            and isinstance(manifest["source"], list), "manifest_counts_mismatch")
    return manifest


def rehearse(source_snapshot, disposable_target, manifest_path, *, source_sha256,
             manifest_sha256, expected_qualified=55, expected_excluded,
             capture_disposable=False):
    source, target = offline_file(source_snapshot), offline_file(disposable_target)
    require(not source.samefile(target), "source_target_alias")
    protected = [ROOT / "src/database/dmv_bus_stops.db"]
    if os.environ.get("DMV_BUS_STOPS_DB"):
        protected.append(Path(os.environ["DMV_BUS_STOPS_DB"]))
    require(not any(p.exists() and p.samefile(target) for p in protected), "application_target_forbidden")
    original = file_hash(source)
    require(original == source_sha256.lower(), "source_hash_mismatch")
    manifest = read_manifest(manifest_path, manifest_sha256, expected_qualified, expected_excluded)
    try:
        with connection(source) as conn:
            conn.execute("BEGIN")
            source_data = application_fingerprint(conn)
        with connection(target) as conn:
            conn.execute("BEGIN")
            check_schema(conn)
            require(source_data == application_fingerprint(conn), "source_target_data_mismatch")
            cohort = manifest["cohort"]
            current = source_plan(conn, RULE_KEY, through_assignment=cohort["through_assignment"],
                                  after_assignment=cohort["after_assignment"], limit=cohort["limit"],
                                  sqlite_utc_provenance=manifest["sqlite_utc_provenance"])
            require(canonical(current) == canonical({k: manifest[k] for k in current}),
                    "reviewed_manifest_mismatch")
            state = check_state(conn, manifest, allow_empty=True)
        if capture_disposable:
            capture_batch(target, manifest, gate=RecognitionGate(capture=True, issuance=False))
            with connection(target) as conn:
                conn.execute("BEGIN")
                state = check_state(conn, manifest, allow_empty=False)
                require(source_data == application_fingerprint(conn), "application_data_changed")
        return {"mode": "capture-disposable" if capture_disposable else "verify-only",
                "state": state, "qualified": expected_qualified, "excluded": expected_excluded,
                "manifest_id": digest(manifest), "issuance_enabled": False}
    finally:
        require(file_hash(source) == original, "source_snapshot_changed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-snapshot", type=Path, required=True)
    parser.add_argument("--disposable-target", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--expected-qualified", type=int, default=55)
    parser.add_argument("--expected-excluded", type=int, required=True)
    parser.add_argument("--capture-disposable", action="store_true",
                        help="Explicitly authorize capture on the offline disposable target only")
    args = parser.parse_args(argv)
    try:
        result = rehearse(args.source_snapshot, args.disposable_target, args.manifest,
                          source_sha256=args.source_sha256, manifest_sha256=args.manifest_sha256,
                          expected_qualified=args.expected_qualified, expected_excluded=args.expected_excluded,
                          capture_disposable=args.capture_disposable)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, f"Rehearsal refused: {error}\n")
    print(canonical(result))


if __name__ == "__main__":
    main()
