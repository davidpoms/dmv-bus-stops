"""Disposable real generation-5 enrollment; no production access."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import io
import os
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, authorization
from src.review.recognition import deployment_claim_recovery as recovery
from src.review.recognition import runtime_challenges as challenges, runtime_evidence as evidence
from src.review.recognition import runtime_enrollment as enrollment, runtime_validation as runtime
from src.review.recognition import runtime_execution_claim_schema as claims
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import load
from tests import test_recognition_administration as fixture


class DeploymentClaimRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.AdministrationTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config = self.f.config
        self.f.authenticated()  # Real durable MFA/authentication records to preserve.
        for generation in (1, 2):
            with a.connect(self.config.target) as target:
                preview = digest(a.observe_target(target))
            a.advance_restore_generation(self.config, expected_generation=generation,
                expected_target_sha256=preview, operator='fixture', reason='disposable preparation', now=fixture.at(60))
        a.migrate_runtime_profile_contract(self.config, expected_generation=3,
            operator='fixture', reason='disposable preparation', now=fixture.at(120))
        with a.connect(self.config.control) as control:
            binding = challenges._deployment_binding(control)
        scope = dict(expected_generation=4, installation_id=binding['installation_id'], target_id=binding['target_id'],
                     owner_id=1, source_binding_sha256=digest(binding), operator='fixture', reason='private fixture')
        issued = challenges.issue_challenge(self.config, now=fixture.at(180), **scope)
        challenge = issued['challenge']
        record = evidence._collect(self.config.target, self.config.control,
            challenge_id=challenge['challenge_id'], challenge_sha256=challenge['challenge_sha256'], now=fixture.at(181))
        review = dict(format=enrollment.REVIEW_FORMAT, observations=[record],
                      selected_observation_sha256=record['observation_sha256'])
        with patch.object(enrollment, '_utc_now', return_value=fixture.at(182)):
            enrollment.enroll_runtime_profile(self.config, canonical(review), issued['nonce'], **scope,
                challenge_id=challenge['challenge_id'], challenge_sha256=challenge['challenge_sha256'],
                approved_review_sha256=digest(review), approved_observation_sha256=record['observation_sha256'],
                confirm_private_log_review=True, confirm_enroll_runtime_profile=True)
        clock = patch.object(runtime, '_utc_now', return_value=fixture.at(183))
        self.clock = clock.start()
        self.addCleanup(clock.stop)
        self.changes = {}
        def current(subject):
            actual = authorization.target_identity(subject)
            return replace(actual, device=actual.device+1, **self.changes)
        identity = patch.object(a, 'target_identity', side_effect=current)
        identity.start()
        self.addCleanup(identity.stop)
        mount = patch.object(recovery, '_mount', return_value=dict(filesystem='nfs', source='fixture:/home',
                     root='/', mount_target=str(self.config.target.parent), major_minor='0:59'))
        mount.start()
        self.addCleanup(mount.stop)

    def protected(self):
        with a.connect(self.config.control) as control:
            tables = ('recognition_admin_bindings', 'recognition_runtime_profiles', 'recognition_runtime_auth_bindings',
                      'recognition_admin_mfa', 'recognition_admin_primary', 'recognition_admin_sessions',
                      'recognition_admin_stepups', 'recognition_admin_confirmations')
            return {name: [tuple(row) for row in control.execute('SELECT * FROM '+name)] for name in tables}

    def authorize(self):
        preview = recovery.preview(self.config)
        return recovery.authorize(self.config, approved_snapshot_sha256=preview['snapshot_sha256'],
                                  owner_id=1, operator='verified-owner', reason='accept reviewed mount uncertainty')['recovery_sha256']

    def migrate(self, token=None, **options):
        return claims.migrate(self.config, expected_generation=options.pop('expected_generation', 5),
                              operator='verified-owner', reason='claim schema only', recovery_sha256=token, **options)

    def test_authorized_migration_preserves_generation_profile_authentication_target_and_consumes(self):
        before, target = self.protected(), self.config.target.read_bytes()
        token = self.authorize()
        self.assertEqual('AUTHORIZED', recovery.inspect(self.config, token)['state'])
        result = self.migrate(token)
        self.assertEqual(dict(migration_id=claims.MIGRATION, installed=True, generation=5), result)
        self.assertEqual(before, self.protected())
        self.assertEqual(target, self.config.target.read_bytes())
        status = recovery.inspect(self.config, token)
        self.assertEqual('CONSUMED', status['state'])
        self.assertTrue(status['installed'])
        self.assertFalse(status['execution_authority'])
        with a.connect(self.config.control) as control:
            binding, _, _ = runtime._history(control)
            self.assertEqual(5, binding['generation'])
            self.assertEqual('NOT_ACTIVATED', binding['production_state'])
            self.assertEqual(recovery.CONSUMED, load(a._audit_head(control)['body_json'])['action'])
            for table in (claims.CLAIMS, claims.HISTORY):
                self.assertEqual(0, control.execute('SELECT COUNT(*) FROM '+table).fetchone()[0])
        with self.assertRaisesRegex(ValueError, 'claim_recovery_replayed'):
            self.migrate(token)

    def test_unauthorized_drift_rejected(self):
        with self.assertRaisesRegex(ValueError, 'control_identity_mismatch'):
            self.migrate()

    def test_normal_exact_identity_unchanged(self):
        with patch.object(a, 'target_identity', side_effect=authorization.target_identity):
            self.assertTrue(self.migrate()['installed'])
            self.assertFalse(self.migrate()['installed'])

    def test_wrong_generation(self):
        token = self.authorize()
        with self.assertRaisesRegex(ValueError, 'generation_conflict'):
            self.migrate(token, expected_generation=6)

    def test_wrong_operation(self):
        token = self.authorize()
        with patch.object(claims, 'ACTION', 'other_operation'), self.assertRaisesRegex(ValueError, 'scope_changed'):
            self.migrate(token)

    def test_expiry(self):
        token = self.authorize()
        self.clock.return_value = fixture.at(783)
        with self.assertRaisesRegex(ValueError, 'claim_recovery_expired'):
            self.migrate(token)

    def test_expiry_immediately_before_commit_rolls_back_consumption(self):
        token = self.authorize()
        original = recovery.finish
        def finish(*args):
            expiry = original(*args)
            self.clock.return_value = fixture.at(783)
            return expiry
        with patch.object(recovery, 'finish', side_effect=finish):
            with self.assertRaisesRegex(ValueError, 'claim_recovery_expired'):
                self.migrate(token)
        self.clock.return_value = fixture.at(184)
        self.assertEqual('AUTHORIZED', recovery.inspect(self.config, token)['state'])
        self.assertTrue(self.migrate(token)['installed'])

    def test_unknown_or_modified_authorization_digest(self):
        token = self.authorize()
        with self.assertRaisesRegex(ValueError, 'claim_recovery_not_found'):
            self.migrate(('0' if token[0] != '0' else '1')+token[1:])

    def test_inode_hostname_path_or_second_device_drift_rejected(self):
        token = self.authorize()
        for changes in (dict(inode=1), dict(hostname='other'), dict(database=str(self.config.target.parent/'other.db')),
                        dict(device=123)):
            with self.subTest(changes=changes):
                if 'device' in changes:
                    with patch.object(a, 'target_identity', side_effect=lambda x: replace(authorization.target_identity(x), device=123)):
                        with self.assertRaises(ValueError):
                            self.migrate(token)
                else:
                    self.changes = changes
                    with self.assertRaises(ValueError):
                        self.migrate(token)
                self.changes = {}

    def test_exact_scope_binds_installation_target_binding_profile_schema_and_enrollment(self):
        token = self.authorize()
        original = recovery.snapshot
        for field in ('installation_id', 'target_id', 'generation', 'binding_sha256', 'profile_sha256',
                      'target_schema_sha256', 'control_schema_sha256', 'enrollment_binding_sha256', 'enrollment_audit_sha256'):
            def changed(*args, **kwargs):
                value = deepcopy(original(*args, **kwargs))
                value[field] = 6 if field == 'generation' else 'changed'
                return value
            with self.subTest(field=field), patch.object(recovery, 'snapshot', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'scope_changed'):
                    self.migrate(token)

    def test_partial_migration_rolls_back_authorization_still_usable(self):
        token = self.authorize()
        before = self.config.control.read_bytes()
        original = claims.definitions
        calls = 0
        def broken():
            nonlocal calls
            calls += 1
            definitions = original()
            # First call pins migration definitions in the scope validation.
            if calls == 2:
                definitions['broken'] = 'CREATE TABLE broken ('
            return definitions
        with patch.object(claims, 'definitions', side_effect=broken):
            with self.assertRaises(Exception):
                self.migrate(token)
        self.assertEqual(before, self.config.control.read_bytes())
        self.assertTrue(self.migrate(token)['installed'])

    def test_final_observation_change_rolls_back(self):
        token = self.authorize()
        original = recovery.snapshot
        def changed(*args, **kwargs):
            value = original(*args, **kwargs)
            if kwargs.get('installed'):
                value['observed_control']['device'] += 1
            return value
        with patch.object(recovery, 'snapshot', side_effect=changed), self.assertRaisesRegex(ValueError, 'observation_changed'):
            self.migrate(token)
        self.assertTrue(self.migrate(token)['installed'])

    def test_runtime_identity_still_rejects_drift(self):
        self.migrate(self.authorize())
        with a.connect(self.config.control) as control, a.connect(self.config.target) as target:
            with self.assertRaises(ValueError):
                runtime._identity_snapshot(self.config, control, target, fixture.at(184))

    def test_preview_and_owner_approval_required(self):
        preview = recovery.preview(self.config)
        for changes in (dict(owner_id=2), dict(approved_snapshot_sha256='0'*64)):
            options = dict(owner_id=1, approved_snapshot_sha256=preview['snapshot_sha256'], operator='owner', reason='review')
            options.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                recovery.authorize(self.config, **options)

    def test_actual_target_and_control_replacement_rejected(self):
        token = self.authorize()
        for path in (self.config.target, self.config.control):
            with self.subTest(path=path):
                replacement = path.with_suffix('.replacement')
                saved = path.with_suffix('.saved')
                shutil.copyfile(path, replacement)
                path.rename(saved)
                replacement.rename(path)
                try:
                    with self.assertRaises(ValueError):
                        self.migrate(token)
                finally:
                    path.unlink()
                    saved.rename(path)
        self.assertTrue(self.migrate(token)['installed'])

    def test_actual_schema_change_rejected(self):
        token = self.authorize()
        with a.connect(self.config.target, write=True) as target:
            target.execute('CREATE TABLE changed_schema(value TEXT)')
            target.commit()
        with self.assertRaises(ValueError):
            self.migrate(token)

    def test_actual_installation_and_target_id_changes_rejected(self):
        token = self.authorize()
        for field in ('installation_id', 'target_id'):
            with self.subTest(field=field):
                with a.connect(self.config.target, write=True) as target:
                    old = target.execute('SELECT '+field+' FROM recognition_local_installation').fetchone()[0]
                    target.execute('UPDATE recognition_local_installation SET '+field+'=?',
                                   (str(uuid4()),))
                    target.commit()
                try:
                    with self.assertRaisesRegex(ValueError, 'installation_target_mismatch'):
                        self.migrate(token)
                finally:
                    with a.connect(self.config.target, write=True) as target:
                        target.execute('UPDATE recognition_local_installation SET '+field+'=?', (old,))
                        target.commit()

    def test_changed_control_schema_or_mount_rejected(self):
        token = self.authorize()
        with patch.object(recovery, '_mount', return_value=dict(filesystem='nfs', source='other:/export')):
            with self.assertRaisesRegex(ValueError, 'scope_changed'):
                self.migrate(token)
        with a.connect(self.config.control, write=True) as control:
            control.execute('CREATE TABLE changed_schema(value TEXT)')
            control.commit()
        with self.assertRaisesRegex(ValueError, 'schema_mismatch'):
            self.migrate(token)

    def test_modified_authorization_content_rejected_by_audit_chain(self):
        token = self.authorize()
        with a.connect(self.config.control, write=True) as control:
            # Adversarial corruption fixture only; the real immutable trigger
            # prevents this write. Retain its definition to restore exact schema.
            name = 'recognition_admin_audit_immutable_update'
            sql = control.execute('SELECT sql FROM sqlite_master WHERE name=?', (name,)).fetchone()[0]
            control.execute('DROP TRIGGER '+name)
            event = load(control.execute('SELECT body_json FROM recognition_admin_audit WHERE body_sha256=?', (token,)).fetchone()[0])
            event['subject']['snapshot']['operation'] = 'other_operation'
            control.execute('UPDATE recognition_admin_audit SET body_json=? WHERE body_sha256=?', (canonical(event), token))
            control.execute(sql)
            control.commit()
        with self.assertRaisesRegex(ValueError, 'audit_integrity'):
            self.migrate(token)

    def test_authorization_events_immutable(self):
        token = self.authorize()
        with a.connect(self.config.control, write=True) as control:
            import sqlite3
            for sql in ('DELETE FROM recognition_admin_audit WHERE body_sha256=?',
                        'UPDATE recognition_admin_audit SET body_json=body_json WHERE body_sha256=?'):
                with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                    control.execute(sql, (token,))

    def test_cli_requires_scope_acknowledgement_and_digest_confirmation(self):
        # CLI production bootstrap is covered separately; do not attempt the
        # Linux-only production loader inside this Windows unit-test process.
        with patch('src.api.sqlite_runtime.load_production_sqlite'):
            from scripts.active import recover_recognition_claim_schema as cli
        body = recovery.preview(self.config)['snapshot']
        common = ['--target', str(self.config.target), '--control', str(self.config.control),
                  '--key-file', str(self.config.key_file), '--installation-id', body['installation_id'],
                  '--target-id', body['target_id'], '--expected-generation', '5', '--owner-id', '1',
                  '--operation', claims.ACTION]
        with patch('sys.stdout', new_callable=io.StringIO) as output:
            cli.main(['preview', *common])
        self.assertIn('snapshot_sha256', output.getvalue())
        args = ['authorize', *common, '--operator', 'owner', '--reason', 'review',
                '--approved-snapshot-sha256', digest(body)]
        with patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit):
            cli.main(args)
        with patch('builtins.input', return_value='wrong'), patch('sys.stdout', new_callable=io.StringIO):
            with self.assertRaisesRegex(ValueError, 'confirmation_mismatch'):
                cli.main([*args, '--accept-storage-continuity-uncertainty'])
        with patch('builtins.input', return_value=digest(body)), patch('sys.stdout', new_callable=io.StringIO) as output:
            cli.main([*args, '--accept-storage-continuity-uncertainty'])
        self.assertIn('recovery_sha256', output.getvalue())


class MountObservationTests(unittest.TestCase):
    def test_supported_nfs_mount_and_non_nfs_rejection(self):
        with patch.object(os, 'major', return_value=0, create=True), patch.object(os, 'minor', return_value=59, create=True), \
             patch.object(Path, 'read_text', return_value='10 1 0:59 / /home rw - nfs server:/home rw\n'):
            self.assertEqual('server:/home', recovery._mount(Path('/home/db'), 59)['source'])
        with patch.object(Path, 'read_text', return_value='10 1 0:59 / /home rw - ext4 /dev/disk rw\n'):
            with self.assertRaisesRegex(ValueError, 'nfs_required'):
                recovery._mount(Path('/home/db'), 59)
