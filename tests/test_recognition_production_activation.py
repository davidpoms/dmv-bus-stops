"""Slice G trusted-local path exercised ONLY on fresh synthetic owned files."""

from concurrent.futures import ThreadPoolExecutor
import os
import io
import secrets
import json
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from tests import test_recognition_readiness_receipts as fixtures
from tests.test_recognition_administration import at
from src.review.recognition import administration as a, admin_auth as m, approvals as b, local_readiness as r, local_execution as c
from src.review.recognition import production_operations as d, permanent, authority, writer_boundary
from src.review.recognition.rules import digest


class ProductionActivationTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ReadinessReceiptTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.clock = self.enterContext(patch.object(c, "_utc_now", return_value=at(120)))

    def confirmation(self):
        self.f.deployment()
        self.step = self.f.fresh_step("activate", 120)
        result = r.begin_activation_confirmation(self.f.config, self.f.session, self.step, now=at(120))
        self.token = result["confirmation_token"]
        return result

    def activate(self):
        self.confirmation()
        return self.change()

    def change(self, seconds=120, token=None, step=None):
        self.clock.return_value = at(seconds)
        return r.change_state(self.f.config, self.f.session, step or self.step, state="ACTIVATED",
            reason="explicit synthetic owner approval; never a deployed installation", now=at(seconds),
            confirmation_token=self.token if token is None else token)

    def execute(self, seconds=120):
        self.clock.return_value = at(seconds)
        context = d.load_context(self.f.config, self.f.oid)
        return c.execute_approved_operation(context, self.f.session, self.f.aid, now=at(seconds))

    def test_ceremony_then_fixed_writer_receipt_and_restart_idempotence(self):
        before = self.f.counts()
        result = self.confirmation()
        self.assertEqual("NOT_ACTIVATED", result["readiness"]["activation_state"])
        self.assertEqual(before, self.f.counts())
        state = self.change()
        self.assertEqual(("ACTIVATED", "trusted-local-production"), (state["state"], state["scope"]))
        self.assertEqual(digest(r._assessment_binding(result["readiness"])), state["readiness_sha256"])
        self.assertEqual("FINAL_ADMISSION_REQUIRED", r.assess(self.f.config, now=at(120))["production_execution"])
        self.assertEqual("COMPLETED", self.execute().state)
        self.assertEqual("trusted-local-production", self.f.seal()["receipt"]["execution_scope"])
        self.assertEqual(digest(state), self.f.seal()["receipt"]["activation_sha256"])
        self.assertEqual("ALREADY_EXECUTED", self.execute().admission)
        self.assertEqual((1, 1, 1, 1), self.f.counts())
        self.assertEqual([], d.discover_pending(self.f.config))

    def test_readiness_without_deployment_never_activates(self):
        step = self.f.fresh_step("activate", 120)
        with self.assertRaises(a.AdminError):
            r.begin_activation_confirmation(self.f.config, self.f.session, step, now=at(120))
        self.assertEqual("NOT_ACTIVATED", r.assess(self.f.config, now=at(120))["activation_state"])

    def test_missing_confirmation_cannot_activate(self):
        self.confirmation()
        result = r.change_state(self.f.config, self.f.session, self.step, state="ACTIVATED", reason="missing token", now=at(120))
        self.assertEqual("BLOCKED", result["result"])
        self.assertEqual((0, 0, 0, 0), self.f.counts())

    def test_operation_confirmation_cannot_activate(self):
        self.confirmation()
        with self.assertRaises(a.AdminError):
            self.change(token=self.f.token)

    def test_wrong_owner_is_denied(self):
        self.confirmation()
        self.f.sql("UPDATE community_reviewers SET role='review_lead' WHERE id=1")
        with self.assertRaises(a.AdminError):
            self.change()

    def test_missing_and_expired_step_up(self):
        self.confirmation()
        with self.assertRaises(a.AdminError):
            self.change(step="x" * 32)
        with self.assertRaises(a.AdminError):
            self.change(seconds=721)

    def test_expired_confirmation_with_fresh_step_up_is_rejected(self):
        self.confirmation()
        fresh = self.f.fresh_step("activate", 750)
        with self.assertRaisesRegex(a.AdminError, "invalid_or_stale_activation_confirmation"):
            self.change(seconds=750, step=fresh)

    def test_activation_refreshes_time_after_waiting_for_locks(self):
        self.confirmation()
        self.clock.return_value = at(750)
        with self.assertRaisesRegex(a.AdminError, "recent_step_up_required"):
            r.change_state(self.f.config, self.f.session, self.step, state="ACTIVATED", reason="old request timestamp",
                           confirmation_token=self.token, now=at(120))
        self.assertEqual([(0,)], self.f.sql("SELECT used FROM recognition_admin_confirmations WHERE token_hash=?", (a.token_hash(self.token),), control=True))

    def test_changed_dependencies_block_confirmation_and_execution(self):
        self.confirmation()
        self.f.sql("UPDATE stop_review_assignments SET status='pending' WHERE id=1")
        with self.assertRaises(a.AdminError):
            self.change()
        self.assertNotEqual("COMPLETED", self.execute().state)
        self.assertEqual((0, 0, 0, 0), self.f.counts())

    def test_confirmation_one_use_after_deactivation(self):
        self.activate()
        step = self.f.fresh_step("deactivate", 150)
        r.change_state(self.f.config, self.f.session, step, state="DEACTIVATED", reason="synthetic pause", now=at(150))
        fresh = self.f.fresh_step("activate", 180)
        with self.assertRaises(a.AdminError):
            self.change(seconds=180, step=fresh)
        self.assertNotEqual("COMPLETED", self.execute(180).state)

    def test_confirmation_binds_current_state(self):
        self.confirmation()
        step = self.f.fresh_step("suspend", 150)
        r.change_state(self.f.config, self.f.session, step, state="SUSPENDED", reason="state changed", now=at(150))
        fresh = self.f.fresh_step("activate", 180)
        with self.assertRaises(a.AdminError):
            self.change(seconds=180, step=fresh)

    def test_confirmation_binds_deployment_readiness(self):
        self.confirmation()
        self.f.deployment(120)
        with self.assertRaises(a.AdminError):
            self.change()

    def test_confirmation_binds_restore_generation(self):
        self.confirmation()
        with a.connect(self.f.path) as conn:
            preview = digest(a.observe_target(conn))
        a.advance_restore_generation(self.f.config, expected_generation=1, expected_target_sha256=preview,
            operator="synthetic-host", reason="deliberate synthetic rebind", now=at(120))
        with self.assertRaises(a.AdminError):
            self.change()
        self.assertEqual("NOT_ACTIVATED", r.assess(self.f.config, now=at(120))["activation_state"])

    def test_stop_blocks_activation_and_execution(self):
        self.confirmation()
        self.f.workspace.set_stop(active=True, now=at(120))
        with self.assertRaises(a.AdminError):
            self.change()

    def test_stop_after_activation_blocks_new_writer(self):
        self.activate()
        self.f.workspace.set_stop(active=True, now=at(120))
        self.assertEqual("emergency_stop", self.execute().reason)
        self.assertEqual((0, 0, 0, 0), self.f.counts())

    def test_suspension_blocks_new_writer(self):
        self.activate()
        step = self.f.fresh_step("suspend", 150)
        r.change_state(self.f.config, self.f.session, step, state="SUSPENDED", reason="synthetic pause", now=at(150))
        self.assertNotEqual("COMPLETED", self.execute(150).state)

    def test_concurrent_activation_consumes_once(self):
        self.confirmation()
        barrier = threading.Barrier(2)
        def run():
            barrier.wait()
            try:
                return self.change()["state"]
            except a.AdminError:
                return "DENIED"
        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(["ACTIVATED", "DENIED"], sorted(pool.map(lambda _: run(), range(2))))
        self.assertEqual([(1,)], self.f.sql("SELECT COUNT(*) FROM recognition_local_activation WHERE json_extract(body_json,'$.state')='ACTIVATED'", control=True))

    def test_concurrent_execution_uses_one_claim(self):
        self.activate()
        barrier = threading.Barrier(2)
        def run():
            barrier.wait()
            return self.execute().admission
        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(["ADMITTED", "ALREADY_EXECUTED"], sorted(pool.map(lambda _: run(), range(2))))
        self.assertEqual((1, 1, 1, 1), self.f.counts())

    def test_fixture_state_environment_and_raw_context_cannot_bypass(self):
        self.f.activate()  # Old explicit simulation is not a production ceremony.
        with patch.dict(os.environ, {"RECOGNITION_ACTIVATED": "1", "PRODUCTION_WRITER_ENABLED": "1"}):
            self.assertEqual("production_activation_deployment_blocked", self.execute().reason)
        with self.assertRaises(TypeError):
            writer_boundary.LocalExecutionCapability()
        with self.assertRaises(Exception):
            authority.provision_production_authority()
        self.assertEqual((0, 0, 0, 0), self.f.counts())

    def test_arbitrary_writer_and_synthetic_operation_cannot_enter(self):
        with self.assertRaises(a.AdminError):
            d.create_operation(self.f.config, self.f.session, dict(self.f.request(), writer="arbitrary"), now=at(90))
        self.f.new_operation()
        with self.assertRaises(a.AdminError):
            d.load_context(self.f.config, self.f.oid)

    def test_uncertain_commit_recovery_projects_without_second_writer(self):
        self.activate()
        def fail(point):
            if point == "E":
                raise c.journal.SimulatedInterruption("seal committed before projection")
        with patch.object(c, "_fault", side_effect=fail), self.assertRaises(c.journal.SimulatedInterruption):
            self.execute()
        self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
        context = d.load_recovery_context(self.f.config, self.f.oid)
        with patch.object(permanent, "finalize", side_effect=AssertionError("blind writer retry")):
            self.assertEqual("ALREADY_EXECUTED", self.f.recover(context=context).admission)
        self.assertEqual((1, 1, 1, 1), self.f.counts())

    def test_atomic_activation_rolls_back_confirmation_on_history_failure(self):
        self.confirmation()
        with patch.object(r, "_append", side_effect=RuntimeError("history interrupted")), self.assertRaises(RuntimeError):
            self.change()
        self.assertEqual([(0,)], self.f.sql("SELECT used FROM recognition_admin_confirmations WHERE token_hash=?", (a.token_hash(self.token),), control=True))
        self.assertEqual("ACTIVATED", self.change()["state"])

    def test_geography_uses_same_production_capability_and_frozen_receipt(self):
        for number in range(2, 6):
            self.f.fixture.review(number)
        self.assertEqual("INVALIDATED", b.get_approval(self.f.config, self.f.session, self.f.aid, now=at(90))["state"])
        self.f.create(self.f.request(True))
        self.f.approve(120)
        self.f.deployment(120)
        step = self.f.fresh_step("activate", 150)
        self.clock.return_value = at(150)
        token = r.begin_activation_confirmation(self.f.config, self.f.session, step, now=at(150))["confirmation_token"]
        r.change_state(self.f.config, self.f.session, step, state="ACTIVATED", reason="synthetic geography review",
            confirmation_token=token, now=at(150))
        self.assertEqual("COMPLETED", self.execute(150).state)
        receipt = self.f.seal()["receipt"]
        self.assertEqual(("geography_steward", "trusted-local-production", 2),
            (receipt["writer_family"], receipt["execution_scope"], receipt["authorized_count"]))
        self.assertEqual(10, len(receipt["actual_records"]["recognition_geography_members"]))

    def test_approval_automatically_enters_existing_production_coordinator(self):
        self.f.create()
        self.activate()
        step = self.f.fresh_step("approve", 150, self.f.oid)
        token = m.begin_operation_confirmation(self.f.config, self.f.session, step, operation_id=self.f.oid, now=at(150))
        self.clock.return_value = at(150)
        result = c.approve_and_execute(self.f.config, self.f.session, step, token, operation_id=self.f.oid,
            reason="synthetic exact population approval", now=at(150))
        self.assertEqual("COMPLETED", result["execution"]["state"])
        self.assertFalse(result["execution_pending"])

    def test_http_ceremony_strict_fields_csrf_and_owner_only(self):
        from src.api import app as api
        from src.review.recognition import admin_routes
        self.f.deployment()
        step = self.f.fresh_step("activate", 120)
        with patch.object(api, "DATABASE_PATH", self.f.path), patch.dict(api.app.config, dict(TESTING=True,
                SECRET_KEY=secrets.token_urlsafe(32), RECOGNITION_ADMIN_CONTROL=str(self.f.control),
                RECOGNITION_ADMIN_KEY_FILE=str(self.f.key_file))), patch.object(admin_routes, "now_utc", return_value=at(120)):
            client = api.app.test_client()
            with client.session_transaction() as browser:
                browser.update(authenticated_reviewer_id=1, reviewer_key="owner-key", recognition_primary=self.f.primary,
                               recognition_admin=self.f.session, auth_csrf="test-csrf")
            route = "/api/admin/recognition-control/activation"
            self.assertEqual(400, client.post(route+"/confirmations", json=dict(step_up_token=step)).status_code)
            response = client.post(route+"/confirmations", json=dict(step_up_token=step, csrf_token="test-csrf"))
            self.assertEqual(200, response.status_code, response.get_json())
            token = response.get_json()["confirmation_token"]
            body = dict(state="ACTIVATED", step_up_token=step, confirmation_token=token, reason="explicit synthetic ceremony", csrf_token="test-csrf")
            for extra in ({"force": True}, {"writer": "finalize"}, {"fixture": True}, {"target": str(self.f.path)}):
                self.assertEqual(400, client.post(route, json=dict(body, **extra)).status_code)
            self.assertEqual(200, client.post(route, json=body).status_code)
            with client.session_transaction() as browser:
                browser["authenticated_reviewer_id"] = 2
            self.assertEqual(403, client.post(route, json=body).status_code)
        self.assertEqual((0, 0, 0, 0), self.f.counts())

    def test_cli_has_no_activation_or_writer_bypass(self):
        from scripts.active import manage_recognition_administration as cli
        for action in ("activate", "force-activate", "provision-writer", "execute"):
            with self.subTest(action=action), self.assertRaises(SystemExit), patch("sys.stderr", new_callable=io.StringIO):
                cli.main([action])

    def _fresh_worker(self):
        code = '''import sys,json,pathlib,sqlite3,urllib.parse
payload=json.load(sys.stdin)
root=pathlib.Path(payload["target"]).parent.resolve()
def audit(event,args):
 if event in ("socket.connect","socket.getaddrinfo"): raise RuntimeError("network forbidden")
 if event=="sqlite3.connect":
  raw=str(args[0])
  if raw.startswith("file:"):
   raw=urllib.parse.unquote(urllib.parse.urlsplit(raw).path)
   if raw.startswith("/") and len(raw)>2 and raw[2]==":": raw=raw[1:]
  if raw!=":memory:" and not pathlib.Path(raw).resolve().is_relative_to(root): raise RuntimeError("outside synthetic root")
sys.addaudithook(audit)
from src.review.recognition import administration as a, production_operations as d, local_execution as c
c._utc_now=lambda: payload["now"]  # Synthetic test clock; no runtime switch.
config=a.LocalAdministration(*(pathlib.Path(payload[key]) for key in ("target","control","key")))
print(json.dumps(d.continue_pending(config,now=payload["now"])))
'''
        result = subprocess.run([sys.executable, "-B", "-c", code], input=json.dumps(dict(target=str(self.f.path),
            control=str(self.f.control), key=str(self.f.key_file), now=at(120))), text=True, capture_output=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def test_fresh_process_reconstructs_approved_work_and_never_duplicates(self):
        self.activate()
        result = self._fresh_worker()
        self.assertEqual("COMPLETED", result[0]["execution"]["state"])
        self.assertEqual([], self._fresh_worker())
        self.assertEqual((1, 1, 1, 1), self.f.counts())

    def test_fresh_worker_does_not_retry_uncertain_claim(self):
        self.activate()
        def fail(point):
            if point == "C":
                raise c.journal.SimulatedInterruption("claim without seal")
        with patch.object(c, "_fault", side_effect=fail), self.assertRaises(c.journal.SimulatedInterruption):
            self.execute()
        self.assertEqual([], self._fresh_worker())
        self.assertEqual((1, 0, 0, 0), self.f.counts())

    def test_request_time_cannot_preserve_expired_approval_session(self):
        self.activate()
        self.clock.side_effect = [at(30000)]
        self.assertEqual("BLOCKED", self.execute().admission)
        self.assertEqual((0, 0, 0, 0), self.f.counts())

    def test_session_expiry_at_capability_boundary_fences_claim(self):
        self.activate()
        self.clock.side_effect = [at(120), at(120), at(30000)]
        self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
        self.assertEqual((1, 0, 0, 0), self.f.counts())

    def _crash(self, stage):
        self.activate()
        def interrupt(point):
            if point == stage:
                raise c.journal.SimulatedInterruption(stage)
        with patch.object(c, "_fault", side_effect=interrupt), self.assertRaises(c.journal.SimulatedInterruption):
            self.execute()
        expected = (0, 0, 0, 0) if stage in "AB" else ((1, 0, 0, 0) if stage in "CD" else (1, 1, 1, 1))
        self.assertEqual(expected, self.f.counts())
        if stage in "AB":
            self.assertEqual("COMPLETED", self.execute().state)
        elif stage in "CD":
            self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
            context = d.load_context(self.f.config, self.f.oid)
            with patch.object(permanent, "finalize", side_effect=AssertionError("blind retry after crash")):
                self.assertEqual("FAILED_BEFORE_COMMIT", self.f.recover(context=context).state)
                self.assertEqual("FAILED_BEFORE_COMMIT", self.execute(150).state)
        else:
            self.assertEqual("ALREADY_EXECUTED", self.execute().admission)

    def test_crash_before_verification(self): self._crash("A")
    def test_crash_before_claim(self): self._crash("B")
    def test_crash_after_claim(self): self._crash("C")
    def test_crash_during_writer(self): self._crash("D")
    def test_crash_after_projection(self): self._crash("F")
    def test_crash_lost_acknowledgement(self): self._crash("G")
