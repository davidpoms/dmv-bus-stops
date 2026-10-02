"""Permanent foundation: disposable files only; no application activation."""

from pathlib import Path
from contextlib import contextmanager
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.review.recognition import DISABLED, RecognitionGate
from src.review.recognition.backfill import capture_batch, dry_run
from src.review.recognition.processing import finalize_job, lease_jobs, ledger_candidates
from src.review.recognition.processing import prepare_evaluation, materialize_ledger
from src.review.recognition.integrity import check_award_integrity
from src.review.recognition.qualification import Quarantined, capture, permanent_time, qualify
from src.review.recognition.rules import RULE_KEY, canonical, digest, explorer_candidates, initial_definition
from src.review.recognition.schema import TABLES, connection, migrate


ENABLED = RecognitionGate(capture=True, issuance=True)


class RecognitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "fixture.db"
        with sqlite3.connect(self.path) as db:
            db.executescript("""
                CREATE TABLE community_reviewers(id INTEGER PRIMARY KEY,display_name TEXT);
                INSERT INTO community_reviewers VALUES(1,'Private Name'),(2,'Other');
                CREATE TABLE physical_stops(id INTEGER PRIMARY KEY);
                CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER PRIMARY KEY,current_gtfs INTEGER);
                CREATE TABLE stop_review_assignments(id INTEGER PRIMARY KEY,stop_id INTEGER,reviewer_id INTEGER,status TEXT,completed_at TEXT);
                CREATE TABLE stop_observations(id INTEGER PRIMARY KEY,assignment_id INTEGER,reviewer_id INTEGER,physical_stop_id INTEGER,source TEXT,observed_at TEXT);
            """)
        db.close()

    def sql(self, query, parameters=()):
        with connection(self.path, write=True) as conn:
            rows = conn.execute(query, parameters).fetchall()
            conn.commit()
            return [tuple(row) for row in rows]

    def review(self, assignment, stop=None, timestamp=None):
        stop = assignment if stop is None else stop
        timestamp = timestamp or f"2026-09-01T00:{assignment // 60:02d}:{assignment % 60:02d}Z"
        with connection(self.path, write=True) as conn:
            conn.execute("INSERT OR IGNORE INTO physical_stops VALUES(?)", (stop,))
            conn.execute("INSERT OR IGNORE INTO stop_gtfs_status VALUES(?,0)", (stop,))
            conn.execute("INSERT INTO stop_review_assignments VALUES(?,?,1,'completed',?)", (assignment, stop, timestamp))
            conn.execute("INSERT INTO stop_observations VALUES(?,?,1,?,'community_review','2026-09-01 01:00:00')", (assignment, assignment, stop))
            conn.commit()

    def capture_all(self, count):
        migrate(self.path, apply=True)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for assignment in range(1, count + 1):
                capture(conn, assignment, RULE_KEY, gate=ENABLED)
            conn.commit()

    def issue(self, rule=RULE_KEY, limit=100):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            jobs = lease_jobs(conn, rule, gate=ENABLED, limit=limit)
            conn.commit()
        for job in jobs:
            owner = self.sql("SELECT reviewer_id FROM recognition_completions WHERE assignment_id=?", (job["assignment_id"],))[0][0]
            prepared = prepare_evaluation(self.path, owner, rule)
            with connection(self.path, write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                finalize_job(conn, job["assignment_id"], job["lease_token"], rule,
                             prepared, gate=ENABLED)
                conn.commit()
        return jobs

    def test_migration_rehearsal_repeat_source_preservation_and_fk(self):
        self.review(1)
        original = self.path.read_bytes()
        migrate(self.path)
        self.assertEqual(original, self.path.read_bytes())
        before = self.sql("SELECT * FROM stop_observations")
        migrate(self.path, apply=True)
        migrate(self.path, apply=True)
        self.assertEqual(before, self.sql("SELECT * FROM stop_observations"))
        tables = {r[0] for r in self.sql("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'recognition_%'")}
        self.assertEqual(set(TABLES), tables)
        with connection(self.path, write=True) as conn:
            self.assertEqual(1, conn.execute("PRAGMA foreign_keys").fetchone()[0])
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO recognition_jobs(assignment_id,rule_key,updated_at_utc) VALUES(999,?,'now')", (RULE_KEY,))
        self.assertEqual([], self.sql("PRAGMA foreign_key_check"))

    def test_incompatible_schema_rolls_back_and_missing_path_not_created(self):
        self.sql("CREATE TABLE recognition_jobs(wrong TEXT)")
        with self.assertRaisesRegex(ValueError, "incompatible_recognition_schema"):
            migrate(self.path, apply=True)
        self.assertEqual([], self.sql("SELECT name FROM sqlite_master WHERE name='recognition_completions'"))
        missing = self.path.parent / "missing.db"
        with self.assertRaises(sqlite3.OperationalError):
            migrate(missing, apply=True)
        self.assertFalse(missing.exists())

    def test_migration_on_repository_schema_and_drift_detection(self):
        path = self.path.parent / "current-schema.db"
        db = sqlite3.connect(path)
        try:
            db.executescript((Path(__file__).resolve().parents[1] / "src/database/schema.sql").read_text(encoding="utf-8"))
            db.commit()
        finally:
            db.close()
        migrate(path, apply=True)
        migrate(path, apply=True)
        with connection(path, write=True) as conn:
            conn.execute("DROP TRIGGER recognition_completions_immutable_update")
            conn.execute("CREATE TRIGGER recognition_completions_immutable_update BEFORE UPDATE ON recognition_completions BEGIN SELECT 1; END")
            conn.commit()
        with self.assertRaisesRegex(ValueError, "incompatible_recognition_schema"):
            migrate(path, apply=True)

    def test_commands_require_explicit_paths_and_processor_has_no_apply(self):
        root = Path(__file__).resolve().parents[1]
        for script, arguments in (
            ("create_recognition_tables.py", []),
            ("process_reviewer_recognition.py", []),
            ("process_reviewer_recognition.py", ["--db", str(self.path), "--rule-key", RULE_KEY,
                                                 "--through-assignment", "0", "--apply"]),
        ):
            result = subprocess.run([sys.executable, "-B", str(root / "scripts/active" / script), *arguments],
                                    capture_output=True, text=True, timeout=20, cwd=root)
            self.assertEqual(2, result.returncode, result.stderr)
        self.assertEqual([], self.sql("SELECT name FROM sqlite_master WHERE name LIKE 'recognition_%'"))

    def test_qualification_rejects_duplicates_before_matching(self):
        self.review(1)
        self.sql("INSERT INTO stop_observations VALUES(2,1,2,999,'community_review',NULL)")
        with connection(self.path) as conn, self.assertRaisesRegex(Quarantined, "ambiguous"):
            qualify(conn, 1)

    def test_qualification_identity_source_status_and_missing_rows(self):
        self.review(1)
        self.sql("INSERT INTO stop_observations VALUES(2,1,2,999,'import',NULL)")
        with connection(self.path) as conn:
            self.assertEqual(1, qualify(conn, 1)["observation_id"])
        for column, wrong in (("reviewer_id", 2), ("physical_stop_id", 999)):
            self.sql(f"UPDATE stop_observations SET {column}=? WHERE id=1", (wrong,))
            with connection(self.path) as conn, self.assertRaisesRegex(Quarantined, "identity_mismatch"):
                qualify(conn, 1)
            self.sql(f"UPDATE stop_observations SET {column}=1 WHERE id=1")
        self.sql("DELETE FROM physical_stops")
        with connection(self.path) as conn, self.assertRaisesRegex(Quarantined, "missing_identity"):
            qualify(conn, 1)
        self.sql("UPDATE stop_review_assignments SET status='assigned'")
        with connection(self.path) as conn, self.assertRaisesRegex(Quarantined, "not_completed"):
            qualify(conn, 1)

    def test_timestamp_policy_and_no_observed_fallback(self):
        for value in (None, "bad", "2026-02-30T00:00:00Z", "2026-09-01T00:00:00.000Z",
                      "2026-09-01T00:00:00.1-04:00", "2026-09-01 00:00:00"):
            with self.subTest(value=value), self.assertRaises(Quarantined):
                permanent_time(value)
        self.assertEqual(("2026-09-01T04:00:00Z", "explicit_offset"), permanent_time("2026-09-01T00:00:00-04:00"))
        self.assertEqual("2026-09-01T00:00:00Z", permanent_time("2026-09-01 00:00:00", sqlite_utc_provenance="reviewed-submit-writer")[0])
        self.review(1, timestamp="bad")
        with connection(self.path) as conn, self.assertRaisesRegex(Quarantined, "invalid_completion_time"):
            qualify(conn, 1)

    def test_capture_inactive_history_and_retries_preserve_evidence(self):
        self.review(1)
        self.capture_all(1)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            capture(conn, 1, RULE_KEY, gate=ENABLED)
            conn.commit()
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_completions"))
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_jobs"))
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-02T00:00:00Z'")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(Quarantined, "immutable_completion_conflict"):
                capture(conn, 1, RULE_KEY, gate=ENABLED)

    def test_explorer_all_boundaries_and_explicit_rule_definition(self):
        facts = [dict(assignment_id=n, observation_id=n, reviewer_id=1, physical_stop_id=n,
                      completed_at_utc=f"2026-09-01T00:{n // 60:02d}:{n % 60:02d}Z") for n in range(1, 102)]
        for count in (0, 4, 5, 19, 20, 49, 50, 99, 100, 101):
            with self.subTest(count=count):
                candidates = explorer_candidates(facts[:count], RULE_KEY, initial_definition())
                self.assertEqual([str(n) for n in (5, 20, 50, 100) if n <= count], [c["tier_key"] for c in candidates])
                for c in candidates:
                    self.assertEqual(c["numerator"], len(c["evidence"]["witnesses"]))
                    self.assertEqual(facts[c["numerator"]-1]["completed_at_utc"], c["earned_at_utc"])
        # Proves evaluator uses supplied definition, not module thresholds.
        changed = initial_definition()
        changed["thresholds"] = [20]
        self.assertEqual(["20"], [c["tier_key"] for c in explorer_candidates(facts, "test-rule", changed)])

    def test_earliest_distinct_witnesses_order_is_deterministic(self):
        for n in range(1, 7):
            self.review(n, stop=1 if n == 6 else n, timestamp="2026-09-01T00:00:00Z")
        self.capture_all(6)
        with connection(self.path) as conn:
            conn.execute("BEGIN")
            snapshot = materialize_ledger(conn, RULE_KEY, reviewer_id=1)
            facts = [dict(r) for r in conn.execute("SELECT * FROM recognition_completions ORDER BY assignment_id DESC")]
        candidates = ledger_candidates(snapshot)
        self.assertEqual(candidates, explorer_candidates(facts, RULE_KEY, initial_definition()))
        self.assertEqual([1, 2, 3, 4, 5], [w["assignment_id"] for w in candidates[0]["evidence"]["witnesses"]])

    def test_immutable_triggers_and_lifetime_uniqueness(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        self.issue()
        for table in set(TABLES) - {"recognition_jobs", "recognition_runs"}:
            column = self.sql(f"PRAGMA table_info({table})")[0][1]
            for statement in (f"DELETE FROM {table}", f"UPDATE {table} SET {column}={column}"):
                with self.subTest(statement=statement), self.assertRaises(sqlite3.IntegrityError):
                    self.sql(statement)
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql("""INSERT INTO recognition_awards SELECT 'different-id',reviewer_id,family,scope_key,tier_key,
                rule_key,earned_at_utc,evaluated_at_utc,origin,numerator,evidence_json,evidence_sha256 FROM recognition_awards""")
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_awards"))
        # Protect against REPLACE even through a connection with recursive triggers off.
        with sqlite3.connect(self.path) as legacy:
            with self.assertRaises(sqlite3.IntegrityError):
                legacy.execute("INSERT OR REPLACE INTO recognition_rule_versions SELECT * FROM recognition_rule_versions")
        legacy.close()

    def test_version_changes_do_not_reaward_and_stale_delivery_fails(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        jobs = self.issue()
        original_awards = self.sql("SELECT * FROM recognition_awards")
        original_witnesses = self.sql("SELECT * FROM recognition_award_witnesses")
        definition = initial_definition()
        self.sql("INSERT INTO recognition_rule_versions VALUES('explorer:v2','explorer',2,?,?,'2026-10-01T00:00:00Z')", (canonical(definition), digest(definition)))
        self.review(6)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            capture(conn, 6, "explorer:v2", gate=ENABLED)
            conn.commit()
        self.issue("explorer:v2")
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_awards"))
        self.assertEqual(original_awards, self.sql("SELECT * FROM recognition_awards"))
        self.assertEqual(original_witnesses, self.sql("SELECT * FROM recognition_award_witnesses"))
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(Quarantined, "stale_job_lease"):
                finalize_job(conn, 1, jobs[0]["lease_token"], RULE_KEY, [], gate=ENABLED)

    def test_disabled_services_do_not_open_or_write(self):
        self.assertEqual(RecognitionGate(), DISABLED)
        self.assertIsNone(capture(None, 1, RULE_KEY))
        self.assertEqual([], lease_jobs(None, RULE_KEY))
        self.assertEqual([], finalize_job(None, 1, "token", RULE_KEY, []))
        self.assertIsNone(capture_batch("missing.db", {}))
        self.review(1)
        before = self.path.read_bytes()
        with connection(self.path, write=True) as conn:
            self.assertIsNone(capture(conn, 1, RULE_KEY))
        self.assertEqual(before, self.path.read_bytes())

    def test_backfill_deterministic_bounded_private_manifest_and_idempotent_capture(self):
        for n in range(1, 7):
            self.review(n)
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-01T00:00:00.5Z' WHERE id=6")
        migrate(self.path, apply=True)
        before = self.path.read_bytes()
        plan = dry_run(self.path, RULE_KEY, through_assignment=6, limit=6)
        self.assertEqual(plan, dry_run(self.path, RULE_KEY, through_assignment=6, limit=6))
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual([], plan["candidates"])
        self.assertEqual("fractional_timestamp_policy_unresolved", plan["excluded"][0]["reason"])
        self.assertNotIn("Private Name", canonical(plan))
        partial = dry_run(self.path, RULE_KEY, through_assignment=6, limit=2)
        self.assertEqual(2, partial["cohort"]["next_after_assignment"])
        self.assertTrue(partial["cohort"]["has_more"])
        run = capture_batch(self.path, plan, gate=ENABLED)
        self.assertEqual(run, capture_batch(self.path, plan, gate=ENABLED))
        self.assertEqual([(5,)], self.sql("SELECT count(*) FROM recognition_completions"))
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_runs"))
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_awards"))
        repeated = dry_run(self.path, RULE_KEY, through_assignment=6, limit=6)
        self.assertEqual(repeated, dry_run(self.path, RULE_KEY, through_assignment=6, limit=6))
        self.assertEqual(["5"], [c["tier_key"] for c in repeated["candidates"]])
        for query in ("DELETE FROM recognition_runs", "UPDATE recognition_runs SET state='running',finished_at_utc=NULL"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.sql(query)

    def test_changed_backfill_input_rejected_and_failure_rolls_back_closes(self):
        self.review(1)
        self.review(2)
        migrate(self.path, apply=True)
        plan = dry_run(self.path, RULE_KEY, through_assignment=2)
        with patch("src.review.recognition.backfill.record_run", side_effect=RuntimeError("injected")):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                capture_batch(self.path, plan, gate=ENABLED)
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_completions"))
        # Independent writer succeeding demonstrates no retained write lock.
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-10-01T00:00:00Z' WHERE id=1")
        with self.assertRaisesRegex(Quarantined, "backfill_input_changed"):
            capture_batch(self.path, plan, gate=ENABLED)

    def test_award_witness_failure_rolls_back_group_and_expired_lease_retries(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            first = lease_jobs(conn, RULE_KEY, gate=ENABLED, limit=1)[0]
            conn.commit()
        self.sql("UPDATE recognition_jobs SET lease_until_utc='2000-01-01T00:00:00Z' WHERE assignment_id=1")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            job = lease_jobs(conn, RULE_KEY, gate=ENABLED, limit=1)[0]
            self.assertNotEqual(first["lease_token"], job["lease_token"])
            conn.commit()
        before_source = self.sql("SELECT * FROM stop_observations")
        self.sql("""CREATE TRIGGER injected_failure BEFORE INSERT ON recognition_award_witnesses
            WHEN (SELECT count(*) FROM recognition_award_witnesses)=2
            BEGIN SELECT RAISE(ABORT,'injected'); END""")
        prepared = prepare_evaluation(self.path, 1, RULE_KEY)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(sqlite3.IntegrityError, "injected"):
                finalize_job(conn, 1, job["lease_token"], RULE_KEY, prepared, gate=ENABLED)
            # Even if a caller catches the exception and commits, no partial award.
            conn.commit()
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_awards"))
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_award_witnesses"))
        self.assertEqual(before_source, self.sql("SELECT * FROM stop_observations"))
        self.assertEqual([('leased',)], self.sql("SELECT state FROM recognition_jobs WHERE assignment_id=1"))
        self.sql("DROP TRIGGER injected_failure")

    def test_completion_job_failure_is_atomic_with_assignment_transaction(self):
        self.review(1)
        self.sql("UPDATE stop_review_assignments SET status='assigned',completed_at=NULL")
        migrate(self.path, apply=True)
        self.sql("CREATE TRIGGER reject_job BEFORE INSERT ON recognition_jobs BEGIN SELECT RAISE(ABORT,'injected'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            with connection(self.path, write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("UPDATE stop_review_assignments SET status='completed',completed_at='2026-09-01T00:00:00Z'")
                capture(conn, 1, RULE_KEY, gate=ENABLED)
                conn.commit()
        self.assertEqual([('assigned', None)], self.sql("SELECT status,completed_at FROM stop_review_assignments"))
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_completions"))
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM stop_observations"))

    def test_connection_closes_even_if_rollback_raises(self):
        mock = MagicMock()
        mock.rollback.side_effect = RuntimeError("rollback failure")
        with patch("src.review.recognition.schema.sqlite3.connect", return_value=mock):
            with self.assertRaisesRegex(RuntimeError, "rollback failure"):
                with connection(self.path):
                    pass
        mock.close.assert_called_once()

    def test_cross_rule_changed_qualification_is_rejected_without_rewriting_award(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        self.issue()
        original = self.sql("SELECT * FROM recognition_awards")
        witnesses = self.sql("SELECT * FROM recognition_award_witnesses")
        definition = initial_definition()
        self.sql("INSERT INTO recognition_rule_versions VALUES('explorer:v2','explorer',2,?,?,'2026-10-01T00:00:00Z')", (canonical(definition), digest(definition)))
        self.review(6, timestamp="2026-08-01T00:00:00Z")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            capture(conn, 6, "explorer:v2", gate=ENABLED)
            job = lease_jobs(conn, "explorer:v2", gate=ENABLED, limit=1)[0]
            conn.commit()
        prepared = prepare_evaluation(self.path, 1, "explorer:v2")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(Quarantined, "award_qualification_evidence_conflict"):
                finalize_job(conn, 6, job["lease_token"], "explorer:v2", prepared, gate=ENABLED)
            conn.commit()
        self.assertEqual(original, self.sql("SELECT * FROM recognition_awards"))
        self.assertEqual(witnesses, self.sql("SELECT * FROM recognition_award_witnesses"))
        self.assertEqual([('leased',)], self.sql("SELECT state FROM recognition_jobs WHERE assignment_id=6"))

    def test_calculation_is_read_only_and_finalization_does_not_scan_history(self):
        for n in range(1, 101):
            self.review(n)
        self.capture_all(100)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            job = lease_jobs(conn, RULE_KEY, gate=ENABLED, limit=1)[0]
            with self.assertRaisesRegex(ValueError, "read_only"):
                materialize_ledger(conn, RULE_KEY, reviewer_id=1)
            conn.commit()
        def calculate(*args):
            # This runs synchronously inside CPU calculation, with no sleeps.
            # A reservation alone is insufficient: COMMIT needs the read lock gone.
            other = sqlite3.connect(self.path, timeout=0)
            try:
                self.assertEqual('delete', other.execute("PRAGMA journal_mode").fetchone()[0])
                other.execute("UPDATE community_reviewers SET display_name='committed during calculation' WHERE id=1")
                other.commit()
            finally:
                other.close()
            return explorer_candidates(*args)
        with patch("src.review.recognition.processing.explorer_candidates", side_effect=calculate) as calculator:
            prepared = prepare_evaluation(self.path, 1, RULE_KEY)
            self.assertEqual(1, calculator.call_count)
        with connection(self.path, write=True) as conn:
            statements = []
            conn.set_trace_callback(statements.append)
            conn.execute("BEGIN IMMEDIATE")
            with patch("src.review.recognition.processing.ledger_candidates", side_effect=AssertionError("full-history scan")):
                finalize_job(conn, 1, job["lease_token"], RULE_KEY, prepared, gate=ENABLED)
            conn.commit()
        self.assertFalse(any("FROM recognition_completions WHERE reviewer_id=" in " ".join(sql.split())
                             for sql in statements))
        self.assertEqual([(4,)], self.sql("SELECT count(*) FROM recognition_awards"))
        self.assertEqual([('committed during calculation',)], self.sql("SELECT display_name FROM community_reviewers WHERE id=1"))

    def test_late_completion_invalidates_prepared_snapshot(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        prepared = prepare_evaluation(self.path, 1, RULE_KEY)
        # A lower assignment ID proves MAX(assignment_id) is not the checkpoint.
        self.review(0, stop=6, timestamp="2026-08-01T00:00:00Z")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            capture(conn, 0, RULE_KEY, gate=ENABLED)
            job = lease_jobs(conn, RULE_KEY, gate=ENABLED, limit=1)[0]
            with self.assertRaisesRegex(Quarantined, "stale_or_invalid_candidates"):
                finalize_job(conn, job["assignment_id"], job["lease_token"], RULE_KEY, prepared, gate=ENABLED)
            conn.commit()
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_awards"))

    def test_preparation_and_dry_run_close_connections_before_cpu_calculation(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        original_plan = dry_run(self.path, RULE_KEY, through_assignment=5)

        def independent_commit():
            other = sqlite3.connect(self.path, timeout=0)
            try:
                self.assertEqual('delete', other.execute("PRAGMA journal_mode").fetchone()[0])
                other.execute("UPDATE community_reviewers SET display_name='CPU-stage commit' WHERE id=1")
                other.commit()
            finally:
                other.close()

        # Negative control: the old retained read snapshot really prevents this
        # exact independent COMMIT, even though BEGIN IMMEDIATE would succeed.
        with connection(self.path) as reader:
            reader.execute("BEGIN")
            reader.execute("SELECT * FROM recognition_completions").fetchall()
            with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                independent_commit()

        for operation, module in (
            (lambda: prepare_evaluation(self.path, 1, RULE_KEY), "processing"),
            (lambda: dry_run(self.path, RULE_KEY, through_assignment=5), "backfill"),
        ):
            with self.subTest(module=module):
                opened = []

                @contextmanager
                def track_connection(*args, **kwargs):
                    with connection(*args, **kwargs) as conn:
                        opened.append(conn)
                        yield conn

                def calculate(*args):
                    self.assertEqual(1, len(opened))
                    with self.assertRaises(sqlite3.ProgrammingError):
                        opened[0].execute("SELECT 1")
                    independent_commit()
                    return explorer_candidates(*args)

                with patch(f"src.review.recognition.{module}.connection", side_effect=track_connection):
                    with patch("src.review.recognition.processing.explorer_candidates", side_effect=calculate) as cpu:
                        result = operation()
                        self.assertEqual(1, cpu.call_count)
                if module == "backfill":
                    self.assertEqual(original_plan, result)
        self.assertEqual([('CPU-stage commit',)], self.sql("SELECT display_name FROM community_reviewers WHERE id=1"))

    def test_preparation_read_failure_closes_snapshot(self):
        self.review(1)
        self.capture_all(1)
        opened = []

        @contextmanager
        def track_connection(*args, **kwargs):
            with connection(*args, **kwargs) as conn:
                opened.append(conn)
                yield conn

        with patch("src.review.recognition.processing.connection", side_effect=track_connection):
            with patch("src.review.recognition.processing.load_rule", side_effect=RuntimeError("read failed")):
                with self.assertRaisesRegex(RuntimeError, "read failed"):
                    prepare_evaluation(self.path, 1, RULE_KEY)
        with self.assertRaises(sqlite3.ProgrammingError):
            opened[0].execute("SELECT 1")
        self.sql("UPDATE community_reviewers SET display_name='after failure' WHERE id=1")

    def test_backfill_capture_never_calculates_candidates_under_writer(self):
        self.review(1)
        migrate(self.path, apply=True)
        plan = dry_run(self.path, RULE_KEY, through_assignment=1)
        with patch("src.review.recognition.backfill.ledger_candidates", side_effect=AssertionError("candidate read under writer")):
            capture_batch(self.path, plan, gate=ENABLED)
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_completions"))

    def test_legacy_replacement_refuses_retained_sources_and_preserves_unreferenced_behavior(self):
        from src.review import complete_stop_review as legacy
        self.review(1)
        self.review(2)
        for column in ("shelter_present", "bench_present", "bench_condition", "waiting_area_type", "notes"):
            self.sql(f"ALTER TABLE stop_observations ADD COLUMN {column} TEXT")
        args = ("no", "no", "none", "sidewalk", "fixture")
        # Pre-migration replacement is still supported.
        with patch.object(legacy, "DATABASE_PATH", self.path):
            legacy.complete_stop_review(2, 1, *args)
        self.capture_all(1)
        before = self.sql("SELECT * FROM stop_observations")
        with patch.object(legacy, "DATABASE_PATH", self.path):
            with self.assertRaisesRegex(ValueError, "recognition_retention"):
                legacy.complete_stop_review(1, 1, *args)
        self.assertEqual(before, self.sql("SELECT * FROM stop_observations"))
        # Successful subsequent mutation verifies rollback/close and unrelated use.
        with patch.object(legacy, "DATABASE_PATH", self.path):
            legacy.complete_stop_review(2, 1, *args)
        self.assertEqual([], self.sql("PRAGMA foreign_key_check"))

    def test_award_integrity_detects_missing_extra_mismatch_duplicates_and_order(self):
        for n in range(1, 7):
            self.review(n)
        self.capture_all(6)
        prepared = prepare_evaluation(self.path, 1, RULE_KEY)
        candidate = json.loads(prepared.candidates_json)[0]
        for defect in ("missing", "extra", "mismatch", "duplicate", "order", "hash"):
            with self.subTest(defect=defect), connection(self.path, write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                evidence = json.loads(canonical(candidate["evidence"]))
                ids = list(range(1, 6))
                if defect == "missing":
                    ids.pop()
                elif defect == "extra":
                    ids.append(6)
                elif defect == "mismatch":
                    evidence["witnesses"][0]["observation_id"] = 999
                elif defect == "duplicate":
                    evidence["witnesses"][1] = evidence["witnesses"][0]
                elif defect == "order":
                    evidence["witnesses"][0], evidence["witnesses"][1] = evidence["witnesses"][1], evidence["witnesses"][0]
                conn.execute("INSERT INTO recognition_awards VALUES('corrupt',1,'explorer','global','5',?,?,?,'live',5,?,?)",
                             (RULE_KEY, candidate["earned_at_utc"], candidate["earned_at_utc"], canonical(evidence),
                              "bad-hash" if defect == "hash" else digest(evidence)))
                conn.executemany("INSERT INTO recognition_award_witnesses VALUES('corrupt',?)", [(n,) for n in ids])
                with self.assertRaises(Quarantined):
                    check_award_integrity(conn, "corrupt")
                job = lease_jobs(conn, RULE_KEY, gate=ENABLED, limit=1)[0]
                with self.assertRaises(Quarantined):
                    finalize_job(conn, 1, job["lease_token"], RULE_KEY, prepared, gate=ENABLED)
                self.assertEqual('leased', conn.execute("SELECT state FROM recognition_jobs WHERE assignment_id=1").fetchone()[0])
                # No commit: discard deliberately corrupt fixture records.

    def test_multiprocess_workers_cannot_duplicate_awards(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        code = """
import sys
from src.review.recognition import RecognitionGate
from src.review.recognition.schema import connection
from src.review.recognition.processing import lease_jobs, prepare_evaluation, finalize_job
gate=RecognitionGate(issuance=True)
with connection(sys.argv[1],write=True) as conn:
    conn.execute('BEGIN IMMEDIATE')
    jobs=lease_jobs(conn,'explorer:v1',gate=gate,limit=1)
    conn.commit()
prepared=prepare_evaluation(sys.argv[1],1,'explorer:v1')
with connection(sys.argv[1],write=True) as conn:
    conn.execute('BEGIN IMMEDIATE')
    for job in jobs:
        finalize_job(conn,job['assignment_id'],job['lease_token'],'explorer:v1',prepared,gate=gate)
    conn.commit()
"""
        children = [subprocess.Popen([sys.executable, "-B", "-c", code, str(self.path)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                     cwd=Path(__file__).resolve().parents[1]) for _ in range(2)]
        try:
            for child in children:
                _, error = child.communicate(timeout=30)
                self.assertEqual(0, child.returncode, error)
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                child.communicate()
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_awards"))
        self.assertEqual([(5,)], self.sql("SELECT count(*) FROM recognition_award_witnesses"))
        self.assertEqual([(2,)], self.sql("SELECT count(*) FROM recognition_jobs WHERE state='done'"))


if __name__ == "__main__":
    unittest.main()
