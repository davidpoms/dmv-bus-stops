"""Readiness/ceremonies on fresh disposable stores and ephemeral public-key fixtures."""

import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.review.recognition import activation as a, activation_schema, authority, execution, writer_boundary, trust
from src.review.recognition.authorization import AuthorizationError


NOW = "2099-01-01T00:00:00Z"
LATER = "2099-01-01T00:01:00Z"
EXPIRY = "2099-01-02T00:00:00Z"
GENERATIONS = {"trust": 2, "status": 3, "enrollment": 4, "deployment": 5}


def independent_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        status_key = Ed25519PrivateKey.generate()
        public = lambda k: base64.b64encode(k.public_key().public_bytes_raw()).decode()
        self.provider = trust.SyntheticTrustProvider(json.dumps(dict(registry_id="activation-test-registry",
            authority_keys=[dict(authority_id="synthetic-admin", key_id="admin-key", public_key=public(self.key),
                grants=[dict(family="first_look", action="finalize")])],
            status_keys=[dict(key_id="status-key", public_key=public(status_key))])))
        self.workspace = a.SyntheticActivationWorkspace(provider=self.provider, administrative_authority_id="synthetic-admin")
        self.addCleanup(self.workspace.cleanup)
        self.workspace.install()
        self.evidence = tuple(a.InterfaceEvidence(key, "SATISFIED", a.REQUIRED_STATES[key], NOW, EXPIRY,
            hashlib.sha256(("independent-interface-fixture:" + key).encode()).hexdigest()) for key in sorted(a.KEYS))

    def assess(self, evidence=None, **kwargs):
        return a.assess_production_readiness(installation=self.workspace,
            evidence=self.evidence if evidence is None else evidence, generations=GENERATIONS,
            trusted_now_utc=kwargs.pop("trusted_now_utc", NOW), **kwargs)

    def changed(self, key, **updates):
        return tuple(replace(e, **updates) if e.prerequisite == key else e for e in self.evidence)

    def ceremony(self, report, action="activate", **updates):
        p = a.ceremony_payload(self.workspace, report, action=action, ceremony_id=str(uuid4()),
            issued_at_utc=NOW, expires_at_utc=EXPIRY)
        p.update(updates)
        # Independent canonicalization/domain, not implementation signing helper.
        raw = b"DMV-recognition-installation-ceremony-v1\x00" + json.dumps(p,
            sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        return json.dumps(dict(payload=p, signature=base64.b64encode(self.key.sign(raw)).decode()))

    def change(self, action="activate", report=None, ceremony=None, now=NOW):
        report = self.assess() if report is None else report
        ceremony = self.ceremony(report, action) if ceremony is None else ceremony
        method = {"activate": a.activate_production, "deactivate": a.deactivate_production, "suspend": a.suspend_production}[action]
        return method(self.workspace, assessment=report, ceremony_json=ceremony, trusted_now_utc=now)

    def connection(self):
        return sqlite3.connect(self.workspace.directory / "ledger.sqlite")

    def test_production_missing_prerequisites_report_all_exact_failures(self):
        report = a.assess_production_readiness()
        body = json.loads(report.canonical_json)
        self.assertEqual("BLOCKED", report.status)
        self.assertFalse(report.production_ready)
        self.assertEqual(set(a.KEYS), {c["prerequisite"] for c in body["checks"]})
        self.assertTrue(all(c["outcome"] == "EXTERNAL_PREREQUISITE_UNVERIFIED" for c in body["checks"]))
        self.assertEqual(independent_hash(body), report.sha256)
        self.assertIn("trust_root", [c["prerequisite"] for c in body["checks"]])

    def test_synthetic_trust_provider_is_not_a_production_installation(self):
        report = a.assess_production_readiness(installation=self.provider, evidence=self.evidence,
            generations=GENERATIONS, trusted_now_utc=NOW)
        self.assertEqual("BLOCKED", report.status)
        self.assertEqual("PRODUCTION_UNPROVISIONED", json.loads(report.canonical_json)["scope"])

    def test_every_missing_required_interface_blocks_even_when_others_satisfied(self):
        for key in sorted(a.KEYS):
            with self.subTest(prerequisite=key):
                report = self.assess(tuple(e for e in self.evidence if e.prerequisite != key))
                self.assertEqual("BLOCKED", report.status)
                failure = next(c for c in json.loads(report.canonical_json)["checks"] if c["prerequisite"] == key)
                self.assertEqual("EXTERNAL_PREREQUISITE_UNVERIFIED", failure["outcome"])

    def test_stale_status_enrollment_mismatch_dependencies_schema_fallback_and_provisioning_block(self):
        failures = {"authority_status": "BLOCKED", "target_enrollment": "INTEGRITY_FAILURE",
                    "target_identity": "INTEGRITY_FAILURE", "dependencies": "BLOCKED",
                    "schema_versions": "INTEGRITY_FAILURE", "database_selection": "CONFIGURATION_ERROR",
                    "provisioning": "EXTERNAL_PREREQUISITE_UNVERIFIED"}
        for key, outcome in failures.items():
            with self.subTest(key=key, outcome=outcome):
                report = self.assess(self.changed(key, outcome=outcome))
                self.assertEqual("BLOCKED", report.status)
                self.assertEqual(outcome, next(c["outcome"] for c in json.loads(report.canonical_json)["checks"] if c["prerequisite"] == key))

    def test_dependency_stale_invalid_and_verification_failure_are_never_warnings(self):
        for native in ("STALE", "INVALID", "VERIFICATION_FAILURE"):
            with self.subTest(native=native):
                report = self.assess(self.changed("dependencies", observed_state=native))
                self.assertEqual("BLOCKED", report.status)
                self.assertEqual("BLOCKED", self.change(report=report).result)

    def test_unsafe_native_interface_states_override_satisfied_assertion(self):
        for key, native in (("authority_status", "STALE"), ("target_enrollment", "MISMATCH"),
                            ("database_selection", "FALLBACK"), ("provider_separation", "SYNTHETIC"),
                            ("provisioning", "ABSENT"), ("finality", "UNVERIFIED")):
            with self.subTest(key=key, native=native):
                report = self.assess(self.changed(key, observed_state=native))
                self.assertEqual("BLOCKED", report.status)
                self.assertIn("unsafe_interface_state", report.canonical_json)

    def test_expired_or_future_evidence_blocks(self):
        for key in ("authority_status", "trusted_time", "target_enrollment", "trust_root"):
            with self.subTest(key=key):
                self.assertEqual("BLOCKED", self.assess(self.changed(key, expires_at_utc=LATER), trusted_now_utc=LATER).status)
                self.assertEqual("BLOCKED", self.assess(self.changed(key, observed_at_utc=LATER)).status)

    def test_unavailable_repository_writer_recovery_and_stop_block(self):
        for module, name in ((writer_boundary, "production_guard"), (execution, "reconcile_operation"),
                             (execution, "set_emergency_stop")):
            with self.subTest(name=name), patch.object(module, name, None):
                report = self.assess()
                self.assertEqual("BLOCKED", report.status)
                self.assertIn("INTEGRITY_FAILURE", report.canonical_json)

    def test_all_interface_doubles_ready_but_not_production_ready(self):
        report = self.assess()
        self.assertEqual("READY_FOR_ACTIVATION", report.status)
        self.assertFalse(report.production_ready)
        self.assertEqual("DISPOSABLE_INTERFACE_DOUBLES", json.loads(report.canonical_json)["scope"])
        self.assertEqual("NOT_ACTIVATED", a.get_activation_state(self.workspace).state)
        self.assertEqual("NOT_ACTIVATED", a.get_activation_state().state)

    def test_readiness_is_read_only_and_never_migrates_or_invokes_writer(self):
        with closing(self.connection()) as conn, conn:
            before = list(conn.iterdump())
        with patch.object(activation_schema, "install", side_effect=AssertionError("migration")), \
             patch.object(execution, "execute_operation", side_effect=AssertionError("writer")):
            self.assertEqual("READY_FOR_ACTIVATION", self.assess().status)
        with closing(self.connection()) as conn, conn:
            self.assertEqual(before, list(conn.iterdump()))

    def test_explicit_signed_activation_durable_and_independent_audit_expectations(self):
        report = self.assess()
        ceremony = self.ceremony(report)
        result = self.change(report=report, ceremony=ceremony)
        self.assertEqual(("ACTIVATED", "ACTIVATED", 1, False),
            (result.result, result.state.state, result.state.sequence, result.state.production_admitted))
        self.assertEqual(result.state, a.get_activation_state(self.workspace))
        with closing(self.connection()) as conn:
            serialized, sha = conn.execute("SELECT body_json,body_sha256 FROM recognition_activation_history").fetchone()
        row = json.loads(serialized)
        self.assertEqual(independent_hash(row), sha)
        self.assertEqual(("activate", "synthetic-admin", "NOT_ACTIVATED", "ACTIVATED", NOW, None),
            tuple(row[k] for k in ("action", "actor", "prior_state", "new_state", "timestamp_utc", "previous_sha256")))
        self.assertEqual(GENERATIONS, row["readiness"]["generations"])
        self.assertEqual(independent_hash(json.loads(report.canonical_json)), json.loads(ceremony)["payload"]["readiness_sha256"])

    def test_repeated_activation_exact_ceremony_is_deterministic_after_expiry(self):
        report = self.assess()
        ceremony = self.ceremony(report)
        first = self.change(report=report, ceremony=ceremony)
        replay = self.change(report=report, ceremony=ceremony, now="2099-01-03T00:00:00Z")
        self.assertEqual("ALREADY_ACTIVATED", replay.result)
        self.assertEqual(first.state, replay.state)
        self.assertEqual("ALREADY_ACTIVATED", self.change().result)

    def test_concurrent_activation_ceremony_applies_once(self):
        report = self.assess()
        ceremony = self.ceremony(report)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.change(report=report, ceremony=ceremony), range(2)))
        self.assertEqual(["ACTIVATED", "ALREADY_ACTIVATED"], sorted(r.result for r in results))
        self.assertEqual(1, a.get_activation_state(self.workspace).sequence)

    def test_deactivation_durable_and_reactivation_requires_new_ceremony(self):
        self.assertEqual("ACTIVATED", self.change().result)
        self.assertEqual("DEACTIVATED", self.change("deactivate").result)
        self.assertEqual(("DEACTIVATED", 2), (a.get_activation_state(self.workspace).state, a.get_activation_state(self.workspace).sequence))
        self.assertEqual("ACTIVATED", self.change().result)
        self.assertEqual(3, a.get_activation_state(self.workspace).sequence)

    def test_suspension_durable_and_distinct_from_emergency_stop(self):
        self.change()
        with patch.object(execution, "set_emergency_stop", side_effect=AssertionError("stop changed")):
            self.assertEqual("SUSPENDED", self.change("suspend").result)
        self.assertEqual("SUSPENDED", a.get_activation_state(self.workspace).state)
        self.assertEqual("DEACTIVATED", self.change("deactivate").result)

    def test_safety_transitions_allowed_with_blocked_readiness(self):
        self.change()
        blocked = self.assess(self.changed("authority_status", outcome="BLOCKED"))
        self.assertEqual("SUSPENDED", self.change("suspend", report=blocked).result)

    def test_bad_signature_wrong_identity_and_wrong_action_rejected(self):
        report = self.assess()
        for update in ({"authority_id": "application-admin"}, {"action": "deactivate"},
                       {"installation_id": str(uuid4())}, {"generations": {**GENERATIONS, "enrollment": 9}}):
            with self.subTest(update=update):
                self.assertEqual("BLOCKED", self.change(report=report, ceremony=self.ceremony(report, **update)).result)
        value = json.loads(self.ceremony(report))
        value["signature"] = base64.b64encode(bytes(64)).decode()
        self.assertEqual("BLOCKED", self.change(report=report, ceremony=json.dumps(value)).result)
        self.assertEqual(0, a.get_activation_state(self.workspace).sequence)

    def test_stale_ceremony_after_state_change_cannot_reactivate(self):
        report = self.assess()
        old = self.ceremony(report)
        self.change()
        self.change("deactivate")
        self.assertEqual("BLOCKED", self.change(report=report, ceremony=old).result)

    def test_expired_ceremony_and_evidence_cannot_enter(self):
        report = self.assess()
        self.assertEqual("BLOCKED", self.change(report=report, now=EXPIRY).result)
        ceremony = self.ceremony(report, expires_at_utc="2099-01-03T00:00:00Z")
        self.assertEqual("BLOCKED", self.change(report=report, ceremony=ceremony, now=EXPIRY).result)

    def test_fabricated_or_cross_installation_assessment_rejected(self):
        report = self.assess()
        fake = a.ReadinessAssessment(report.canonical_json, report.sha256)
        self.assertEqual("BLOCKED", self.change(report=fake, ceremony=self.ceremony(report)).result)
        other = a.SyntheticActivationWorkspace(provider=self.provider, administrative_authority_id="synthetic-admin")
        self.addCleanup(other.cleanup)
        other.install()
        self.assertEqual("BLOCKED", a.activate_production(other, assessment=report,
            ceremony_json=self.ceremony(report), trusted_now_utc=NOW).result)

    def test_no_boolean_role_environment_or_database_authorization(self):
        for obj in (True, "admin", {"role": "executive"}, {"activated": True}, self.provider):
            with self.subTest(obj=type(obj).__name__):
                self.assertEqual("BLOCKED", a.activate_production(obj, assessment=True, ceremony_json=True).result)
        with patch.dict(os.environ, {"RECOGNITION_ACTIVATED": "1", "FORCE_PRODUCTION": "1"}):
            self.assertEqual("BLOCKED", a.assess_production_readiness().status)
            self.assertEqual("BLOCKED", a.activate_production().result)
        with closing(self.connection()) as conn, conn:
            conn.execute("CREATE TABLE activation_flags (activated INTEGER)")
            conn.execute("INSERT INTO activation_flags VALUES(1)")
        self.assertEqual("BLOCKED", self.assess().status)

    def test_audit_update_delete_replace_rejected_with_recursive_triggers_off(self):
        self.change()
        with closing(self.connection()) as conn, conn:
            conn.execute("PRAGMA recursive_triggers=OFF")
            for statement in ("UPDATE recognition_activation_history SET body_sha256='fake'",
                              "DELETE FROM recognition_activation_history",
                              "INSERT OR REPLACE INTO recognition_activation_history SELECT * FROM recognition_activation_history",
                              "UPDATE recognition_activation_installation SET body_json='{}'",
                              "DELETE FROM recognition_activation_installation",
                              "INSERT OR REPLACE INTO recognition_activation_installation SELECT * FROM recognition_activation_installation"):
                with self.subTest(statement=statement), self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(statement)

    def test_explicit_install_rolls_back_and_never_adopts_explorer_target(self):
        with closing(sqlite3.connect(":memory:")) as conn:
            conn.execute("BEGIN IMMEDIATE")
            activation_schema.install(conn)
            conn.rollback()
            self.assertEqual([], conn.execute("SELECT name FROM sqlite_master").fetchall())
            conn.execute("CREATE TABLE explorer_fixture (id INTEGER)")
            conn.execute("INSERT INTO explorer_fixture VALUES(7)")
            with self.assertRaises(trust.TrustError):
                activation_schema.install(conn)
            conn.commit()
            self.assertEqual([(7,)], conn.execute("SELECT * FROM explorer_fixture").fetchall())
            self.assertEqual([("explorer_fixture",)], conn.execute("SELECT name FROM sqlite_master").fetchall())

    def test_partial_install_failure_rolls_back_inside_caller_transaction(self):
        with closing(sqlite3.connect(":memory:")) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with patch.object(activation_schema, "check_schema", side_effect=trust.TrustError("injected")):
                with self.assertRaises(trust.TrustError):
                    activation_schema.install(conn)
            conn.commit()
            self.assertEqual([], conn.execute("SELECT name FROM sqlite_master").fetchall())

    def test_ledger_install_is_explicit_and_state_reads_never_create_file(self):
        workspace = a.SyntheticActivationWorkspace(provider=self.provider, administrative_authority_id="synthetic-admin")
        self.addCleanup(workspace.cleanup)
        self.assertEqual([], list(workspace.directory.iterdir()))
        report = a.assess_production_readiness(installation=workspace, evidence=self.evidence,
            generations=GENERATIONS, trusted_now_utc=NOW)
        self.assertEqual("BLOCKED", report.status)
        with self.assertRaises(trust.TrustError):
            a.get_activation_state(workspace)
        self.assertEqual([], list(workspace.directory.iterdir()))

    def test_malformed_duplicate_evidence_and_generation_fail_closed(self):
        for evidence in (self.evidence + (self.evidence[0],), (True,), self.changed("trust_root", outcome="WARNING")):
            with self.subTest(evidence=repr(evidence)[:40]):
                self.assertEqual("BLOCKED", self.assess(evidence).status)
        report = a.assess_production_readiness(installation=self.workspace, evidence=self.evidence,
            generations={**GENERATIONS, "trust": True}, trusted_now_utc=NOW)
        self.assertEqual("BLOCKED", report.status)

    def test_no_production_authority_even_after_disposable_activation(self):
        self.change()
        with self.assertRaises(AuthorizationError):
            authority.provision_production_authority()
        with self.assertRaises(AuthorizationError):
            writer_boundary.production_guard(type("Claim", (), {"environment": "production"})())
        self.assertFalse(a.get_activation_state(self.workspace).production_admitted)
        self.assertEqual("BLOCKED", a.activate_production().result)

    def test_fresh_startup_import_never_connects_provisions_or_activates(self):
        code = '''
import sqlite3
from unittest.mock import patch
with patch.object(sqlite3, "connect", side_effect=AssertionError("startup connection")):
    from src.review.recognition import activation, authority, DISABLED
    with patch.object(authority, "provision_production_authority", side_effect=AssertionError("provision")):
        assert activation.get_activation_state().state == "NOT_ACTIVATED"
        assert activation.assess_production_readiness().status == "BLOCKED"
        assert activation.activate_production().result == "BLOCKED"
        assert DISABLED.issuance is False
'''
        run = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
            env={**os.environ, "FORCE_PRODUCTION": "1", "RECOGNITION_ACTIVATED": "1"})
        self.assertEqual(0, run.returncode, run.stderr)
