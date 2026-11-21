"""Synthetic keys and disposable G5 databases only. No hosted evidence."""
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import asdict
import hashlib
import io
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.review.recognition import administration as a, admin_auth as auth, authorization, deployment_qualification
from src.review.recognition import runtime_governance_recovery as recovery
from src.review.recognition import runtime_production_governance as governance
from src.review.recognition import runtime_target_schema_completion as completion, runtime_target_schema_lineage as lineage
from src.review.recognition import runtime_validation as runtime
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import load
from src.review import email_delivery
from tests import test_recognition_target_schema_completion as fixture
from tests import test_recognition_administration as base


def public(key):
    return base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()


def complete_test_foundation(foundation, approval=None):
    # The qualification fixture uses synthetic host evidence. Completing the
    # foundation rechecks that evidence but must not depend on the host launcher.
    with patch.object(deployment_qualification, 'qualify_locking') as probe:
        result = foundation.apply(approval)
    probe.assert_called_once_with(foundation.config)
    return result


def fixture_acl_checks(test):
    """Check real disposable Windows ACLs once per unchanged file identity.

    These protocol tests do not mutate ACLs. The existing bootstrap suite tests
    the real ACL subprocess, including changed/broad ACL rejection. Production
    never caches permission checks; POSIX tests use every actual check.
    """
    if os.name != 'nt':
        return
    original = recovery._protected
    checked = set()
    from scripts.operator.recognition_governance import _path
    def stable(path, *, directory=False):
        _path(path)  # Still reject changed symlinks/canonical paths every time.
        info = path.lstat()
        stamp = (str(path), directory, info.st_dev, info.st_ino, info.st_mode,
                 info.st_nlink, info.st_ctime_ns)
        if stamp not in checked:
            original(path, directory=directory)
            checked.add(stamp)
    test.enterContext(patch.object(recovery, '_protected', side_effect=stable))


class GovernanceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.TargetSchemaCompletionTests()
        self.f.omit_qualification = True
        self.f.omit_rehearsal = True
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        fixture_acl_checks(self)
        self.config = self.f.config
        for path in (self.config.target, self.config.control, self.config.key_file):
            path.chmod(0o600); path.parent.chmod(0o700)
        self.clock = self.f.f.clock
        self.clock.return_value = base.at(240)
        self._pair_synthetic_clock()
        self.original_bytes = governance.trust_path(self.config).read_bytes()
        self.root_a = governance._root(self.config)
        self.r = Ed25519PrivateKey.generate()
        self.b = Ed25519PrivateKey.generate()
        self.recovery_key = dict(format=recovery.KEY_FORMAT, installation_id=self.root_a['installation_id'],
                                 owner_id=1, public_key=public(self.r))
        self.root_b = dict(self.root_a, public_key=public(self.b))
        self.mail = []
        self.enterContext(patch.object(email_delivery, 'governance_recovery_sender_from_env',
            return_value=lambda recipient, message, minutes:self.mail.append((recipient, load(message), minutes))))

    def _pair_synthetic_clock(self):
        # The existing fixture freezes UTC in 2099. On Windows, real ACL checks
        # use subprocesses and can exceed that frozen clock's one-second sample.
        # Pair BOTH synthetic clocks; never relax the production _Clock rules.
        from src.review.recognition import runtime_execution_claims as claims
        self.enterContext(patch.object(claims.time, 'monotonic_ns',
            side_effect=lambda:a.timestamp(runtime._utc_now())*1_000_000_000))

    def request(self):
        self.requested = recovery.request_enrollment(self.config, self.recovery_key, reason='synthetic recovery enrollment')
        return self.requested

    def enroll(self):
        request = self.request()
        return recovery.enroll(self.config, request['request_id'], email_challenge=self.mail[-1][1]['email_challenge'],
            code=base.independent_code(self.clock.return_value), approved_request_sha256=request['request_sha256'])

    def run_enroll_cli(self, *, challenge=None, code=None, approved=None, startup=None):
        from scripts.operator import recognition_governance_recovery as cli
        from src.api import sqlite_runtime
        request = self.requested
        args = ['enroll', '--target', str(self.config.target), '--control', str(self.config.control),
                '--key-file', str(self.config.key_file), '--installation-id', self.root_a['installation_id'],
                '--owner-id', '1', '--original-public-key-sha256', recovery.fingerprint(self.root_a),
                '--request-id', request['request_id'], '--approved-request-sha256', approved or request['request_sha256']]
        inputs = (challenge or self.mail[-1][1]['email_challenge'], code or base.independent_code(self.clock.return_value))
        with patch.object(sqlite_runtime, 'load_production_sqlite', side_effect=startup), \
                patch('builtins.input', return_value=args[-1]), patch.object(cli, '_secret', side_effect=inputs), \
                patch('sys.stdout', new_callable=io.StringIO) as out, patch('sys.stderr', new_callable=io.StringIO) as err:
            status = cli.main(args)
        return status, out.getvalue(), err.getvalue()

    def assert_enroll_diagnostic(self, phase, *, scope_fields=None, **inputs):
        before_target = self.config.target.read_bytes()
        status, output, errors = self.run_enroll_cli(**inputs)
        self.assertEqual(1, status)
        self.assertEqual('', output)
        expected = dict(error='governance_recovery_outcome_unconfirmed', inspect_before_retry=True,
                        execution_authority=False, phase=phase)
        if scope_fields is not None:
            expected['scope_fields'] = scope_fields
        self.assertEqual(canonical(expected) + '\n', errors)
        self.assertEqual(before_target, self.config.target.read_bytes())

    def counter(self):
        with a.connect(self.config.control) as control:
            return control.execute('SELECT last_counter FROM recognition_admin_mfa WHERE actor=1').fetchone()[0]

    def test_operator_cli_success_keeps_enrollment_output_contract(self):
        self.request()
        fingerprint = recovery.fingerprint(self.root_a)
        expected = dict(state='READY', root_sha256=digest(self.root_a), public_key_sha256=fingerprint,
                        current_public_key_sha256=fingerprint, recovery_key_sha256=digest(self.recovery_key),
                        pending_ids=[], execution_authority=False)

        def startup():
            import sys
            print('recognition_sqlite_startup {"expected_library":"/synthetic/private/libsqlite3.so.0"}',
                  file=sys.stderr)

        self.assertEqual((0, canonical(expected) + '\n', ''), self.run_enroll_cli(startup=startup))
        self.assertEqual(expected, recovery.inspect(self.config))

    def test_enrollment_diagnostic_pre_mfa_failures(self):
        self.request()
        before = self.config.control.read_bytes()
        self.assert_enroll_diagnostic('email_challenge', challenge='synthetic-wrong-email-challenge')
        self.assert_enroll_diagnostic('prompt', code=EOFError('synthetic prompt detail'))
        self.assert_enroll_diagnostic('request_validation', approved='0'*64)
        with patch('socket.gethostname', return_value='synthetic-other-console'):
            self.assert_enroll_diagnostic('scope_validation', scope_fields=['physical'])
        with patch.object(recovery, '_reserved', side_effect=OSError('synthetic private path')):
            self.assert_enroll_diagnostic('reservation')
        with patch.object(recovery, 'enroll', side_effect=RuntimeError('synthetic secret')):
            self.assert_enroll_diagnostic('unknown')
        def startup():
            import sys
            print('synthetic SQLite library path', file=sys.stderr)
            raise RuntimeError('synthetic environment value')
        self.assert_enroll_diagnostic('startup', startup=startup)
        self.clock.return_value = base.at(841)
        self.assert_enroll_diagnostic('approval_clock')
        self.assertEqual(before, self.config.control.read_bytes())
        self.request()
        with a.connect(self.config.control, write=True) as control:
            a._audit(control, 'unrelated_fixture_audit', 1, self.clock.return_value)
            control.commit()
        before = self.config.control.read_bytes()
        self.assert_enroll_diagnostic('request_validation')
        self.assertEqual(before, self.config.control.read_bytes())

    def test_enrollment_diagnostic_mfa_seed_and_durable_denial(self):
        self.request()
        before, counter = self.config.control.read_bytes(), self.counter()
        with patch.object(Fernet, 'decrypt', side_effect=InvalidToken('synthetic ciphertext')):
            self.assert_enroll_diagnostic('mfa_verification')
        self.assertEqual(before, self.config.control.read_bytes())
        self.assert_enroll_diagnostic('mfa_verification', code='synthetic-invalid-code')
        self.assertEqual('administration_denied', self.records()[-1]['action'])
        self.assertEqual(counter, self.counter())
        with a.connect(self.config.control) as control:
            self.assertEqual(1, control.execute('SELECT failures FROM recognition_admin_attempts WHERE actor=1').fetchone()[0])

    def signed(self, plan, key=None):
        return dict(serialized_approval=canonical(plan),
            signature=base64.b64encode((key or self.r).sign(recovery.signing_bytes(plan))).decode())

    def rotate(self, root=None):
        result = recovery.plan(self.config, root or self.root_b, reason='synthetic exact cutover')
        self.plan = result['plan']
        return recovery.cutover(self.config, self.signed(self.plan), approved_plan_sha256=result['plan_sha256'])

    def records(self):
        with a.connect(self.config.control) as control:
            return [load(row[0]) for row in control.execute('SELECT body_json FROM recognition_admin_audit ORDER BY sequence')]

    def protected(self):
        tables = ('recognition_admin_bindings','recognition_runtime_profiles','recognition_runtime_auth_bindings',
                  'recognition_admin_primary','recognition_admin_sessions','recognition_admin_stepups',
                  'recognition_admin_confirmations','recognition_local_activation')
        with a.connect(self.config.control) as control:
            return {table:[tuple(row) for row in control.execute('SELECT * FROM '+table)] for table in tables}

    def approval(self, key):
        subject = dict(kind=completion.PREVIEW_KIND, operator='fixture-owner', reason='synthetic preview')
        physical = dict(target=asdict(a.target_identity(self.config.target)), control=asdict(a.target_identity(self.config.control)))
        grant = authorization.Authorization(target=authorization.Target(**physical['target']), environment='production',
            expires_at_utc=base.at(540), **completion.preview_binding(subject))
        body = dict(format=governance.FORMAT, mandate=self.root_a['mandate'], installation_id=self.root_a['installation_id'],
            binding_sha256='a'*64, holder=dict(actor_id=1, primary_sha256='b'*64, session_sha256='c'*64),
            subject=subject, **physical, issued_at_utc=base.at(240), expires_at_utc=base.at(540), approvals=[asdict(grant)])
        return dict(serialized=canonical(body), signature=base64.b64encode(key.sign(governance.DOMAIN+canonical(body).encode())).decode())

    def test_email_totp_enrollment_without_runtime_identity_or_browser_credentials(self):
        before, target = self.protected(), self.config.target.read_bytes()
        with a.connect(self.config.control) as control:
            original_mfa = dict(control.execute('SELECT * FROM recognition_admin_mfa WHERE actor=1').fetchone())
        with patch.object(runtime, '_identity_snapshot', side_effect=AssertionError('must not enter runtime admission')):
            with redirect_stdout(io.StringIO()) as output:
                result = self.enroll()
        self.assertEqual('READY', result['state'])
        self.assertEqual(self.root_a, governance._root(self.config))
        self.assertEqual('owner@example.test', self.mail[0][0])
        self.assertEqual(10, self.mail[0][2])
        token = self.mail[0][1]['email_challenge']
        code = base.independent_code(self.clock.return_value)
        self.assertNotIn(token, canonical(self.records()))
        self.assertNotIn(code, output.getvalue())
        self.assertNotIn(token, output.getvalue())
        self.assertEqual(before, self.protected())
        self.assertEqual(target, self.config.target.read_bytes())
        self.assertEqual(self.original_bytes, governance.trust_path(self.config).read_bytes())
        with a.connect(self.config.control) as control:
            current_mfa = dict(control.execute('SELECT * FROM recognition_admin_mfa WHERE actor=1').fetchone())
        original_mfa['last_counter'] = a.timestamp(self.clock.return_value)//30
        self.assertTrue(original_mfa == current_mfa, 'MFA fields other than the consumed counter changed')
        self.assertFalse(original_mfa['seed_ciphertext'] in canonical(self.records()), 'MFA secret entered audit')
        with self.assertRaisesRegex(ValueError, 'already_enrolled'):
            self.request()

    def test_email_challenge_and_explicit_exact_request_required(self):
        requested = self.request()
        before = self.config.control.read_bytes()
        for token, digest_value in (('ordinary-login-token-not-purpose-bound', requested['request_sha256']),
                                   (self.mail[-1][1]['email_challenge'], '0'*64)):
            with self.subTest(digest=digest_value), self.assertRaises(ValueError):
                recovery.enroll(self.config, requested['request_id'], email_challenge=token,
                    code=base.independent_code(self.clock.return_value), approved_request_sha256=digest_value)
        self.assertEqual(before, self.config.control.read_bytes())
        self.assertEqual('NOT_ENROLLED', recovery.inspect(self.config)['state'])

    def test_invalid_totp_persists_only_failure_and_denial(self):
        requested = self.request()
        before = self.protected()
        with self.assertRaisesRegex(a.AdminError, 'invalid_or_replayed_totp'):
            recovery.enroll(self.config, requested['request_id'], email_challenge=self.mail[-1][1]['email_challenge'],
                code='not-a-code', approved_request_sha256=requested['request_sha256'])
        self.assertEqual(before, self.protected())
        self.assertEqual('administration_denied', self.records()[-1]['action'])
        with a.connect(self.config.control) as control:
            self.assertEqual(1, control.execute('SELECT failures FROM recognition_admin_attempts WHERE actor=1').fetchone()[0])
        self.assertFalse(any(row['action'] == recovery.ENROLLED for row in self.records()))
        self.assertFalse(recovery.certificate_directory(self.config).exists())

    def test_existing_totp_replay_and_throttle_are_enforced(self):
        requested = self.request()
        with a.connect(self.config.control, write=True) as control:
            control.execute('UPDATE recognition_admin_mfa SET last_counter=? WHERE actor=1',
                            (a.timestamp(self.clock.return_value)//30,))
            control.commit()
        with self.assertRaisesRegex(a.AdminError, 'invalid_or_replayed_totp'):
            recovery.enroll(self.config, requested['request_id'], email_challenge=self.mail[-1][1]['email_challenge'],
                code=base.independent_code(self.clock.return_value), approved_request_sha256=requested['request_sha256'])
        self.clock.return_value = base.at(841)
        requested = self.request()
        with a.connect(self.config.control, write=True) as control:
            control.execute('INSERT INTO recognition_admin_attempts VALUES(1,?,5) ON CONFLICT(actor) DO UPDATE SET window_start=excluded.window_start,failures=5',
                            (a.timestamp(self.clock.return_value),)); control.commit()
        with self.assertRaisesRegex(a.AdminError, 'mfa_rate_limited'):
            recovery.enroll(self.config, requested['request_id'], email_challenge=self.mail[-1][1]['email_challenge'],
                code=base.independent_code(self.clock.return_value), approved_request_sha256=requested['request_sha256'])

    def test_request_expiry_stale_audit_and_independent_recovery_key(self):
        same_key = dict(self.recovery_key, public_key=self.root_a['public_key'])
        with self.assertRaisesRegex(ValueError, 'independent_key'):
            recovery.request_enrollment(self.config, same_key, reason='reject signing key as recovery')
        requested = self.request()
        self.clock.return_value = base.at(841)
        with self.assertRaisesRegex(ValueError, 'expired'):
            recovery.enroll(self.config, requested['request_id'], email_challenge=self.mail[-1][1]['email_challenge'],
                code=base.independent_code(self.clock.return_value), approved_request_sha256=requested['request_sha256'])
        requested = self.request()
        with a.connect(self.config.control, write=True) as control:
            a._audit(control, 'unrelated_fixture_audit', 1, self.clock.return_value); control.commit()
        with self.assertRaisesRegex(ValueError, 'stale'):
            recovery.enroll(self.config, requested['request_id'], email_challenge=self.mail[-1][1]['email_challenge'],
                code=base.independent_code(self.clock.return_value), approved_request_sha256=requested['request_sha256'])

    def test_current_b_historical_a_and_reusable_b_to_c(self):
        original_target = self.config.target.read_bytes()
        approval_a = self.approval(self.f.key)
        proof = dict(**approval_a, root_sha256=digest(self.root_a))
        with a.connect(self.config.control, write=True) as control:
            grant = load(approval_a['serialized'])['approvals'][0]
            a._audit(control, 'synthetic_governance_evidence', 1, self.clock.return_value,
                     dict(approval=grant, governance_proof=proof)); control.commit()
        historical = self.records()[-1]
        before = self.protected()
        self.enroll()
        with a.connect(self.config.control) as control:
            enrolled_mfa = [tuple(row) for row in control.execute('SELECT * FROM recognition_admin_mfa')]
        self.assertEqual('READY', self.rotate()['state'])
        self.assertEqual(self.root_b, governance._root(self.config))
        self.assertEqual(self.root_b, governance._verify(self.config, **self.approval(self.b))[0])
        with self.assertRaises(ValueError):
            governance._verify(self.config, **approval_a)
        with a.connect(self.config.control) as control:
            governance.verify_evidence(proof, grant, control=control, event=historical)
            self.assertEqual(self.root_a, recovery.historical_root(self.config, control, historical))
            changed = dict(historical, at_utc=base.at(1))
            with self.assertRaisesRegex(ValueError, 'membership'):
                recovery.historical_root(self.config, control, changed)
        key_c = Ed25519PrivateKey.generate(); root_c = dict(self.root_a, public_key=public(key_c))
        self.rotate(root_c)
        self.assertEqual(root_c, governance._root(self.config))
        self.assertEqual(before, self.protected())
        self.assertEqual(original_target, self.config.target.read_bytes())
        with a.connect(self.config.control) as control:
            self.assertTrue(enrolled_mfa == [tuple(row) for row in control.execute('SELECT * FROM recognition_admin_mfa')],
                            'Cutover changed MFA state')
        self.assertEqual(self.original_bytes, governance.trust_path(self.config).read_bytes())
        self.assertEqual(2, sum(event['action'] == recovery.CUTOVER for event in self.records()))
        with self.assertRaisesRegex(ValueError, 'root_reuse'):
            recovery.plan(self.config, self.root_b, reason='must not reactivate retired root')

    def test_root_b_self_authorization_wrong_plan_and_replay_rejected(self):
        self.enroll()
        result = recovery.plan(self.config, self.root_b, reason='synthetic plan')
        before = self.config.control.read_bytes()
        for key, sha in ((self.b, result['plan_sha256']), (self.f.key, result['plan_sha256']), (self.r, '0'*64)):
            with self.subTest(key=key is self.r, digest=sha), self.assertRaises(ValueError):
                recovery.cutover(self.config, self.signed(result['plan'], key), approved_plan_sha256=sha)
        self.assertEqual(before, self.config.control.read_bytes())
        envelope = self.signed(result['plan'])
        recovery.cutover(self.config, envelope, approved_plan_sha256=result['plan_sha256'])
        with self.assertRaises(ValueError):
            recovery.cutover(self.config, envelope, approved_plan_sha256=result['plan_sha256'])

    def test_wrong_scope_modified_expired_and_stale_plan(self):
        self.enroll()
        plan = recovery.plan(self.config, self.root_b, reason='synthetic plan')['plan']
        for field in ('installation_id','owner_id','generation','target_id','binding_sha256','profile_sha256',
                      'target_schema_sha256','control_schema_sha256'):
            changed = deepcopy(plan)
            changed['scope'][field] = 42 if type(changed['scope'][field]) is int else 'a'*64 if field.endswith('sha256') else str(__import__('uuid').uuid4())
            with self.subTest(field=field), self.assertRaises(ValueError):
                recovery.cutover(self.config, self.signed(changed), approved_plan_sha256=digest(changed))
        changed = deepcopy(plan); changed['scope']['physical']['target']['inode'] += 1
        with self.assertRaisesRegex(ValueError, 'scope_changed'):
            recovery.cutover(self.config, self.signed(changed), approved_plan_sha256=digest(changed))
        self.clock.return_value = base.at(841)
        with self.assertRaisesRegex(ValueError, 'expired'):
            recovery.cutover(self.config, self.signed(plan), approved_plan_sha256=digest(plan))
        self.clock.return_value = base.at(842)
        plan = recovery.plan(self.config, self.root_b, reason='synthetic plan')['plan']
        with a.connect(self.config.control, write=True) as control:
            a._audit(control, 'unrelated_fixture_audit', 1, self.clock.return_value); control.commit()
        with self.assertRaisesRegex(ValueError, 'scope_changed'):
            recovery.cutover(self.config, self.signed(plan), approved_plan_sha256=digest(plan))

    def test_interrupted_enrollment_publication_blocks_then_explicitly_publishes(self):
        self.request()
        counter = self.counter()
        with patch.object(recovery, '_publish', side_effect=OSError('synthetic failure')):
            self.assert_enroll_diagnostic('publication')
        self.assertEqual(recovery.ENROLLED, self.records()[-1]['action'])
        self.assertGreater(self.counter(), counter)
        status = recovery.inspect(self.config)
        self.assertEqual('PUBLICATION_PENDING', status['state'])
        with self.assertRaisesRegex(ValueError, 'publication_pending'):
            governance._root(self.config)
        with self.assertRaises(ValueError):
            self.request()
        before = self.config.control.read_bytes()
        self.clock.return_value = base.at(1000)  # Finishing publication is not a new approval.
        recovery.publish_committed(self.config, status['pending_ids'][0])
        self.assertEqual(before, self.config.control.read_bytes())
        self.assertEqual('READY', recovery.inspect(self.config)['state'])
        with self.assertRaises(ValueError):
            recovery.publish_committed(self.config, status['pending_ids'][0])

    def test_cutover_publication_pending_no_a_fallback_and_no_automatic_repair(self):
        self.enroll()
        with patch.object(recovery, '_publish', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                self.rotate()
        status = recovery.inspect(self.config)
        self.assertEqual('PUBLICATION_PENDING', status['state'])
        with self.assertRaisesRegex(ValueError, 'publication_pending'):
            governance._verify(self.config, **self.approval(self.f.key))
        recovery.publish_committed(self.config, status['pending_ids'][0])
        self.assertEqual(self.root_b, governance._root(self.config))
        path = recovery.certificate_directory(self.config)/'cutover-00000001.json'
        value = load(path.read_text()); value['plan']['reason'] = 'modified'
        path.write_text(canonical(value))
        with self.assertRaisesRegex(ValueError, 'certificate_conflict'):
            recovery.inspect(self.config)
        with self.assertRaises(ValueError):
            recovery.publish_committed(self.config, status['pending_ids'][0])

    def test_concurrent_cutovers_only_one_commits(self):
        self.enroll()
        plan = recovery.plan(self.config, self.root_b, reason='synthetic race')['plan']
        envelope = self.signed(plan)
        def run(_):
            try:
                return recovery.cutover(self.config, envelope, approved_plan_sha256=digest(plan))['state']
            except (ValueError, sqlite3.Error):
                return 'REJECTED'
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(run, range(2)))
        self.assertEqual(['READY','REJECTED'], sorted(outcomes))
        self.assertEqual(1, sum(event['action'] == recovery.CUTOVER for event in self.records()))

    def test_local_only_storage_and_identity_checks(self):
        from flask import Flask
        with Flask(__name__).test_request_context('/not-a-recovery-api'):
            with self.assertRaisesRegex(ValueError, 'local_custodian'):
                self.request()
        with a.connect(self.config.target, write=True) as target:
            target.execute('PRAGMA journal_mode=WAL')
        with self.assertRaisesRegex(ValueError, 'storage_settings'):
            self.request()

    def test_enrollment_rollback_and_lost_commit_acknowledgement(self):
        requested = self.request()
        options = dict(email_challenge=self.mail[-1][1]['email_challenge'],
            code=base.independent_code(self.clock.return_value), approved_request_sha256=requested['request_sha256'])
        before = self.config.control.read_bytes()
        counter = self.counter()
        with patch.object(recovery, '_final_files', side_effect=OSError('synthetic final failure')):
            self.assert_enroll_diagnostic('final_validation')
        self.assertEqual(before, self.config.control.read_bytes())
        with patch.object(recovery, '_commit', side_effect=OSError('before commit')):
            self.assert_enroll_diagnostic('commit')
        self.assertEqual(before, self.config.control.read_bytes())
        self.assertEqual(counter, self.counter())
        commit = recovery._commit
        def lose_ack(control):
            commit(control)
            raise OSError('after commit')
        with patch.object(recovery, '_commit', side_effect=lose_ack):
            self.assert_enroll_diagnostic('commit')
        self.assertEqual(recovery.ENROLLED, self.records()[-1]['action'])
        self.assertGreater(self.counter(), counter)
        self.assertEqual('PUBLICATION_PENDING', recovery.inspect(self.config)['state'])
        self.assertFalse(recovery.certificate_directory(self.config).exists())
        with self.assertRaises(ValueError):
            recovery.enroll(self.config, requested['request_id'], **options)
        recovery.publish_committed(self.config, requested['request_id'])

    def test_cutover_rollback_usable_approval_and_lost_acknowledgement(self):
        self.enroll()
        plan = recovery.plan(self.config, self.root_b, reason='synthetic uncertain commit')['plan']
        before = self.config.control.read_bytes()
        with patch.object(recovery, '_commit', side_effect=OSError('before commit')):
            with self.assertRaises(OSError):
                recovery.cutover(self.config, self.signed(plan), approved_plan_sha256=digest(plan))
        self.assertEqual(before, self.config.control.read_bytes())
        self.assertEqual(self.root_a, governance._root(self.config))
        commit = recovery._commit
        def lose_ack(control):
            commit(control)
            raise OSError('after commit')
        with patch.object(recovery, '_commit', side_effect=lose_ack):
            with self.assertRaises(OSError):
                recovery.cutover(self.config, self.signed(plan), approved_plan_sha256=digest(plan))
        self.assertEqual('PUBLICATION_PENDING', recovery.inspect(self.config)['state'])
        with self.assertRaises(ValueError):
            recovery.cutover(self.config, self.signed(plan), approved_plan_sha256=digest(plan))
        recovery.publish_committed(self.config, plan['id'])
        self.assertEqual(self.root_b, governance._root(self.config))

    def test_pending_publication_rejects_intervening_audit_write(self):
        with patch.object(recovery, '_publish', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                self.enroll()
        pending = recovery.inspect(self.config)['pending_ids'][0]
        with a.connect(self.config.control, write=True) as control:
            a._audit(control, 'unrelated_fixture_audit', 1, self.clock.return_value); control.commit()
        with self.assertRaisesRegex(ValueError, 'publication_stale'):
            recovery.publish_committed(self.config, pending)
        with self.assertRaises(ValueError):
            governance._root(self.config)

    def test_historical_foundation_survives_root_cutover(self):
        from tests.recognition_deployment_qualification_fixture import prepare
        prepare(self.f, self.config)
        preview = self.f.preview()['plan']
        with patch.object(deployment_qualification, 'qualify_locking',
                          side_effect=AssertionError('synthetic completion reached the host probe')) as host_probe:
            complete_test_foundation(self.f, self.f.approval(preview))
        host_probe.assert_not_called()
        before = self.protected()
        self.enroll(); self.rotate()
        with a.connect(self.config.control) as control:
            self.assertEqual(preview, lineage.verify(control))
            event = next(body for _,body in recovery._records(control) if body['action'] == lineage.ACTION)
            modified = dict(event['subject'], signature='A'*88)
            with self.assertRaisesRegex(ValueError, 'audit_provenance'):
                lineage._signed_history(control, event, modified)
        self.assertEqual(before, self.protected())
        with a.connect(self.config.control) as control:
            binding, _, _ = runtime._history(control)
            from src.review.recognition.local_readiness import _state
            self.assertEqual('NOT_ACTIVATED', _state(control, binding)['state'])

    def _foundation(self):
        from tests.recognition_deployment_qualification_fixture import prepare
        prepare(self.f, self.config)
        complete_test_foundation(self.f)

    def _proposal(self, *, orphan=False):
        from uuid import uuid4
        from src.review.recognition import runtime_proposals, runtime_proposal_records as records
        source = self.f.f.f.fixture.request()
        request = dict(request_id=str(uuid4()), family=source['family'], inputs=source['inputs'],
            evaluation_at_utc=source['evaluation_at_utc'], review_reference=source['review_reference'],
            parent_operation_id=None)
        if orphan:
            # Canonical target-first persistence: interrupt AFTER target commit,
            # before the genuine ACK. No manual tables/records or repair path.
            with patch.object(records, 'build_acknowledgement', side_effect=RuntimeError('synthetic ACK failure')):
                with self.assertRaisesRegex(RuntimeError, 'synthetic ACK failure'):
                    runtime_proposals.create_proposal(self.config, self.f.session, request, primary_token=self.f.primary)
        else:
            runtime_proposals.create_proposal(self.config, self.f.session, request, primary_token=self.f.primary)
        with a.connect(self.config.control) as control, a.connect(self.config.target) as target:
            self.assertEqual(0, control.execute('SELECT count(*) FROM recognition_runtime_execution_claims').fetchone()[0])
            self.assertEqual(0 if orphan else 1, control.execute(
                "SELECT count(*) FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",
                (records.ACK_ACTION,)).fetchone()[0])
            self.assertEqual(1, target.execute('SELECT count(*) FROM recognition_operation_contracts').fetchone()[0])

    def test_acknowledged_proposal_without_claims_blocks_enrollment(self):
        self._foundation(); self._proposal()
        before = self.config.control.read_bytes()
        with self.assertRaisesRegex(ValueError, 'recovery_work_present'):
            self.request()
        self.assertEqual(before, self.config.control.read_bytes())
        self.assertEqual([], self.mail)

    def test_acknowledged_proposal_without_claims_blocks_plan_and_cutover(self):
        self.enroll(); self._foundation()
        plan = recovery.plan(self.config, self.root_b, reason='synthetic pre-work plan')['plan']
        self._proposal()
        before = self.config.control.read_bytes()
        with self.assertRaisesRegex(ValueError, 'recovery_work_present'):
            recovery.plan(self.config, self.root_b, reason='reject pending proposal')
        with self.assertRaisesRegex(ValueError, 'recovery_work_present'):
            recovery.cutover(self.config, self.signed(plan), approved_plan_sha256=digest(plan))
        self.assertEqual(before, self.config.control.read_bytes())
        self.assertEqual(self.root_a, governance._root(self.config))

    def test_target_only_operation_without_ack_or_claims_blocks_cutover(self):
        self.enroll(); self._foundation()
        plan = recovery.plan(self.config, self.root_b, reason='synthetic pre-work plan')['plan']
        self._proposal(orphan=True)
        before = self.config.control.read_bytes()
        with self.assertRaisesRegex(ValueError, 'recovery_work_present'):
            recovery.plan(self.config, self.root_b, reason='reject target-only operation')
        with self.assertRaisesRegex(ValueError, 'recovery_work_present'):
            recovery.cutover(self.config, self.signed(plan), approved_plan_sha256=digest(plan))
        self.assertEqual(before, self.config.control.read_bytes())
        self.assertEqual(self.root_a, governance._root(self.config))

    def test_conflicting_certificate_extra_file_and_no_source_repair(self):
        self.enroll()
        directory = recovery.certificate_directory(self.config)
        extra = directory/'cutover-00000099.json'; extra.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'uncommitted_certificate'):
            governance._root(self.config)
        extra.unlink()
        original = directory/'enrollment.json'
        hardlink = directory/'linked'; __import__('os').link(original, hardlink)
        try:
            with self.assertRaises(ValueError):
                governance._root(self.config)
        finally:
            hardlink.unlink()
        self.assertEqual(self.original_bytes, governance.trust_path(self.config).read_bytes())

    def test_offline_recovery_key_and_exact_domain_signer(self):
        import tempfile
        from scripts.operator import recognition_governance_recovery as tool
        from scripts.operator import recognition_governance as operator
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        with tempfile.TemporaryDirectory(prefix='offline-recovery-synthetic-') as directory:
            folder = Path(directory).resolve()
            private_path, public_path = folder/'recovery.pem', folder/'public.json'
            password = b'synthetic-offline-test-passphrase'
            with patch.object(operator, '_password', return_value=password), redirect_stdout(io.StringIO()) as logs:
                tool.keygen(private_path, public_path, self.root_a['installation_id'], 1)
            key = load_pem_private_key(private_path.read_bytes(), password=password)
            with self.assertRaises(TypeError):
                load_pem_private_key(private_path.read_bytes(), password=None)
            self.recovery_key = load(public_path.read_text())
            self.r = key
            self.enroll()
            plan = recovery.plan(self.config, self.root_b, reason='synthetic offline signer')['plan']
            payload, output = folder/'plan.json', folder/'signed.json'
            # Exercise creation under a POSIX umask that allows group writes.
            previous_umask = os.umask(0o002) if os.name == 'posix' else None
            try:
                payload.touch(mode=0o600, exist_ok=False)
            finally:
                if previous_umask is not None:
                    os.umask(previous_umask)
            if os.name == 'posix':
                self.assertEqual(0o600, payload.stat().st_mode & 0o777)
            payload.write_text(canonical(plan), encoding='utf-8')
            with patch.object(operator, '_password', return_value=password), patch('builtins.input', return_value=digest(plan)), redirect_stdout(logs):
                tool.sign(private_path, public_path, payload, output)
            envelope = load(output.read_text())
            self.assertEqual({'serialized_approval','signature'}, set(envelope))
            recovery._verify_signature(self.recovery_key, plan, envelope)
            recovery.cutover(self.config, envelope, approved_plan_sha256=digest(plan))
            with self.assertRaises(ValueError):
                tool.sign(private_path, public_path, payload, output)
            self.assertFalse(private_path.is_relative_to(operator.REPOSITORY))
            self.assertNotIn(password.decode(), logs.getvalue())
            for path in recovery.certificate_directory(self.config).iterdir():
                self.assertNotIn('PRIVATE KEY', path.read_text())


class RecoveryClockTests(unittest.TestCase):
    def exercise(self, *, final_utc, elapsed_ns, error=None, sample_interval=False):
        from src.review.recognition import runtime_execution_claims as claims
        for action in ('enroll', 'cutover'):
            with self.subTest(action=action):
                f = GovernanceRecoveryTests()
                try:
                    f.setUp()
                    if action == 'enroll':
                        requested = f.request()
                        approval = requested['request']
                        def operation():
                            return recovery.enroll(f.config, requested['request_id'],
                                email_challenge=f.mail[-1][1]['email_challenge'],
                                code=base.independent_code(base.at(830)),
                                approved_request_sha256=requested['request_sha256'])
                    else:
                        f.enroll()
                        approval = recovery.plan(f.config, f.root_b, reason='synthetic clock boundary')['plan']
                        def operation():
                            return recovery.cutover(f.config, f.signed(approval), approved_plan_sha256=digest(approval))
                    self.assertEqual(base.at(840), approval['expires_at_utc'])
                    f.clock.return_value = base.at(830)  # Only TEN seconds remain.
                    before = f.config.control.read_bytes(), f.config.target.read_bytes()
                    late = [False]
                    final_samples = iter((1_000_000_000+9_900_000_000, 1_000_000_000+10_100_000_000))
                    def monotonic_ns():
                        if not late[0]:
                            return 1_000_000_000
                        return next(final_samples) if sample_interval else 1_000_000_000+elapsed_ns
                    original = recovery._final_files
                    def after_validation(*args):
                        original(*args)
                        f.clock.return_value = base.at(final_utc)
                        late[0] = True
                    # Real paired-clock implementation; deterministic independent
                    # UTC/monotonic samples, no sleeps or clock-check bypasses.
                    with patch.object(claims.time, 'monotonic_ns', side_effect=monotonic_ns), \
                            patch.object(recovery, '_final_files', side_effect=after_validation):
                        if error:
                            with self.assertRaisesRegex(ValueError, error):
                                operation()
                        else:
                            self.assertEqual('READY', operation()['state'])
                    if error:
                        self.assertEqual(before, (f.config.control.read_bytes(), f.config.target.read_bytes()))
                        self.assertEqual(f.root_a, governance._root(f.config))
                        self.assertFalse(any(e['action'] == (recovery.ENROLLED if action == 'enroll' else recovery.CUTOVER)
                                             for e in f.records()))
                    else:
                        self.assertEqual(f.root_a if action == 'enroll' else f.root_b, governance._root(f.config))
                    self.assertEqual(f.original_bytes, governance.trust_path(f.config).read_bytes())
                finally:
                    f.doCleanups()

    def test_utc_rollback_before_commit_rejects_and_rolls_back(self):
        self.exercise(final_utc=820, elapsed_ns=20_000_000_000, error='runtime_claim_clock_anomaly')

    def test_frozen_utc_with_advancing_monotonic_rejects_and_rolls_back(self):
        self.exercise(final_utc=830, elapsed_ns=20_000_000_000, error='runtime_claim_clock_anomaly')

    def test_expiry_during_transaction_rejects_and_rolls_back(self):
        self.exercise(final_utc=840, elapsed_ns=10_000_000_000, error='recovery_.*expired')

    def test_remaining_lifetime_is_clipped_at_end_of_clock_sample(self):
        # The UTC sample is still 839 and the paired sampler's before/after
        # interval is consistent. Its END exceeds the original remaining 10s,
        # so a fresh 600s budget (or UTC-only check) would incorrectly accept.
        self.exercise(final_utc=839, elapsed_ns=0, sample_interval=True, error='recovery_.*expired')

    def test_consistent_clocks_empty_work_and_remaining_lifetime_succeed(self):
        self.exercise(final_utc=839, elapsed_ns=9_000_000_000)


class SuccessorRecoveryTests(unittest.TestCase):
    def fixture(self):
        from tests.test_recognition_runtime_profile_successor import SuccessorTests
        f = SuccessorTests()
        f.setUp(); self.addCleanup(f.doCleanups)
        fixture_acl_checks(self)
        from src.review.recognition import runtime_execution_claims as claims
        self.enterContext(patch.object(claims.time, 'monotonic_ns',
            side_effect=lambda:a.timestamp(runtime._utc_now())*1_000_000_000))
        return f

    def recover(self, f):
        f.f.f.clock.return_value = base.at(240)
        recovery_key, replacement = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
        key = dict(format=recovery.KEY_FORMAT, installation_id=f.root['installation_id'],
                   owner_id=f.root['owner_id'], public_key=public(recovery_key))
        root_b = dict(f.root, public_key=public(replacement))
        mail = []
        with patch('flask.has_request_context', return_value=False), patch.object(email_delivery,
                'governance_recovery_sender_from_env', return_value=lambda recipient,message,minutes:mail.append(load(message))):
            request = recovery.request_enrollment(f.config, key, reason='synthetic G6 recovery')
            recovery.enroll(f.config, request['request_id'], email_challenge=mail[0]['email_challenge'],
                code=base.independent_code(base.at(240)), approved_request_sha256=request['request_sha256'])
            proposed = recovery.plan(f.config, root_b, reason='synthetic G6 cutover')['plan']
            envelope = dict(serialized_approval=canonical(proposed),
                signature=base64.b64encode(recovery_key.sign(recovery.signing_bytes(proposed))).decode())
            recovery.cutover(f.config, envelope, approved_plan_sha256=digest(proposed))
        f.root = root_b; f.f.key = replacement

    def test_committed_g6_signed_by_a_remains_valid_after_recovery_to_b(self):
        from src.review.recognition import runtime_profile_successor as successor
        from src.review.recognition import runtime_profile_successor_contract as contract
        f = self.fixture()
        f.prepare(); plan = f.plan()
        successor.complete(f.config, f.envelope(contract.COMPLETE, plan=plan), f.prepared['nonce'])
        original_g5 = contract.SOURCE_BINDING
        self.recover(f)
        self.assertEqual(6, runtime.validate_runtime_snapshot(f.config)['generation'])
        with a.connect(f.config.control) as control:
            self.assertEqual(original_g5, control.execute('SELECT body_sha256 FROM recognition_admin_bindings WHERE generation=5').fetchone()[0])
        status = successor.inspect(f.config, f.envelope(contract.INSPECT, authorization_id=f.identifier))
        self.assertEqual('COMMITTED', status['state'])
        f.current_device = 63
        with self.assertRaisesRegex(a.AdminError, 'runtime_profile_identity_mismatch'):
            runtime.validate_runtime_snapshot(f.config)

    def test_recover_at_g5_then_existing_exact_g5_to_g6_ceremony(self):
        from src.review.recognition import runtime_profile_successor as successor
        from src.review.recognition import runtime_profile_successor_contract as contract
        f = self.fixture()
        self.recover(f)
        with self.assertRaisesRegex(a.AdminError, 'runtime_profile_identity_mismatch'):
            runtime.validate_runtime_snapshot(f.config)
        f.prepare(); plan = f.plan()
        result = successor.complete(f.config, f.envelope(contract.COMPLETE, plan=plan), f.prepared['nonce'])
        self.assertEqual((6, False), (result['generation'], result['execution_authority']))
        self.assertEqual(6, runtime.validate_runtime_snapshot(f.config)['generation'])
        # The actual downstream deployment path still uses fresh G6 owner MFA,
        # qualification and exact-plan Root B foundation authorization.
        from src.review.recognition import runtime_activation as owner
        from tests.recognition_deployment_qualification_fixture import prepare
        f.f.f.clock.return_value = base.at(270)
        f.f.primary = owner.record_primary_authentication(f.config, actor_id=1, reviewer_key='owner-key')
        f.f.session = owner.open_admin_session(f.config, f.f.primary, base.independent_code(base.at(270)))
        prepare(self, f.config)
        foundation_plan = f.f.preview()['plan']
        completed = complete_test_foundation(f.f, f.f.approval(foundation_plan))
        self.assertEqual(('COMPLETED', 6, False),
            (completed['state'], completed['generation'], completed['execution_authority']))
        self.assertEqual('NOT_ACTIVATED', completed['production_state'])
        self.assertEqual(6, runtime.validate_runtime_snapshot(f.config)['generation'])
        f.current_device = 63
        with self.assertRaisesRegex(a.AdminError, 'runtime_profile_identity_mismatch'):
            runtime.validate_runtime_snapshot(f.config)


class RecoveryEmailTests(unittest.TestCase):
    def test_message_is_purpose_bound_and_no_dev_outbox(self):
        message = email_delivery.governance_recovery_message('sender@example.test','owner@example.test',
            'synthetic exact request and token', 10)
        self.assertIn('governance recovery enrollment', str(message['Subject']))
        self.assertIn('NOT a sign-in link', message.get_content())
        with self.assertRaises(email_delivery.EmailConfigurationError):
            email_delivery.governance_recovery_sender_from_env({'REVIEWER_AUTH_DEV_MODE':'1'})
        env = dict(REVIEWER_EMAIL_BACKEND='resend', REVIEWER_EMAIL_FROM='sender@example.test', RESEND_API_KEY='synthetic-test')
        with patch.object(email_delivery.requests,'post') as send:
            send.return_value.status_code=200; send.return_value.json.return_value={'id':'synthetic'}
            email_delivery.governance_recovery_sender_from_env(env)('owner@example.test','synthetic token',10)
        self.assertEqual('Approve DMV Bus Stops offline governance recovery enrollment', send.call_args.kwargs['json']['subject'])


class RecoveryToolTests(unittest.TestCase):
    def test_posix_publication_syncs_directory_parent(self):
        from unittest.mock import MagicMock
        from scripts.operator import recognition_governance as operator
        directory = MagicMock(); directory.exists.return_value = True
        order = []
        with patch.object(recovery, 'certificate_directory', return_value=directory), \
                patch.object(recovery, '_protected'), patch.object(operator, '_publish', side_effect=lambda *args:order.append('publish')), \
                patch.object(recovery.os, 'name', 'posix'), patch.object(recovery.os, 'O_DIRECTORY', 0, create=True), \
                patch.object(recovery.os, 'open', return_value=123) as opened, \
                patch.object(recovery.os, 'fsync', side_effect=lambda fd:order.append('sync')), \
                patch.object(recovery.os, 'close') as closed:
            recovery._publish(None, 'enrollment.json', dict(public='synthetic'))
        self.assertEqual(['publish','sync'], order)
        self.assertEqual(directory.parent, opened.call_args.args[0])
        closed.assert_called_once_with(123)

    def test_non_enrollment_failure_keeps_generic_error_contract(self):
        from scripts.operator import recognition_governance_recovery as tool
        from src.api import sqlite_runtime
        marker = 'SENTINEL-SECRET-KEY-PATH-TOTP-NEVER-PRINT'
        root = dict(format=governance.FORMAT, mandate=governance.contract.MANDATE,
            installation_id='aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee', owner_id=1,
            public_key=base64.b64encode(b'x'*32).decode())
        # Output-boundary unit test only: no DB, email transport or key access.
        folder = Path(__file__).resolve().parent
        args = ['inspect', '--target', str(folder/'not-created-target.db'), '--control', str(folder/'not-created-control.db'),
            '--key-file', str(folder/'not-created.key'), '--installation-id', root['installation_id'], '--owner-id', '1',
            '--original-public-key-sha256', recovery.fingerprint(root)]
        with patch.object(sqlite_runtime, 'load_production_sqlite'), patch.object(recovery, '_original', return_value=root), \
                patch.object(recovery, 'inspect', side_effect=OSError(marker)), \
                patch('sys.stdout', new_callable=io.StringIO) as out, patch('sys.stderr', new_callable=io.StringIO) as err:
            self.assertEqual(1, tool.main(args))
        self.assertEqual('', out.getvalue())
        self.assertEqual(canonical(dict(error='governance_recovery_outcome_unconfirmed',
                                        inspect_before_retry=True, execution_authority=False)) + '\n', err.getvalue())

    def test_parser_never_echoes_secret_content(self):
        from scripts.operator import recognition_governance_recovery as tool
        marker = 'SENTINEL-SECRET-KEY-PATH-TOTP-NEVER-PRINT'
        with patch('sys.stderr', new_callable=io.StringIO) as err, self.assertRaises(SystemExit):
            tool.main(['keygen', '--passphrase', marker])
        self.assertNotIn(marker, err.getvalue())


if __name__ == '__main__':
    unittest.main()
