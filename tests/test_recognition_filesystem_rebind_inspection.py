"""Read-only eligibility; synthetic identities and owned disposable databases."""
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from src.review.recognition import administration as a
from src.review.recognition import filesystem_rebind_inspection as inspection
from tests import test_recognition_filesystem_rebind as rebind_fixture
from tests.test_recognition_administration import at
from tests.recognition_production_owner_fixture import allocation


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(allocation())
        self.fixture = rebind_fixture.FilesystemRebindTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.f = self.fixture.f
        self.enterContext(patch.object(inspection, '_utc_now', return_value=at(60)))
        self.enterContext(patch.object(a, 'rebind_filesystem_identity', side_effect=AssertionError('rebind forbidden')))

    def inspect(self, generation=1):
        before = (self.f.control.read_bytes(), self.f.path.read_bytes())
        original = a.connect
        calls = []
        def readonly(path, **kwargs):
            self.assertFalse(kwargs.get('write', False))
            calls.append(path)
            return original(path, **kwargs)
        with patch.object(a, 'connect', side_effect=readonly):
            result = inspection.inspect_rebind(self.f.path, self.f.control, expected_generation=generation)
        self.assertTrue(calls)
        self.assertEqual(before, (self.f.control.read_bytes(), self.f.path.read_bytes()))
        return result

    def rejects(self, condition, generation=1):
        result = self.inspect(generation)
        self.assertEqual('NOT_ELIGIBLE_FOR_REBIND', result['classification'])
        self.assertIn(condition, [x['condition'] for x in result['failed_conditions']])
        return result

    def test_device_only_drift_reports_complete_metadata_without_writes(self):
        result = self.inspect()
        self.assertEqual('ELIGIBLE_FOR_REBIND', result['classification'], result['failed_conditions'])
        self.assertTrue(result['history_valid'])
        self.assertTrue(result['only_devices_differ'])
        self.assertEqual(1, result['current_generation'])
        self.assertEqual(self.fixture.preview(), result['target_sha256'])
        self.assertEqual(dict(exists=True, role='owner', verified=True), result['owner_status'])
        self.assertFalse(result['rebind_authorized'])
        self.assertFalse(result['write_reservation_acquired'])
        for name in ('control', 'target'):
            recorded = result['recorded_'+name+'_identity']
            observed = result['observed_'+name+'_identity']
            self.assertEqual(recorded['device']+3, observed['device'])
            self.assertEqual(set(recorded), {'hostname', 'database', 'device', 'inode'})

    def test_hostname_path_and_inode_mismatch(self):
        for path in (self.f.control, self.f.path):
            name = 'control' if path == self.f.control else 'target'
            for field, value in (('hostname', 'wrong-host'), ('database', 'wrong-path'), ('inode', -1)):
                with self.subTest(database=name, field=field):
                    self.fixture.overrides[str(path)] = {field: value}
                    self.rejects(name+'_non_device_fields_match')
                    self.fixture.overrides.clear()

    def test_schema_mismatch(self):
        self.f.sql('CREATE TABLE unrelated_test_schema(id INTEGER)')
        self.rejects('target_schema_matches')

    def test_logical_id_mismatch(self):
        self.f.sql("UPDATE recognition_local_installation SET target_id='wrong-target'")
        self.rejects('logical_ids_match')

    def test_owner_role_failure(self):
        self.f.sql("UPDATE community_reviewers SET role='reviewer' WHERE id=1")
        self.rejects('owner_verified')

    def test_generation_mismatch(self):
        self.rejects('generation_matches', generation=2)

    def test_no_device_drift(self):
        self.fixture.device_offsets = {}
        self.rejects('device_drift_present')

    def test_invalid_binding_and_incomplete_history(self):
        for audit in (False, True):
            with self.subTest(audit=audit):
                # Simulate corruption only in the disposable fixture; never repair it.
                table = 'recognition_admin_audit' if audit else 'recognition_admin_bindings'
                with a.connect(self.f.control, write=True) as conn:
                    conn.execute('BEGIN IMMEDIATE')
                    triggers = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,)).fetchall()
                    for row in triggers:
                        conn.execute('DROP TRIGGER "'+row[0]+'"')
                    conn.execute('UPDATE '+table+" SET body_sha256=?", ('0'*64,))
                    conn.commit()
                self.rejects('audit_history_valid' if audit else 'binding_history_valid')

    def test_v3_binding_is_not_eligible(self):
        self.fixture.device_offsets = {}
        a.migrate_runtime_profile_contract(self.f.config, expected_generation=1,
            operator='test', reason='test v3 rejection', now=at(60))
        self.fixture.device_offsets = {str(self.f.control): 3, str(self.f.path): 3}
        result = self.rejects('binding_is_v2', generation=2)
        self.assertTrue(result['binding_history_valid'])

    def test_cli_requires_no_key_and_does_not_invoke_mutator(self):
        from scripts.active.manage_recognition_administration import main
        output = io.StringIO()
        with redirect_stdout(output):
            main(['inspect-filesystem-rebind', '--target', str(self.f.path), '--control', str(self.f.control),
                  '--expected-generation', '1'])
        self.assertEqual('ELIGIBLE_FOR_REBIND', json.loads(output.getvalue())['classification'])

    def test_changed_observation_fails_closed(self):
        original = inspection._target_metadata
        calls = []
        def changed(*args):
            result = original(*args)
            calls.append(True)
            if len(calls) > 1:
                result['owner']['verified'] = False
            return result
        with patch.object(inspection, '_target_metadata', side_effect=changed):
            self.rejects('observations_stable')
