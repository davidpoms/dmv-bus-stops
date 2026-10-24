"""Slice F local observations only; no hosted access, network or production data."""

from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from tests import test_recognition_readiness_receipts as fixtures
from tests.recognition_storage_rehearsal import DisposableBackups, inventory
from tests.test_recognition_administration import at
from src.review.recognition import administration as a, admin_auth as m, approvals as b
from src.review.recognition import local_readiness as r, production_operations as d, operations
from src.review.recognition.rules import digest


class BackupRestoreRehearsalTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ReadinessReceiptTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.backups = DisposableBackups(self.fixture.context)
        self.addCleanup(self.backups.cleanup)

    def test_daily_coherent_verified_pair_and_content_failure(self):
        f = self.fixture
        before = inventory(f.path)
        day1 = self.backups.create(now=at(90))
        day2 = self.backups.create(now=at(86490))
        self.assertNotEqual(day1.name, day2.name)
        body = self.backups.verify(day1)
        self.assertEqual(1, body["generation"])
        self.assertEqual(before, body["inventories"]["target"])
        self.assertEqual(len(f.sql("SELECT * FROM recognition_approvals", control=True)),
            body["inventories"]["control"]["tables"]["recognition_approvals"]["count"])
        with closing(sqlite3.connect(day1 / "target.sqlite")) as conn:
            conn.execute("UPDATE community_reviewers SET role='review_lead' WHERE id=1")
            conn.commit()
        with self.assertRaises(ValueError):
            self.backups.verify(day1)

    def test_retention_boundary_latest_restore_point_and_active_file_protection(self):
        start = datetime(2099, 1, 1, tzinfo=timezone.utc)
        stamp = lambda day: (start + timedelta(days=day)).isoformat()
        old = self.backups.create(now=stamp(0))
        boundary = self.backups.create(now=stamp(10))
        recent = self.backups.create(now=stamp(39))
        original = inventory(self.fixture.path)
        self.assertEqual([old], self.backups.retention_plan(now=stamp(40)))
        self.assertEqual([old.name], self.backups.retain(now=stamp(40)))
        self.assertTrue(boundary.exists())
        self.assertTrue(recent.exists())
        self.assertEqual([], self.backups.retain(now=stamp(40)))
        self.backups.retain(now=stamp(100))
        self.assertEqual([recent], list(self.backups.root.iterdir()))
        self.assertEqual([], self.backups.retain(now=stamp(200)))
        self.assertEqual(original, inventory(self.fixture.path))
        for path in (self.fixture.path, self.fixture.control, self.backups.root.parent):
            with self.assertRaises(ValueError):
                self.backups.checked(path)

    def test_retention_refuses_unrecognized_contents(self):
        old = self.backups.create(now=at(90))
        self.backups.create(now=at(90 + 40 * 86400))
        (old / "unknown.txt").write_text("retain for inspection", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.backups.retain(now=at(90 + 50 * 86400))
        self.assertTrue((old / "target.sqlite").exists())

    def test_target_restore_preserves_control_then_explicit_rebind_fences_pending(self):
        f = self.fixture
        f.activate()
        self.assertEqual("COMPLETED", f.execute().state)
        completed = f.oid
        # Freeze and approve another operation; never execute it.
        for number in range(2, 6):
            f.fixture.review(number)
        f.operation = d.create_operation(f.config, f.session, f.request(True), now=at(150))
        f.oid = f.operation["envelope"]["operation_id"]
        f.approve(150)
        pending, approval_id = f.oid, f.aid
        self.assertIn(dict(operation_id=pending, approval_id=approval_id), d.discover_pending(f.config))
        saved = self.backups.create(now=at(150))
        control_before = inventory(f.control)
        self.backups.restore_target(saved)
        self.assertEqual(control_before, inventory(f.control))
        with self.assertRaises(a.AdminError):
            a.get_installation_control(f.config)
        with a.connect(f.path) as conn:
            preview = digest(a.observe_target(conn))
        self.assertEqual(2, a.advance_restore_generation(f.config, expected_generation=1,
            expected_target_sha256=preview, operator="disposable-host", reason="observed target restore", now=at(180)))
        self.assertEqual(2, a.get_installation_control(f.config)["generation"])
        self.assertEqual([], d.discover_pending(f.config))
        self.assertEqual([], d.continue_pending(f.config, now=at(180)))
        with a.transaction(f.config) as (control, _, _):
            self.assertEqual("INVALIDATED", b._read(control, approval_id)["state"])
        with self.assertRaises(a.AdminError):
            m.require_recognition_admin(f.config, f.session, now=at(180))
        with a.connect(f.path) as conn:
            self.assertEqual("COMPLETED", operations.get_operation(conn, completed)["executions"][-1]["state"])
        readiness = r.assess(f.config, now=at(180))
        self.assertEqual("NOT_ACTIVATED", readiness["activation_state"])
        self.assertFalse(readiness["activation_ready"])
        self.assertEqual("BLOCKED", readiness["production_execution"])
        self.assertEqual((1, 1, 1, 1), f.counts())

    def test_unknown_or_damaged_backup_never_used_for_restore(self):
        saved = self.backups.create(now=at(90))
        before = inventory(self.fixture.path)
        (saved / "target.sqlite").write_bytes(b"not SQLite")
        with self.assertRaises(ValueError):
            self.backups.restore_target(saved)
        self.assertEqual(before, inventory(self.fixture.path))

    def test_active_journal_artifact_refuses_restore(self):
        saved = self.backups.create(now=at(90))
        journal = Path(str(self.fixture.path) + "-journal")
        journal.write_bytes(b"synthetic live marker")
        try:
            with self.assertRaises(ValueError):
                self.backups.restore_target(saved)
        finally:
            journal.unlink()


class LocalProcessLockRehearsalTests(unittest.TestCase):
    def test_terminated_process_rolls_back_uncommitted_and_preserves_committed(self):
        for mode in ("DELETE", "WAL"):
            for committed in (False, True):
                with self.subTest(mode=mode, committed=committed), tempfile.TemporaryDirectory() as root:
                    path = Path(root) / "synthetic.sqlite"
                    with closing(sqlite3.connect(path)) as conn:
                        conn.execute("PRAGMA journal_mode=" + mode)
                        conn.execute("CREATE TABLE probe(value INTEGER)")
                        conn.execute("INSERT INTO probe VALUES(1)")
                        conn.commit()
                    code = '''import sqlite3,sys
c=sqlite3.connect(sys.argv[1])
c.execute("BEGIN IMMEDIATE")
c.execute("UPDATE probe SET value=2")
if sys.argv[2]=="True": c.commit()
print("BOUNDARY",flush=True)
sys.stdin.readline()
'''
                    process = subprocess.Popen([sys.executable, "-B", "-u", "-c", code, str(path), str(committed)],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    try:
                        self.assertEqual("BOUNDARY", process.stdout.readline().strip())
                        process.kill()
                        process.communicate(timeout=15)
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.communicate()
                    with closing(sqlite3.connect(path)) as conn:
                        self.assertEqual(2 if committed else 1, conn.execute("SELECT value FROM probe").fetchone()[0])
                        self.assertEqual("ok", conn.execute("PRAGMA integrity_check").fetchone()[0])
                        conn.execute("BEGIN IMMEDIATE")
                        conn.rollback()

    def test_reader_visibility_writer_timeout_then_restart_delete_and_wal(self):
        # Independent real Python processes, explicit stdout handshake. These
        # observations describe this local filesystem only, never PythonAnywhere.
        for mode in ("DELETE", "WAL"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                path = Path(root) / "synthetic.sqlite"
                with closing(sqlite3.connect(path)) as writer:
                    self.assertEqual(mode.lower(), writer.execute("PRAGMA journal_mode=" + mode).fetchone()[0])
                    writer.execute("CREATE TABLE probe(value INTEGER)")
                    writer.execute("INSERT INTO probe VALUES(1)")
                    writer.commit()
                    writer.execute("BEGIN IMMEDIATE")
                    writer.execute("UPDATE probe SET value=2")
                    code = '''import sqlite3,sys,json
c=sqlite3.connect(sys.argv[1], timeout=0.1)
print("READY",flush=True)
assert sys.stdin.readline().strip()=="GO"
old=c.execute("SELECT value FROM probe").fetchone()[0]
try:
 c.execute("BEGIN IMMEDIATE")
except sqlite3.OperationalError as exc:
 assert "locked" in str(exc)
 print(json.dumps(dict(visible=old,writer="locked")),flush=True)
else:
 raise AssertionError("concurrent writer admitted")
c.close()
'''
                    process = subprocess.Popen([sys.executable, "-B", "-u", "-c", code, str(path)],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    try:
                        self.assertEqual("READY", process.stdout.readline().strip())
                        out, err = process.communicate("GO\n", timeout=15)
                        self.assertEqual(0, process.returncode, err)
                        self.assertEqual(dict(visible=1, writer="locked"), json.loads(out))
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.communicate()
                    writer.commit()
                result = subprocess.run([sys.executable, "-B", "-c",
                    "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('BEGIN IMMEDIATE'); "
                    "assert c.execute('SELECT value FROM probe').fetchone()[0]==2; "
                    "assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'; c.rollback(); c.close()", str(path)],
                    capture_output=True, text=True, timeout=15)
                self.assertEqual(0, result.returncode, result.stderr)
