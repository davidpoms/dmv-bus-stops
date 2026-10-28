"""Slice H: synthetic device drift, owned temporary databases only."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import io
import json
import shutil
import threading
import unittest
from unittest.mock import patch

from tests import test_recognition_administration as fixture
from src.review.recognition import administration as a, admin_auth as m, permanent, writer_boundary
from src.review.recognition.rules import digest


class FilesystemRebindTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.AdministrationTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.session, self.step, self.confirmation = self.f.confirmation()
        self.original_identity = a.target_identity
        self.original_binding = a.get_installation_control(self.f.config)
        self.device_offsets = {str(self.f.control): 3, str(self.f.path): 3}
        self.overrides = {}
        self.enterContext(patch.object(a, "target_identity", side_effect=self.current_identity))

    def current_identity(self, database):
        observed = self.original_identity(database)
        fields = dict(device=observed.device + self.device_offsets.get(observed.database, 0))
        fields.update(self.overrides.get(observed.database, {}))
        return replace(observed, **fields)

    def preview(self, config=None):
        with a.connect((config or self.f.config).target) as target:
            return digest(a.observe_target(target))

    def rebind(self, **changes):
        args = dict(expected_generation=1, expected_target_sha256=self.preview(),
                    operator="synthetic-deployment-owner", reason="synthetic device-only remount", now=fixture.at(60))
        args.update(changes)
        return a.rebind_filesystem_identity(self.f.config, **args)

    def assert_unmodified(self):
        self.assertEqual([(1,)], self.f.sql("SELECT MAX(generation) FROM recognition_admin_bindings", control=True))
        self.assertEqual([(0,)], self.f.sql("SELECT revoked FROM recognition_admin_sessions", control=True))
        self.assertEqual([(0,)], self.f.sql("SELECT used FROM recognition_admin_confirmations", control=True))

    def test_device_only_drift_succeeds_without_target_writes(self):
        before = self.f.path.read_bytes()
        with patch.object(permanent, "finalize", side_effect=AssertionError("writer invoked")), \
                patch.object(writer_boundary, "_local_lease", side_effect=AssertionError("capability issued")):
            self.assertEqual(2, self.rebind())
        updated = a.get_installation_control(self.f.config)
        self.assertEqual(self.original_binding["installation_id"], updated["installation_id"])
        self.assertEqual(self.original_binding["target_id"], updated["target_id"])
        self.assertEqual(self.original_binding["owner_id"], updated["owner_id"])
        self.assertEqual(self.original_binding["control_identity"]["device"] + 3, updated["control_identity"]["device"])
        self.assertEqual(self.original_binding["target"]["observation"]["device"] + 3, updated["target"]["observation"]["device"])
        self.assertEqual("NOT_ACTIVATED", updated["production_state"])
        self.assertEqual(before, self.f.path.read_bytes())

    def test_control_only_device_drift_is_supported(self):
        self.device_offsets[str(self.f.path)] = 0
        self.assertEqual(2, self.rebind())
        self.assertEqual(self.original_binding["target"], a.get_installation_control(self.f.config)["target"])

    def test_target_only_device_drift_is_supported(self):
        self.device_offsets[str(self.f.control)] = 0
        self.assertEqual(2, self.rebind())
        self.assertEqual(self.original_binding["control_identity"], a.get_installation_control(self.f.config)["control_identity"])

    def test_control_inode_replacement_fails(self):
        replacement = self.f.control.with_name("replacement-control.sqlite")
        shutil.copyfile(self.f.control, replacement)
        replacement.replace(self.f.control)
        with self.assertRaisesRegex(a.AdminError, "non_device_mismatch"):
            self.rebind()
        self.assert_unmodified()

    def test_target_inode_replacement_fails(self):
        replacement = self.f.path.with_name("replacement-target.sqlite")
        shutil.copyfile(self.f.path, replacement)
        replacement.replace(self.f.path)
        with self.assertRaisesRegex(a.AdminError, "non_device_mismatch"):
            self.rebind()
        self.assert_unmodified()

    def test_hostname_mismatch_fails_for_either_file(self):
        for path in (self.f.path, self.f.control):
            with self.subTest(path=path.name):
                self.overrides[str(path)] = dict(hostname="another-synthetic-host")
                with self.assertRaisesRegex(a.AdminError, "non_device_mismatch"):
                    self.rebind()
                self.overrides.clear()
                self.assert_unmodified()

    def test_paths_must_match_bound_paths(self):
        for attribute, original in (("target", self.f.path), ("control", self.f.control)):
            with self.subTest(attribute=attribute):
                alternative = original.with_name("other-" + original.name)
                shutil.copyfile(original, alternative)
                config = replace(self.f.config, **{attribute: alternative})
                with self.assertRaisesRegex(a.AdminError, "path_mismatch"):
                    a.rebind_filesystem_identity(config, expected_generation=1, expected_target_sha256=self.preview(config),
                        operator="synthetic-host", reason="wrong path", now=fixture.at(60))
                self.assert_unmodified()

    def test_schema_mismatch_fails_even_with_current_preview(self):
        self.f.sql("CREATE TABLE unintended_schema (id INTEGER)")
        with self.assertRaisesRegex(a.AdminError, "schema_mismatch"):
            self.rebind()
        self.assert_unmodified()

    def test_wrong_generation_fails(self):
        for generation in (0, 2, True, None):
            with self.subTest(generation=generation), self.assertRaisesRegex(a.AdminError, "generation_conflict"):
                self.rebind(expected_generation=generation)
        self.assert_unmodified()

    def test_wrong_preview_and_predrift_preview_fail(self):
        for value in ("0" * 64, digest(self.original_binding["target"]), None):
            with self.subTest(value=value), self.assertRaisesRegex(a.AdminError, "preview_mismatch"):
                self.rebind(expected_target_sha256=value)
        self.assert_unmodified()

    def test_no_device_change_is_not_a_rebind(self):
        self.device_offsets.clear()
        with self.assertRaisesRegex(a.AdminError, "device_unchanged"):
            self.rebind()
        self.assert_unmodified()

    def test_operator_and_reason_are_required(self):
        for changes in (dict(operator=""), dict(reason=" "), dict(operator=None), dict(reason=None)):
            with self.subTest(changes=changes), self.assertRaisesRegex(a.AdminError, "ceremony_required"):
                self.rebind(**changes)
        self.assert_unmodified()

    def test_installation_owner_and_target_uuid_must_match(self):
        for column in ("installation_id", "target_id", "owner_id"):
            old = self.f.sql("SELECT " + column + " FROM recognition_local_installation")[0][0]
            value = 2 if column == "owner_id" else "ffffffff-ffff-4fff-8fff-ffffffffffff"
            self.f.sql("UPDATE recognition_local_installation SET " + column + "=?", (value,))
            with self.subTest(column=column), self.assertRaisesRegex(a.AdminError, "installation_target_mismatch"):
                self.rebind()
            self.f.sql("UPDATE recognition_local_installation SET " + column + "=?", (old,))
        self.assert_unmodified()

    def test_pinned_owner_must_still_be_verified_owner(self):
        self.f.sql("UPDATE community_reviewers SET role='reviewer' WHERE id=1")
        with self.assertRaisesRegex(a.AdminError, "verified_project_owner_required"):
            self.rebind()
        self.assert_unmodified()

    def test_authentication_is_invalidated(self):
        self.rebind()
        self.assertTrue(all(row[0] == 1 for row in self.f.sql("SELECT revoked FROM recognition_admin_primary", control=True)))
        self.assertEqual([(1,)], self.f.sql("SELECT revoked FROM recognition_admin_sessions", control=True))
        self.assertEqual([(0,)], self.f.sql("SELECT COUNT(*) FROM recognition_admin_stepups", control=True))
        self.assertEqual([(1,)], self.f.sql("SELECT used FROM recognition_admin_confirmations", control=True))
        with self.assertRaises(a.AdminError):
            m.get_admin_identity(self.f.config, self.f.primary, now=fixture.at(60))
        with self.assertRaises(a.AdminError):
            m.require_recognition_admin(self.f.config, self.session, now=fixture.at(60))

    def test_concurrent_and_stale_rebind_rejected(self):
        preview = self.preview()
        barrier = threading.Barrier(2)
        def run():
            barrier.wait()
            try:
                return self.rebind(expected_target_sha256=preview)
            except a.AdminError as error:
                return error.code
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))
        self.assertCountEqual([2, "filesystem_rebind_generation_conflict"], results)
        with self.assertRaisesRegex(a.AdminError, "generation_conflict"):
            self.rebind(expected_target_sha256=preview)
        self.assertEqual([(2,)], self.f.sql("SELECT COUNT(*) FROM recognition_admin_bindings", control=True))

    def test_binding_and_audit_chains_remain_valid(self):
        self.rebind()
        with a.connect(self.f.control) as control:
            current = a._binding(control)
            record = json.loads(a._audit_head(control)["body_json"])
        self.assertEqual(digest(self.original_binding), current["previous_sha256"])
        self.assertEqual("filesystem_identity_rebound", record["action"])
        self.assertEqual("synthetic-deployment-owner", record["actor"])
        self.assertEqual((1, 2), (record["subject"]["previous_generation"], record["subject"]["generation"]))
        self.assertEqual(self.original_binding["control_identity"], record["subject"]["old_control_identity"])
        self.assertEqual(current["control_identity"], record["subject"]["control_identity"])
        self.assertEqual("synthetic device-only remount", record["subject"]["reason"])

    def test_audit_failure_rolls_back_all_control_changes(self):
        with patch.object(a, "_audit", side_effect=RuntimeError("synthetic append failure")), self.assertRaises(RuntimeError):
            self.rebind()
        self.assert_unmodified()

    def test_another_observation_change_before_commit_rolls_back(self):
        audit = a._audit
        def changed(*args, **kwargs):
            audit(*args, **kwargs)
            self.device_offsets[str(self.f.control)] += 1
        with patch.object(a, "_audit", side_effect=changed), self.assertRaisesRegex(a.AdminError, "observation_changed"):
            self.rebind()
        self.assert_unmodified()

    def test_normal_identity_checks_remain_strict_before_and_after_rebind(self):
        with self.assertRaisesRegex(a.AdminError, "control_identity_mismatch"):
            a.verify_target_control(self.f.config)
        self.device_offsets[str(self.f.control)] = 0
        with self.assertRaisesRegex(a.AdminError, "target_identity_or_schema_mismatch"):
            a.verify_target_control(self.f.config)
        self.device_offsets[str(self.f.control)] = 3
        self.rebind()
        a.verify_target_control(self.f.config)
        self.device_offsets[str(self.f.control)] = 4
        with self.assertRaisesRegex(a.AdminError, "control_identity_mismatch"):
            a.verify_target_control(self.f.config)
        self.device_offsets[str(self.f.control)] = 3
        self.device_offsets[str(self.f.path)] = 4
        with self.assertRaisesRegex(a.AdminError, "target_identity_or_schema_mismatch"):
            a.verify_target_control(self.f.config)
        self.assertEqual(asdict(self.original_identity(self.f.path))["device"], self.f.path.stat().st_dev)

    def test_generation_invalidates_activation_approvals_and_deployment_evidence(self):
        from tests import test_recognition_production_activation as production
        from src.review.recognition import local_readiness as r, approvals as b, production_operations as d
        g = production.ProductionActivationTests()
        self.addCleanup(g.doCleanups)
        g.setUp()
        g.activate()
        original = a.get_installation_control(g.f.config)
        with patch.object(a, "target_identity", side_effect=lambda db: replace(self.original_identity(db), device=self.original_identity(db).device+3)):
            with a.connect(g.f.path) as target:
                preview = digest(a.observe_target(target))
            with patch.object(permanent, "finalize", side_effect=AssertionError("writer invoked")):
                self.assertEqual(2, a.rebind_filesystem_identity(g.f.config, expected_generation=1, expected_target_sha256=preview,
                    operator="synthetic-host", reason="device drift after fixture activation", now=fixture.at(150)))
            current = a.get_installation_control(g.f.config)
            self.assertEqual(original["target_id"], current["target_id"])
            self.assertEqual("NOT_ACTIVATED", current["production_state"])
            readiness = r.assess(g.f.config, now=fixture.at(150))
            self.assertEqual("NOT_ACTIVATED", readiness["activation_state"])
            self.assertFalse(readiness["activation_ready"])
            self.assertEqual("BLOCKED", readiness["production_execution"])
            with a.connect(g.f.control) as control:
                self.assertEqual("INVALIDATED", b._read(control, g.f.aid)["state"])
            self.assertEqual([], d.discover_pending(g.f.config))
            self.assertEqual((0, 0, 0, 0), g.f.counts())

    def test_cli_requires_generation_preview_operator_and_reason(self):
        from scripts.active import manage_recognition_administration as cli
        common = ["rebind-filesystem-identity", "--target", str(self.f.path), "--control", str(self.f.control),
                  "--key-file", str(self.f.key_file)]
        for extra in ([], ["--operator", "host", "--reason", "drift"], ["--operator", "host", "--reason", "drift", "--expected-generation", "1"]):
            with self.subTest(extra=extra), self.assertRaises(SystemExit), patch("sys.stderr", new_callable=io.StringIO):
                cli.main(common + extra)
        with patch("sys.stdout", new_callable=io.StringIO), patch.object(cli, "datetime") as clock:
            clock.now.return_value.strftime.return_value = fixture.at(60)
            cli.main(common + ["--operator", "synthetic-host", "--reason", "drift", "--expected-generation", "1", "--target-sha256", self.preview()])
        self.assertEqual(2, a.get_installation_control(self.f.config)["generation"])

    def test_no_web_route(self):
        rules = [rule.rule for rule in fixture.api.app.url_map.iter_rules()]
        self.assertFalse(any("rebind-filesystem" in rule or "filesystem-identity" in rule for rule in rules))
