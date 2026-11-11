"""Disposable activated ledger fixtures; real current readers, no writer use."""

from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
import pickle
import sqlite3
import threading
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, administration_schema, admin_auth
from src.review.recognition import runtime_activated_owner as owner, runtime_validation as v
from src.review.recognition import runtime_scope_validation as shared, runtime_approval_contract
from src.review.recognition import runtime_claim_consumption as consumption, runtime_claim_validation
from src.review.recognition import runtime_proposal_transaction as proposal, runtime_claim_disposition
from src.review.recognition import local_readiness as readiness, production_operations, writer_boundary
from src.review.recognition import execution, local_execution, events, approvals
from src.review.recognition.rules import digest, canonical
from tests import test_recognition_runtime_execution_claims as lifecycle
from tests import test_recognition_runtime_claim_disposition as disposition_fixtures


class RuntimeActivatedOwnerTests(unittest.TestCase):
    def setUp(self):
        self.f = lifecycle.RuntimeExecutionClaimTests()
        install = a.install
        def prepared_control(config, **options):
            # Install readiness BEFORE the existing migration freezes its exact
            # control-schema manifest; never repair an already-frozen manifest.
            result = install(config, **options)
            with a.connect(config.control, write=True) as control:
                control.execute('BEGIN IMMEDIATE')
                for name, sql in readiness.definitions().items():
                    if not control.execute('SELECT 1 FROM sqlite_master WHERE name=?', (name,)).fetchone():
                        control.execute(sql)
                binding = a._binding(control)
                readiness._append(control,binding,'NOT_ACTIVATED',binding['owner_id'],'disposable genesis',options['now'])
                if not execution._stop(control)['sequence']:
                    body = dict(sequence=1, active=False, reason='disposable stop genesis', actor='owner',
                                recorded_at_utc=options['now'], previous_sha256=None)
                    events._insert(control,'recognition_execution_stops','sequence',(1,),body)
                control.commit()
            return result
        with patch.object(a,'install',side_effect=prepared_control):
            self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config = self.f.config
        self.primary, self.session = self.f.f.primary, self.f.f.session
        self.approval = self.f.f.approval
        self.reference = self.f.f.reference
        self.clock = self.f.clock
        self.handoff = None
        if self._testMethodName.startswith('test_claim_') or self._testMethodName == 'test_preactivation_handoff_cannot_be_promoted':
            self.claim = self.f.acquire()
            self.body = json.loads(self.claim.canonical_json)
            if self._testMethodName in ('test_claim_consumed_is_not_completion', 'test_preactivation_handoff_cannot_be_promoted'):
                with consumption.consume(self.config, self.claim, self.f.snapshot, self.session,
                                         primary_token=self.primary) as handoff:
                    self.handoff = handoff  # Retired preactivation object, not authority.
            elif self._testMethodName == 'test_claim_revoked_is_historical':
                self.transition('REVOKED', 1)
                self.clock.return_value = self.at(1)
            elif self._testMethodName == 'test_claim_recovery_required_blocks':
                self.transition('CONSUMED', 1)
                self.transition('RECOVERY_REQUIRED', 2)
                # Activation must follow the deliberately advanced fixture events.
                self.clock.return_value = self.at(2)
            elif self._testMethodName == 'test_claim_expired_is_historical':
                self.clock.return_value = self.at(300)
        self.activation = self.activate_fixture()
        self.options = dict(primary_token=self.primary,
            approval_sha256=self.approval['approval_sha256'], reference=self.reference,
            activation_sha256=digest(self.activation))

    at = disposition_fixtures.RuntimeClaimDispositionTests.at
    transition = disposition_fixtures.RuntimeClaimDispositionTests.transition

    def activate_fixture(self):
        # Schema/ledger test fixture only: no production API/provider or bypass
        # is added. The actual authoritative activation verifier is NOT mocked.
        with a.connect(self.config.control, write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            binding, _, _ = v._history(control)
            now = v._utc_now()
            if not control.execute('SELECT 1 FROM recognition_local_activation').fetchone():
                readiness._append(control, binding, 'NOT_ACTIVATED', binding['owner_id'], 'disposable genesis', now)
            a._audit(control, 'local_deployment_rehearsal_recorded', 'disposable-test', now,
                dict(target=production_operations.local_target(binding),
                     evidence={key:digest(dict(disposable=key)) for key in readiness.REHEARSAL_CHECKS},
                     reason='synthetic observations, not hosted verification',
                     backup=dict(frequency='daily', retention_days=30, restore_verified=True)))
            # Explicit immutable ledger/used confirmation fixture. It establishes
            # verifier input only, not a new v3 activation issuance path.
            confirmation_hash = digest(dict(disposable_activation=True))
            ceremony_hash = digest(dict(disposable_review=True))
            control.execute('INSERT INTO recognition_admin_confirmations VALUES(?,?,?,?,?,?,?,?,1)',
                (confirmation_hash, a.token_hash(self.session), binding['owner_id'],
                 'activation:'+binding['installation_id'], digest(production_operations.local_target(binding)),
                 ceremony_hash, binding['generation'], a.timestamp(now)+600))
            confirmation = control.execute('SELECT * FROM recognition_admin_confirmations WHERE token_hash=?',
                                           (confirmation_hash,)).fetchone()
            result = readiness._append(control, binding, 'ACTIVATED', binding['owner_id'],
                'disposable valid-ledger fixture, not deployment activation', now,
                scope='trusted-local-production', confirmation=confirmation)
            administration_schema.check_control(control)
            self.assertEqual(result, readiness.require_activated(control, binding))
            control.commit()
            return result

    def validate(self, **changes):
        options = dict(self.options)
        session = changes.pop('session', self.session)
        approval_id = changes.pop('approval_id', self.approval['approval']['approval_id'])
        options.update(changes)
        return owner.validation_transaction(self.config, session, approval_id, **options)

    def sql(self, sql, values=(), *, target=False):
        with a.connect(self.config.target if target else self.config.control, write=True) as conn:
            rows = conn.execute(sql, values).fetchall()
            conn.commit()
            return rows

    def assert_no_authority(self, result):
        self.assertFalse(result.snapshot['execution_authority'])
        self.assertFalse(writer_boundary.verify_local(result, self.config.target, {}))
        with self.assertRaises(ValueError): writer_boundary.acquire(result, self.config.target, {})
        with self.assertRaises(ValueError): production_operations.context_data(result)
        with self.assertRaises(ValueError): execution._context(result)
        self.assertEqual('BLOCKED', local_execution.execute_approved_operation(result, self.session,
            self.approval['approval']['approval_id'], now=v._utc_now()).admission)

    def test_success_zero_writes_secret_isolation_and_no_authority(self):
        before = self.f.dump()
        leases = dict(writer_boundary._local_leases), dict(writer_boundary._leases)
        with self.validate() as result:
            body = result.snapshot
            self.assertEqual(digest(self.activation), body['activation_sha256'])
            self.assertEqual(self.reference, dict(body['reference']))
            self.assert_no_authority(result)
            text = repr(body)
            with a.connect(self.config.control) as control:
                seed = control.execute('SELECT seed_ciphertext FROM recognition_admin_mfa WHERE actor=1').fetchone()[0]
            for secret in (self.primary, self.session, seed, self.config.key_file.read_text().strip()):
                self.assertNotIn(secret, text)
            for name in ('control', 'target', 'view', 'cipher', 'seed', 'writer', 'consume', 'activate'):
                self.assertFalse(hasattr(result, name))
            with self.assertRaises(TypeError): pickle.dumps(result)
            with self.assertRaises(TypeError): owner.ActivatedAdmission()
            with self.assertRaises(TypeError): body['execution_authority'] = True
        self.assertEqual(before, self.f.dump())
        self.assertEqual(leases, (dict(writer_boundary._local_leases), dict(writer_boundary._leases)))
        with self.assertRaises(ValueError): result.snapshot
        with self.assertRaisesRegex(a.AdminError, 'runtime_requires_not_activated'):
            v.validate_runtime_snapshot(self.config)
        with self.assertRaisesRegex(a.AdminError, 'runtime_profile_contract_not_enabled'):
            a.get_installation_control(self.config)

    def test_authentication_denial_persists_existing_reductions_control_only(self):
        self.sql('UPDATE recognition_admin_primary SET expires=? WHERE token_hash=?',
                 (a.timestamp(v._utc_now()), a.token_hash(self.primary)))
        before = self.f.dump()
        with self.assertRaises(a.AdminError):
            with self.validate(): self.fail('expired authentication accepted')
        after = self.f.dump()
        self.assertEqual(before[1], after[1])
        changed = {table for table in before[0] if before[0][table] != after[0][table]}
        self.assertEqual({'recognition_admin_primary', 'recognition_admin_sessions', 'recognition_admin_audit'}, changed)
        self.assertEqual(1, self.sql('SELECT revoked FROM recognition_admin_primary WHERE token_hash=?',
                                   (a.token_hash(self.primary),))[0][0])
        self.assertEqual(1, self.sql('SELECT revoked FROM recognition_admin_sessions WHERE token_hash=?',
                                   (a.token_hash(self.session),))[0][0])
        latest = max(after[0]['recognition_admin_audit'],key=lambda row:row[0])
        self.assertEqual('administration_denied', json.loads(latest[1])['action'])

    def test_runtime_and_readiness_rejection_do_not_invent_mutations(self):
        before = self.f.dump()
        with self.assertRaisesRegex(a.AdminError, 'incarnation'):
            with self.validate(activation_sha256='0'*64): pass
        with patch.object(admin_auth, '_cipher', side_effect=a.AdminError('host_key_unavailable', 503)):
            with self.assertRaisesRegex(a.AdminError, 'host_key_unavailable'):
                with self.validate(): pass
        self.assertEqual(before, self.f.dump())
        self.sql("UPDATE recognition_admin_mfa SET epoch=epoch+1 WHERE actor=1")
        target_before = self.f.dump()[1]
        with self.assertRaises(a.AdminError):
            with self.validate(): pass
        self.assertEqual(target_before, self.f.dump()[1])

    def test_approval_legacy_digest_reference_and_epoch_fences(self):
        before = self.f.dump()
        legacy = self.sql('SELECT approval_id FROM recognition_approvals WHERE approval_id!=?',
                          (self.approval['approval']['approval_id'],))[0][0]
        for changes in (dict(approval_id=legacy), dict(approval_sha256='0'*64),
                        dict(reference=dict(self.reference, acknowledgement_sha256='0'*64))):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                with self.validate(**changes): pass
        self.assertEqual(before, self.f.dump())
        self.sql('UPDATE recognition_local_installation SET auth_epoch=auth_epoch+1', target=True)
        target_before = self.f.dump()[1]
        with self.assertRaises(ValueError):
            with self.validate(): pass
        self.assertEqual(target_before, self.f.dump()[1])

    def test_every_physical_observation_and_logical_scope_mismatch(self):
        observe = a.target_identity.side_effect
        for which in ('control', 'target'):
            for field, value in (('hostname','wrong-host'), ('device',987654), ('inode',987654),
                                  ('database',str(self.config.target.parent/'other.db'))):
                def changed(subject):
                    original = observe(subject)
                    return replace(original, **{field:value}) if original.database == str(getattr(self.config,which)) else original
                with self.subTest(which=which,field=field), patch.object(a,'target_identity',side_effect=changed):
                    with self.assertRaises(ValueError):
                        with self.validate(): pass
        for field, value in (('installation_id','00000000-0000-0000-0000-000000000000'),
                             ('target_id','00000000-0000-0000-0000-000000000000'), ('owner_id',2)):
            old = self.sql('SELECT '+field+' FROM recognition_local_installation', target=True)[0][0]
            self.sql('UPDATE recognition_local_installation SET '+field+'=?', (value,), target=True)
            before = self.f.dump()
            with self.subTest(field=field), self.assertRaises(ValueError):
                with self.validate(): pass
            self.assertEqual(before, self.f.dump())
            self.sql('UPDATE recognition_local_installation SET '+field+'=?', (old,), target=True)

    def test_stop_and_dependency_changes_fail_without_writes(self):
        with a.connect(self.config.control, write=True) as control:
            previous = execution._stop(control)
            body = dict(sequence=previous['sequence']+1, active=True, reason='test stop', actor='owner',
                        recorded_at_utc=v._utc_now(), previous_sha256=digest(previous))
            events._insert(control, 'recognition_execution_stops', 'sequence', (body['sequence'],), body)
            control.commit()
        before = self.f.dump()
        with self.assertRaisesRegex(a.AdminError, 'readiness_blocked'):
            with self.validate(): pass
        self.assertEqual(before, self.f.dump())

    def test_process_thread_lifetime_and_reservation_identity(self):
        with self.validate() as result:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(lambda: result.snapshot)
                with self.assertRaises(ValueError): future.result()
            with patch.object(owner.os, 'getpid', return_value=os.getpid()+1):
                with self.assertRaises(ValueError): result.snapshot
            with patch.object(owner.threading, 'current_thread', return_value=threading.Thread()):
                with self.assertRaises(ValueError): result.snapshot
            self.assertFalse(result.snapshot['execution_authority'])

    def test_connection_and_reservation_replacement_permanently_poison(self):
        for field in ('control','target','control_reservation_epoch','target_reservation_epoch'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                with self.validate() as result:
                    state = owner._contexts[result]
                    original = getattr(state,field)
                    setattr(state,field,original+1 if type(original) is int else object())
                    with self.assertRaises(ValueError): result.snapshot
                    setattr(state,field,original)  # Restoration cannot unpoison.
                    with self.assertRaises(ValueError): result.snapshot

    def test_fresh_profile_generation_and_authentication_scope_comparison(self):
        real = v._identity_snapshot
        with self.validate() as result:
            for field in ('profile_sha256','binding_sha256','generation','installation_id','target_id','owner_id','auth_epoch'):
                def changed(*args):
                    scope = dict(real(*args))  # Run ALL real checks first.
                    scope[field] = scope[field]+1 if type(scope[field]) is int else '0'*64
                    return scope
                with self.subTest(field=field), patch.object(v,'_identity_snapshot',side_effect=changed):
                    with self.assertRaisesRegex(ValueError,'runtime_validation_changed'): result.snapshot
            with patch.object(shared,'_mfa',return_value=owner._contexts[result].mfa_epoch+1):
                with self.assertRaisesRegex(ValueError,'runtime_validation_changed'): result.snapshot

    def test_actual_schema_dependency_and_approval_invalidation(self):
        self.sql('CREATE TABLE changed_target_schema(value)',target=True)
        before = self.f.dump()
        with self.assertRaisesRegex(ValueError,'schema_mismatch'):
            with self.validate(): pass
        self.assertEqual(before,self.f.dump())
        self.sql('DROP TABLE changed_target_schema',target=True)
        self.sql("UPDATE stop_review_assignments SET status='assigned' WHERE id=(SELECT MIN(id) FROM stop_review_assignments)",target=True)
        before = self.f.dump()
        with self.assertRaises(ValueError):
            with self.validate(): pass
        self.assertEqual(before,self.f.dump())
        with a.connect(self.config.control,write=True) as control:
            approvals._invalidate_all(control,'owner',v._utc_now(),'explicit test invalidation')
            control.commit()
        before = self.f.dump()
        with self.assertRaisesRegex(ValueError,'runtime_approval_not_current'):
            with self.validate(): pass
        self.assertEqual(before,self.f.dump())

    def test_activation_requires_current_authoritative_ceremony(self):
        self.sql('UPDATE recognition_admin_confirmations SET used=0 WHERE token_hash=?',
                 (self.activation['confirmation_sha256'],))
        before = self.f.dump()
        with self.assertRaisesRegex(ValueError,'activation_ceremony_required'):
            with self.validate(): pass
        self.assertEqual(before,self.f.dump())
        self.sql('UPDATE recognition_admin_confirmations SET used=1 WHERE token_hash=?',
                 (self.activation['confirmation_sha256'],))
        with a.connect(self.config.control,write=True) as control:
            binding, _, _ = v._history(control)
            readiness._append(control,binding,'SUSPENDED',binding['owner_id'],'disposable suspend',v._utc_now())
            control.commit()
        before = self.f.dump()
        with self.assertRaisesRegex(ValueError,'activation_deployment_blocked'):
            with self.validate(): pass
        self.assertEqual(before,self.f.dump())

    def test_lifecycle_attempts_poison_even_when_body_catches_exception(self):
        for action in ('commit','rollback','execute'):
            with self.subTest(action=action), self.assertRaises(ValueError):
                with self.validate() as result:
                    with self.assertRaises(ValueError): getattr(result,action)
                    with self.assertRaises(ValueError): result.snapshot
        for sql in ('COMMIT', 'ROLLBACK', 'SAVEPOINT forged', 'PRAGMA query_only=OFF'):
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                with self.validate() as result:
                    # Fault injection uses a PRIVATE handle to test the manager
                    # authorizer itself, not a handle exposed to the body.
                    state = owner._contexts[result]
                    with self.assertRaises(sqlite3.DatabaseError): state.target.execute(sql)

    def test_target_write_denial_delete_and_wal_and_commit_order(self):
        real_connect = a.connect
        for mode in ('DELETE','WAL'):
            self.sql('PRAGMA journal_mode='+mode, target=True)
            before = self.f.dump()
            connections, commits, target_sql = {}, [], []
            @contextmanager
            def traced(path, *, write=False):
                with real_connect(path,write=write) as conn:
                    connections[path] = conn
                    if path == self.config.control:
                        def trace(sql):
                            if sql == 'COMMIT': commits.append(connections[self.config.target].in_transaction)
                    else:
                        trace = target_sql.append
                    conn.set_trace_callback(trace)
                    yield conn
            with patch.object(a,'connect',side_effect=traced):
                with self.validate() as result:
                    state = owner._contexts[result]
                    self.assertEqual(1,state.target.execute('PRAGMA query_only').fetchone()[0])
                    self.assertEqual(0,state.target.total_changes)
                    self.assertEqual(0,state.control.total_changes)
            self.assertEqual([True],commits)
            self.assertFalse(any(sql.split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP','COMMIT'}
                                 for sql in target_sql))
            self.assertEqual(before,self.f.dump())
            for sql in ('INSERT INTO recognition_execution_storage SELECT * FROM recognition_execution_storage',
                        'UPDATE community_reviewers SET role=role', 'DELETE FROM community_reviewers',
                        'CREATE TABLE forbidden(value)'):
                with self.subTest(mode=mode,sql=sql), self.assertRaises(ValueError):
                    with self.validate() as result:
                        with self.assertRaises(sqlite3.DatabaseError): owner._contexts[result].target.execute(sql)

    def test_preactivation_handoff_cannot_be_promoted(self):
        with self.assertRaises(ValueError):
            with owner.validation_transaction(self.handoff,self.session,self.approval['approval']['approval_id'],**self.options): pass
        with self.assertRaises(ValueError): self.handoff.snapshot
        with self.validate() as result: self.assert_no_authority(result)

    def test_claim_live_issued_blocks(self):
        before = self.f.dump()
        with self.assertRaisesRegex(a.AdminError,'claim_disposition'):
            with self.validate(): pass
        self.assertEqual(before,self.f.dump())

    def test_claim_recovery_required_blocks(self):
        before = self.f.dump()
        with self.assertRaisesRegex(a.AdminError,'claim_disposition'):
            with self.validate(): pass
        self.assertEqual(before,self.f.dump())

    def check_historical_claim(self, disposition):
        before = self.f.dump()
        with self.validate() as result:
            row = result.snapshot['claim_disposition'][0]
            self.assertEqual(disposition,row['disposition'])
            self.assertEqual('NOT_ESTABLISHED',row['completion'])
            self.assertFalse(row['blocks_readiness'])
        self.assertEqual(before,self.f.dump())

    def test_claim_expired_is_historical(self): self.check_historical_claim('EXPIRED_ISSUED')

    def test_claim_revoked_is_historical(self): self.check_historical_claim('REVOKED')

    def test_claim_consumed_is_not_completion(self): self.check_historical_claim('CONSUMED')
