"""Production-format local records on fresh disposable fixtures only."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
import hashlib
import json
import socket
import sqlite3
import subprocess
import sys
import threading
import io
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import production_operations as d, operations, approvals as b, admin_auth as m
from src.review.recognition import local_execution as c, administration as a, authority, trust, enrollment, activation, permanent
from tests import test_recognition_local_execution as slice_c
from tests.test_recognition_administration import at, independent_code, INSTALLATION


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


class ProductionOperationTests(unittest.TestCase):
    setUp = slice_c.LocalExecutionTests.setUp
    sql = slice_c.LocalExecutionTests.sql
    new_operation = slice_c.LocalExecutionTests.new_operation
    approve = slice_c.LocalExecutionTests.approve
    enrolled = slice_c.LocalExecutionTests.enrolled
    authenticated = slice_c.LocalExecutionTests.authenticated
    counts = slice_c.LocalExecutionTests.counts
    execute = slice_c.LocalExecutionTests.execute
    recover = slice_c.LocalExecutionTests.recover

    def request(self, geography=False):
        request = self.fixture.request(geography=geography)
        return dict(request_id=str(uuid4()), family=request["family"], inputs=request["inputs"],
                    evaluation_at_utc=request["evaluation_at_utc"], review_reference="owner-reviewed-local-population", parent_operation_id=None)

    def create(self, request=None):
        result = d.create_operation(self.config, self.session, request or self.request(), now=at(90))
        self.operation = result
        self.oid = result["envelope"]["operation_id"]
        return result

    def approved(self):
        self.create()
        self.approve(90)
        return self.operation

    def test_first_look_exact_bindings_without_synthetic_providers(self):
        with patch.object(authority, "DisposableWorkspace", side_effect=AssertionError("synthetic authority")), \
             patch.object(trust, "SyntheticTrustProvider", side_effect=AssertionError("trust provider")), \
             patch.object(enrollment, "SyntheticEnrollmentWorkspace", side_effect=AssertionError("enrollment provider")):
            result = self.create()
        e = result["envelope"]
        self.assertEqual("recognition-local-operation-v1", e["format"])
        self.assertEqual((1, "first_look", "PREPARED"), (e["operation_version"], e["family"], e["initial_state"]))
        self.assertNotIn("synthetic_contract_only", e)
        self.assertNotIn("enrollment", e)
        self.assertEqual(sha(e), result["operation_sha256"])
        target = e["local_target"]
        self.assertEqual((INSTALLATION, 1), (target["installation_id"], target["restore_generation"]))
        stat = self.path.stat()
        self.assertEqual(dict(hostname=socket.gethostname(), database=str(self.path.resolve()), device=stat.st_dev, inode=stat.st_ino), e["target_observation"])
        with a.connect(self.path) as conn:
            frozen = c.events.get_event(conn, e["event_id"])
        self.assertEqual(sha(frozen["event"]), e["event_sha256"])
        self.assertEqual(sha(frozen["preparation"]), e["preparation_sha256"])
        self.assertEqual(sha(frozen["preparation"]["dependencies"]), e["dependencies_sha256"])
        self.assertEqual(sha(frozen["preparation"]["manifest"]["candidates"]), e["population_sha256"])
        self.assertEqual(1, len(e["member_ids"]))
        self.assertEqual([], e["accounting_policy"]["quarantine_categories"])
        self.assertEqual("recognition-local-operation-history-v1", result["decisions"][0]["format"])

    def test_geography_frozen_membership_evaluation(self):
        for n in range(2, 6):
            self.fixture.review(n)
        request = self.request(True)
        result = self.create(request)
        with a.connect(self.path) as conn:
            frozen = c.events.get_event(conn, result["envelope"]["event_id"])["preparation"]["manifest"]
        self.assertEqual("geography_steward", result["envelope"]["family"])
        self.assertEqual(request["evaluation_at_utc"], frozen["evaluation_at_utc"])
        self.assertEqual(request["inputs"]["scope_snapshot"], frozen["inputs"]["scope_snapshot"])
        self.assertEqual({10}, {x["denominator"] for x in frozen["candidates"]})
        self.assertEqual(2, len(result["envelope"]["member_ids"]))

    def test_creation_idempotent_and_concurrent(self):
        request = self.request()
        barrier = threading.Barrier(2)
        def create():
            barrier.wait()
            return d.create_operation(self.config, self.session, request, now=at(90))
        with ThreadPoolExecutor(2) as pool:
            first, second = list(pool.map(lambda _: create(), range(2)))
        self.assertEqual(first, second)
        self.assertEqual(first, self.create(request))
        bad = dict(request, review_reference="another-request")
        with self.assertRaises(a.AdminError):
            self.create(bad)

    def test_no_arbitrary_writer_callable_sql_or_family(self):
        for extra in ({"writer": "finalize"}, {"actor_id": 1}, {"sql": "DELETE FROM recognition_awards"}, {"callback": lambda: None}, {"production": True}):
            with self.subTest(fields=list(extra)), self.assertRaises(a.AdminError):
                self.create(dict(self.request(), **extra))
        for family in ("explorer", "VOID", "SUPERSEDE", "REINSTATE", "GRANT_MISSING", "other"):
            with self.subTest(family=family), self.assertRaises(a.AdminError):
                self.create(dict(self.request(), family=family))

    def test_revision_immutable_history_and_old_approval_invalidation(self):
        old = self.approved()
        old_id, old_aid = self.oid, self.aid
        revised = self.create(dict(self.request(), parent_operation_id=old_id))
        self.assertNotEqual(old_id, revised["envelope"]["operation_id"])
        with a.connect(self.path) as conn:
            historical = operations.get_operation(conn, old_id)
        self.assertEqual(old["envelope"], historical["envelope"])
        self.assertEqual("SUPERSEDED", historical["decisions"][-1]["state"])
        self.assertEqual(old["envelope"]["event_id"], revised["envelope"]["parent_event_id"])
        self.assertEqual("INVALIDATED", b.get_approval(self.config, self.session, old_aid, now=at(90))["state"])
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql("UPDATE recognition_operation_contracts SET body_json='{}' WHERE operation_id=?", (old_id,))

    def test_slice_b_approval_and_slice_c_verification_gate(self):
        self.approved()
        self.assertEqual(sha(self.operation["envelope"]), self.approval["approval"]["binding"]["operation_sha256"])
        self.assertFalse(self.approval["approval"]["binding"]["synthetic_contract_only"])
        context = d.load_context(self.config, self.oid)
        preview = c.verify_approved_operation(context, self.session, self.aid, now=at(90))
        self.assertEqual("production_activation_deployment_blocked", preview.reason)
        with patch.object(permanent, "finalize", side_effect=AssertionError("production writer")):
            result = c.execute_approved_operation(context, self.session, self.aid, now=at(90))
        self.assertEqual("WAITING", result.state)
        self.assertEqual("operation_context_consumed", c.execute_approved_operation(context, self.session, self.aid, now=at(90)).reason)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_context_exact_operation_and_target_not_public_constructor(self):
        self.approved()
        context = d.load_context(self.config, self.oid)
        wrong_aid = self.sql("SELECT approval_id FROM recognition_approvals WHERE operation_id!=?", (self.oid,), control=True)[0][0]
        self.assertEqual("BLOCKED", c.execute_approved_operation(context, self.session, wrong_aid, now=at(90)).admission)
        with self.assertRaises(TypeError):
            d.ProductionOperationContext()
        with self.assertRaises(TypeError):
            d.ApprovalContinuation()
        self.sql("UPDATE recognition_local_installation SET target_id='wrong'")
        with self.assertRaises(a.AdminError):
            d.load_context(self.config, self.oid)

    def test_worker_restart_pending_approval_survives_without_mutation(self):
        self.approved()
        for _ in range(2):
            pending = d.discover_pending(self.config)
            self.assertEqual([dict(approval_id=self.aid, operation_id=self.oid)], pending)
            result = d.continue_pending(self.config, now=at(90))
            self.assertEqual("WAITING", result[0]["execution"]["state"])
            self.assertEqual("APPROVED_WAITING", d.inspect_operation(self.config, self.oid)["state"])
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_two_workers_same_pending_operation(self):
        self.approved()
        barrier = threading.Barrier(2)
        def run():
            barrier.wait()
            return d.continue_pending(self.config, now=at(90))
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(["WAITING", "WAITING"], [r[0]["execution"]["state"] for r in results])
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_worker_stale_and_invalidated_approval_cannot_execute(self):
        self.approved()
        captured = d.discover_pending(self.config)
        b.invalidate_approval(self.config, self.session, self.step, self.aid, reason="changed decision", now=at(90))
        with patch.object(d, "discover_pending", return_value=captured):
            results = d.continue_pending(self.config, now=at(90))
        self.assertEqual("BLOCKED", results[0]["execution"]["admission"])
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_worker_stale_dependency_is_terminally_blocked(self):
        self.approved()
        self.sql("UPDATE stop_review_assignments SET status='pending' WHERE id=1")
        self.assertEqual("BLOCKED", d.continue_pending(self.config, now=at(90))[0]["execution"]["admission"])
        self.assertEqual([], d.discover_pending(self.config))

    def test_worker_generation_change_blocks(self):
        self.approved()
        with a.connect(self.path) as conn:
            observation = a.observe_target(conn)
        a.advance_restore_generation(self.config, expected_generation=1, expected_target_sha256=sha(observation), operator="disposable-host", reason="restore", now=at(90))
        self.assertEqual([], d.discover_pending(self.config))
        with self.assertRaises(a.AdminError):
            d.load_context(self.config, self.oid)

    def test_worker_stop_and_disposable_readiness_cannot_enable_production(self):
        self.approved()
        self.workspace.set_stop(active=True, now=at(90))
        result = d.continue_pending(self.config, now=at(90))
        self.assertEqual("emergency_stop", result[0]["execution"]["reason"])
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_completed_disposable_operation_inspection_survives_restart(self):
        self.assertEqual("COMPLETED", self.execute().state)
        for _ in range(2):
            self.assertEqual("COMPLETED", d.inspect_operation(self.config, self.oid)["state"])
            self.assertEqual([], d.discover_pending(self.config))
        self.assertEqual((1, 1, 1, 1), self.counts())

    def test_recovery_required_operation_remains_fenced(self):
        def fail(point):
            if point == "C":
                raise c.journal.SimulatedInterruption("claim")
        with patch.object(c, "_fault", side_effect=fail), self.assertRaises(c.journal.SimulatedInterruption):
            self.execute()
        for _ in range(2):
            self.assertEqual("UNKNOWN_RECOVERY_REQUIRED", d.inspect_operation(self.config, self.oid)["state"])
        self.assertEqual((1, 0, 0, 0), self.counts())

    def test_schema_install_idempotent_and_rollback(self):
        with a.connect(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            d.install_target(conn)
            d.install_target(conn)
            conn.rollback()
        with a.connect(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with patch.object(d.execution_schema, "check_schema", side_effect=RuntimeError("migration fault")):
                with self.assertRaises(RuntimeError):
                    d.install_target(conn)
            conn.commit()
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_operation_approved_during_scan_is_seen_next_scan(self):
        self.create()
        scanned, release = threading.Event(), threading.Event()
        original = d.discover_pending
        def snapshot(config, **kwargs):
            result = original(config, **kwargs)
            scanned.set()
            self.assertTrue(release.wait(10))
            return result
        with patch.object(d, "discover_pending", side_effect=snapshot), ThreadPoolExecutor(1) as pool:
            future = pool.submit(d.continue_pending, self.config, now=at(90))
            self.assertTrue(scanned.wait(10))
            self.approve(90)
            release.set()
            self.assertEqual([], future.result())
        self.assertEqual(1, len(d.continue_pending(self.config, now=at(90))))
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_fresh_process_workers_can_reconstruct_pending_context(self):
        self.approved()
        script = """
import sys,json,pathlib
from src.review.recognition import administration as a, production_operations as d
def audit(event,args):
    if event in ('socket.connect','socket.getaddrinfo'):
        raise RuntimeError('external_network_disabled')
sys.addaudithook(audit)
request=json.loads(sys.stdin.read())
config=a.LocalAdministration(*(pathlib.Path(p) for p in request['paths']))
print(json.dumps(d.continue_pending(config,now=request['now'])))
"""
        payload = json.dumps(dict(paths=[str(self.path), str(self.control), str(self.key_file)], now=at(90)))
        def run():
            process = subprocess.run([sys.executable, "-B", "-c", script], input=payload, text=True, capture_output=True, timeout=30)
            self.assertEqual(0, process.returncode, process.stderr)
            return json.loads(process.stdout)
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(["WAITING", "WAITING"], [r[0]["execution"]["state"] for r in results])
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_browser_contract_creation_approval_and_rejected_authority_fields(self):
        from src.api import app as api
        from src.review.recognition import admin_routes
        with patch.object(api, "DATABASE_PATH", self.path), patch.dict(api.app.config, dict(TESTING=True, SECRET_KEY="slice-d-disposable-only",
                RECOGNITION_ADMIN_CONTROL=str(self.control), RECOGNITION_ADMIN_KEY_FILE=str(self.key_file))), patch.object(admin_routes, "now_utc", return_value=at(90)):
            client = api.app.test_client()
            with client.session_transaction() as browser:
                browser.update(authenticated_reviewer_id=1, reviewer_key="owner-key", recognition_primary=self.primary,
                               recognition_admin=self.session, auth_csrf="test-csrf")
            request = self.request()
            for extra in ({"actor_id": 1}, {"writer": "finalize"}, {"target": str(self.path)}, {"execution_capability": "approved"}):
                with self.subTest(extra=extra):
                    response = client.post("/api/admin/recognition-control/operations", json=dict(request, csrf_token="test-csrf", **extra))
                    self.assertEqual(400, response.status_code)
            response = client.post("/api/admin/recognition-control/operations", json=dict(request, csrf_token="test-csrf"))
            self.assertEqual(201, response.status_code, response.get_json())
            self.operation = response.get_json()
            self.oid = self.operation["envelope"]["operation_id"]
            step = m.create_step_up(self.config, self.session, independent_code(at(90)), action="approve", operation_id=self.oid, now=at(90))
            token = m.begin_operation_confirmation(self.config, self.session, step, operation_id=self.oid, now=at(90))
            result = client.post("/api/admin/recognition-control/operations/"+self.oid+"/approve", json=dict(
                step_up_token=step, confirmation_token=token, reason="Reviewed", csrf_token="test-csrf"))
            self.assertEqual(202, result.status_code, result.get_json())
            self.assertEqual("WAITING", result.get_json()["execution"]["state"])
            self.assertNotIn("context", result.get_json())
            self.assertEqual(200, client.get("/api/admin/recognition-control/operations/"+self.oid).status_code)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_cli_has_no_force_execute_or_approval_bypass(self):
        from scripts.active import manage_recognition_administration as cli
        for action in ("execute", "force-execute", "approve", "run-writer"):
            with self.subTest(action=action), self.assertRaises(SystemExit), patch("sys.stderr", new_callable=io.StringIO):
                cli.main([action])
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_pending_worker_requires_unexpired_original_admin_session(self):
        self.approved()
        self.assertEqual("BLOCKED", d.continue_pending(self.config, now=at(30000))[0]["execution"]["admission"])
        self.assertEqual((0, 0, 0, 0), self.counts())
        self.assertEqual("APPROVED_WAITING", d.inspect_operation(self.config, self.oid)["state"])

    def test_creation_does_not_change_explorer_or_first_look_policy(self):
        from src.review.recognition.schema import TABLES
        before = {name: self.sql("SELECT * FROM "+name) for name in TABLES}
        result = self.create()
        with a.connect(self.path) as conn:
            manifest = c.events.get_event(conn, result["envelope"]["event_id"])["preparation"]["manifest"]
        self.assertEqual([(1, 1, 1)], [(x["physical_stop_id"], x["reviewer_id"], x["assignment_id"]) for x in manifest["candidates"]])
        self.assertEqual(permanent.DEFINITIONS["first_look"], manifest["rule"])
        self.assertEqual(before, {name: self.sql("SELECT * FROM "+name) for name in TABLES})

    def test_production_descriptor_cannot_mint_writer_capability(self):
        from src.review.recognition import writer_boundary
        self.approved()
        context = d.load_context(self.config, self.oid)
        with a.connect(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(Exception, "production_writer_provisioning_unavailable"):
                with writer_boundary._local_lease(context, conn, {}, {}):
                    self.fail("production writer was provisioned")

    def test_creation_target_commit_control_audit_gap_is_recoverable(self):
        request = self.request()
        with patch.object(d, "_creation_audit", side_effect=RuntimeError("control audit interrupted")):
            with self.assertRaises(RuntimeError):
                self.create(request)
        rows = self.sql("SELECT operation_id FROM recognition_operation_contracts WHERE json_extract(body_json,'$.creation.request_id')=?", (request["request_id"],))
        self.assertEqual(1, len(rows))
        result = self.create(request)
        self.assertEqual(rows[0][0], result["envelope"]["operation_id"])
        self.assertEqual([(1,)], self.sql("SELECT COUNT(*) FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')='production_operation_created' AND json_extract(body_json,'$.subject.operation_id')=?", (rows[0][0],), control=True))
        self.assertEqual((0, 0, 0, 0), self.counts())
