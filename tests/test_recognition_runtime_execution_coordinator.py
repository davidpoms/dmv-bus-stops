"""Real disposable issuance; no attempt producer, runtime writer or activation API."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from datetime import timedelta
from dataclasses import replace
import os
import pickle
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from uuid import UUID

from src.review.recognition import administration as a, authorization, administration_schema
from src.review.recognition import runtime_execution_coordinator as c, runtime_activation_authority_issuance as issuer
from src.review.recognition import runtime_execution_attempt_schema as attempts, runtime_activation_authority_schema as storage
from src.review.recognition import runtime_validation as v, runtime_scope_validation as shared, local_readiness
from src.review.recognition import writer_boundary, production_operations, execution, approvals, events, dependencies
from src.review.recognition import runtime_proposal_records as records, admin_auth, local_execution, permanent
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import load, utc
from tests import test_recognition_runtime_activation_authority_issuance as fixtures
from tests import test_recognition_runtime_activation_authority_schema as schema_fixtures


class RuntimeExecutionCoordinatorTests(unittest.TestCase):
    def setUp(self):
        # Install inert attempt storage BEFORE the existing fixture's synthetic
        # activation. No migration of an active installation and no audit repair.
        migrate = schema_fixtures.ActivationAuthoritySchemaTests.migrate
        def installed(fixture, **options):
            result = migrate(fixture, **options)
            with patch.object(a, 'target_identity', side_effect=authorization.target_identity):
                attempts.migrate(fixture.config, expected_generation=3, operator='fixture', reason='inert storage fixture')
            return result
        self.f = fixtures.ActivationAuthorityIssuanceTests()
        with patch.object(schema_fixtures.ActivationAuthoritySchemaTests, 'migrate', installed):
            self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config, self.session, self.primary = self.f.config, self.f.session, self.f.primary
        self.scope, self.approval_id = dict(self.f.scope), self.f.approval_id

    def coordinator(self, **changes):
        return c.coordinator(self.config, self.session, self.f.confirmation['token'], self.approval_id,
                             **dict(self.scope, **changes))

    def sql(self, sql, args=(), *, target=False):
        return self.f.f.sql(sql, args, target=target)

    def assert_inert(self):
        with a.connect(self.config.control) as control:
            administration_schema.check_control(control)
            for table in (attempts.ATTEMPTS, attempts.HISTORY, 'recognition_runtime_execution_claims'):
                self.assertEqual(0, control.execute('SELECT count(*) FROM '+table).fetchone()[0])
        for table in ('recognition_execution_claims', 'recognition_execution_audit', 'recognition_execution_seals', 'recognition_operation_receipts'):
            self.assertEqual(0, self.sql('SELECT count(*) FROM '+table, target=True)[0][0])

    def test_original_private_issuance_and_fresh_inspection_are_inert(self):
        target = self.f.dump(True)
        def protected():
            with a.connect(self.config.control) as control:
                return {table:[tuple(row) for row in control.execute('SELECT * FROM '+table+' ORDER BY 1')]
                    for table in ('recognition_admin_primary','recognition_admin_sessions','recognition_admin_mfa',
                                  'recognition_admin_stepups','recognition_approvals','recognition_approval_history',v.r.AUTH)}
        protected_before = protected()
        self.assertTrue(protected_before['recognition_admin_primary'])
        self.assertTrue(protected_before['recognition_admin_sessions'])
        self.assertTrue(protected_before['recognition_approvals'])
        original = issuer._issue_for_coordinator
        seen = []
        def issue(context, token):
            state = c._state(context)
            self.assertIs(c._coordinators[state.outer.context], state.outer)
            self.assertEqual(1, state.target.execute('PRAGMA query_only').fetchone()[0])
            self.assertTrue(state.control.in_transaction and state.target.in_transaction)
            self.assertEqual(0, len(c._continuations))
            seen.append(context)
            return original(context, token)
        with patch.object(issuer, '_issue_for_coordinator', side_effect=issue), patch.object(issuer,'issue',side_effect=AssertionError('public issuer used')):
            with self.coordinator() as owner:
                outer = c._outer(owner)
                self.assertIsNotNone(outer.continuation)
                before = self.f.dump()
                result = owner.snapshot
                self.assertEqual(before, self.f.dump())
                self.assertFalse(result['execution_authority'])
                self.assertNotIn(self.session, repr(result))
                self.assertNotIn(self.primary, repr(result))
                self.assertNotIn(self.f.confirmation['token'], repr(result))
                self.assertNotIn('seed_ciphertext', repr(result))
                self.assertEqual(digest(load(outer.authority_json)), result['authority_sha256'])
                self.assertEqual(self.scope['reference'], result['authority']['operation_reference']['proposal_reference'])
                self.assertEqual(self.session, outer.session)
                with self.assertRaises(TypeError): result['authority']['runtime_target']['generation'] = 99
                self.assertFalse(writer_boundary.verify_local(owner, self.config.target, {}))
                with self.assertRaises(ValueError): writer_boundary.acquire(owner, self.config.target, {})
                with self.assertRaises(ValueError): production_operations.context_data(owner)
                with self.assertRaises(ValueError): execution._context(owner)
                with self.assertRaises(ValueError): c._state(seen[0])
                self.assert_inert()
                self.assertEqual(protected_before,protected())
        self.assertEqual(target, self.f.dump(True))
        with self.assertRaises(ValueError): _ = owner.snapshot
        self.assertFalse(c._continuations)

    def test_public_and_duplicate_results_cannot_be_adopted(self):
        public = self.f.issue()
        before = self.f.dump()
        with self.assertRaisesRegex(ValueError, 'already_exists'):
            with self.coordinator(): self.fail('adoption')
        for value in (public, public.snapshot, object.__new__(c.CoordinatorAdmissionContext)):
            with self.assertRaises(ValueError): issuer._issue_for_coordinator(value, self.f.confirmation['token'])
        duplicate = self.f.issue()
        self.assertFalse(duplicate['execution_authority'])
        self.assertIsNot(type(duplicate), issuer.IssuedAuthority)
        self.assertEqual(before, self.f.dump())
        self.assertFalse(c._continuations)

    def test_readiness_evidence_is_immutable_and_phase_bound(self):
        assess = local_readiness._assess_coordinator
        evidence = []
        def observed(*args):
            value = assess(*args)
            text = value.canonical_json
            self.assertNotIn('seed_ciphertext',text)
            self.assertNotIn(self.session,text)
            with self.assertRaises(TypeError): pickle.dumps(value)
            evidence.append(value)
            return value
        with patch.object(local_readiness,'_assess_coordinator',side_effect=observed):
            with self.coordinator() as owner:
                self.assertTrue(evidence)
                for value in evidence:
                    with self.assertRaises(ValueError): _ = value.canonical_json
                _ = owner.snapshot
        for value in evidence:
            with self.assertRaises(ValueError): _ = value.canonical_json

    def test_old_readiness_owners_cannot_accept_coordinator_phase(self):
        original = issuer._issue_for_coordinator
        def checked(context, token):
            state = c._state(context)
            for fn in (local_readiness._assess_runtime, local_readiness._assess_authority_consent, local_readiness._assess_authority_issuance):
                with self.subTest(adapter=fn.__name__), self.assertRaises(ValueError): fn(state.view,self.session,self.primary)
            return original(context,token)
        with patch.object(issuer,'_issue_for_coordinator',side_effect=checked):
            with self.coordinator() as owner: self.assertIsNotNone(c._outer(owner).continuation)

    def test_opaque_serialization_forgery_and_restart(self):
        with self.coordinator() as owner:
            for cls in (c.CoordinatorContext, c.CoordinatorAdmissionContext, c._Continuation):
                with self.subTest(cls=cls), self.assertRaises(TypeError): cls()
            for obj in (owner, c._outer(owner).continuation):
                with self.assertRaises(TypeError): pickle.dumps(obj)
                with self.assertRaises(AttributeError): obj.arbitrary = 1
            with self.assertRaises(ValueError): _ = object.__new__(c.CoordinatorContext).snapshot
            child = subprocess.run([sys.executable, '-B', '-c',
                'from src.review.recognition import runtime_execution_coordinator as c\n'
                'try: object.__new__(c.CoordinatorContext).snapshot\n'
                'except ValueError: print("REJECTED")\n'
                'else: raise AssertionError("restored continuation")'], capture_output=True, text=True, timeout=30)
            self.assertEqual(0, child.returncode, child.stderr)
            self.assertEqual('REJECTED', child.stdout.strip())
            self.assert_inert()

    def test_wrong_thread_permanently_poisons_original_owner(self):
        entered = []
        with self.assertRaises(ValueError):
            with self.coordinator() as owner:
                entered.append(True)
                def inspect():
                    with self.assertRaises(ValueError): _ = owner.snapshot
                with ThreadPoolExecutor(max_workers=1) as pool: pool.submit(inspect).result()
                _ = owner.snapshot
        self.assertFalse(c._continuations)
        self.assertTrue(entered)

    def test_wrong_pid_permanently_poisons_original_owner(self):
        entered = []
        with self.assertRaises(ValueError):
            with self.coordinator() as owner:
                entered.append(True)
                with patch.object(os, 'getpid', return_value=-1), self.assertRaises(ValueError): _ = owner.snapshot
                _ = owner.snapshot
        self.assertTrue(entered)

    def test_deadline_inherits_authority_and_is_not_renewable(self):
        entered = []
        with self.assertRaises(ValueError):
            with self.coordinator() as owner:
                entered.append(True)
                outer = c._outer(owner)
                body = load(outer.authority_json)
                expires = a.timestamp(body['expires_at_utc'])
                self.assertLessEqual(expires-a.timestamp(body['issued_at_utc']), 120)
                self.assertEqual(expires, min(deadline for deadline, _ in outer.auth_expiries))
                with patch.object(outer.clock, 'read', return_value=(body['expires_at_utc'], expires)), self.assertRaises(ValueError):
                    _ = owner.snapshot
                _ = owner.snapshot
        self.assertTrue(entered)

    def test_phase_handle_epoch_and_sql_replacement_fail_closed(self):
        before = self.f.dump()
        original = issuer._issue_for_coordinator
        for change in ('control', 'target', 'epoch', 'rollback', 'commit', 'savepoint', 'query_only'):
            reached = []
            def replaced(context, token):
                reached.append(True)
                state = c._state(context)
                if change in ('control', 'target'): setattr(state, change, object())
                elif change == 'epoch': state.target_reservation_epoch += 1
                else:
                    sql = dict(rollback='ROLLBACK', commit='COMMIT', savepoint='SAVEPOINT forged', query_only='PRAGMA query_only=OFF')[change]
                    with self.assertRaises(sqlite3.DatabaseError): state.target.execute(sql)
                return original(context, token)
            with self.subTest(change=change), patch.object(issuer, '_issue_for_coordinator', side_effect=replaced), self.assertRaises(ValueError):
                with self.coordinator(): self.fail('replaced phase')
            self.assertEqual(before, self.f.dump())
            self.assertTrue(reached)

    def test_wrong_expected_scope_and_credentials_never_issue(self):
        for options in ({'approval_sha256':'f'*64}, {'activation_sha256':'f'*64}, {'primary_token':'unknown'},
                        {'reason':'other reason'}, {'reference':dict(self.scope['reference'],operation_sha256='f'*64)}):
            with self.subTest(options=tuple(options)), self.assertRaises(ValueError):
                with self.coordinator(**options): self.fail('wrong scope')
        self.assertEqual(0, self.sql('SELECT count(*) FROM '+storage.AUTHORITIES)[0][0])
        self.assert_inert()

    def test_authentication_denial_preserves_existing_control_reductions(self):
        self.sql('UPDATE recognition_admin_mfa SET epoch=epoch+1')
        target = self.f.dump(True)
        before = self.sql('SELECT count(*) FROM recognition_admin_audit')[0][0]
        with self.assertRaises(a.AdminError):
            with self.coordinator(): self.fail('stale MFA')
        self.assertEqual(1, self.sql('SELECT revoked FROM recognition_admin_sessions WHERE token_hash=?', (a.token_hash(self.session),))[0][0])
        self.assertEqual(0, self.sql('SELECT revoked FROM recognition_admin_primary WHERE token_hash=?', (a.token_hash(self.primary),))[0][0])
        self.assertEqual(before+1, self.sql('SELECT count(*) FROM recognition_admin_audit')[0][0])
        self.assertEqual(target, self.f.dump(True))
        self.assertEqual(0, self.sql('SELECT count(*) FROM '+storage.AUTHORITIES)[0][0])

    def test_wrong_outer_coordinator_cannot_issue(self):
        original = issuer._issue_for_coordinator
        reached = []
        def wrong(context, token):
            reached.append(True)
            state = c._state(context)
            old = state.outer.context
            state.outer.context = object.__new__(c.CoordinatorContext)
            try: return original(context,token)
            finally: state.outer.context = old
        with patch.object(issuer,'_issue_for_coordinator',side_effect=wrong), self.assertRaises(ValueError):
            with self.coordinator(): self.fail('wrong outer')
        self.assertFalse(c._continuations)
        self.assertTrue(reached)
        self.assertEqual(0,self.sql('SELECT count(*) FROM '+storage.AUTHORITIES)[0][0])

    def test_forged_continuation_poisons_and_closes_original(self):
        with self.assertRaises(ValueError):
            with self.coordinator() as owner:
                outer = c._outer(owner)
                original = outer.continuation
                outer.continuation = object.__new__(c._Continuation)
                _ = owner.snapshot
        self.assertNotIn(original,c._continuations)

    def test_lost_owner_access_rejects_at_existing_identity_gate_without_writes(self):
        self.sql("UPDATE community_reviewers SET role='reviewer' WHERE id=1",target=True)
        before, target = self.f.dump(), self.f.dump(True)
        with self.assertRaisesRegex(a.AdminError, 'recognition_owner_required'):
            with self.coordinator(): self.fail('lost owner access')
        self.assertEqual(before,self.f.dump())
        self.assertEqual(target,self.f.dump(True))
        self.assertEqual(0,self.sql('SELECT revoked FROM recognition_admin_primary WHERE token_hash=?',(a.token_hash(self.primary),))[0][0])
        self.assertEqual(0,self.sql('SELECT revoked FROM recognition_admin_sessions WHERE token_hash=?',(a.token_hash(self.session),))[0][0])
        self.assertEqual(0,self.sql('SELECT count(*) FROM '+storage.AUTHORITIES)[0][0])

    def test_revoked_session_between_phases_rejects_and_invalidates(self):
        entered = []
        with self.assertRaises(ValueError):
            with self.coordinator() as owner:
                entered.append(True)
                self.sql('UPDATE recognition_admin_sessions SET revoked=1 WHERE token_hash=?', (a.token_hash(self.session),))
                with self.assertRaises(a.AdminError): _ = owner.snapshot
                _ = owner.snapshot
        self.assertTrue(entered)

    def test_actual_target_metadata_and_physical_identity_mismatch(self):
        observe = a.target_identity.side_effect
        for which in ('control', 'target'):
            for key, value in (('hostname','wrong-host'), ('device',999), ('inode',999), ('database',str(self.config.target.parent/'other.db'))):
                def changed(subject):
                    current = observe(subject)
                    return replace(current, **{key:value}) if current.database == str(getattr(self.config, which)) else current
                with self.subTest(which=which,key=key), patch.object(a,'target_identity',side_effect=changed), self.assertRaises(ValueError):
                    with self.coordinator(): self.fail('physical mismatch')
        for key in ('installation_id','target_id','owner_id'):
            old = self.sql('SELECT '+key+' FROM recognition_local_installation', target=True)[0][0]
            value = old+1 if key == 'owner_id' else str(UUID(int=UUID(old).int ^ 1))
            self.assertNotEqual(old,value)
            self.sql('UPDATE recognition_local_installation SET '+key+'=?', (value,), target=True)
            with self.subTest(key=key), self.assertRaises(ValueError):
                with self.coordinator(): self.fail('metadata mismatch')
            self.sql('UPDATE recognition_local_installation SET '+key+'=?', (old,), target=True)
        self.assertEqual(0, self.sql('SELECT count(*) FROM '+storage.AUTHORITIES)[0][0])

    def test_actual_auth_epoch_change_denies_private_issuance(self):
        self.sql('UPDATE recognition_local_installation SET auth_epoch=auth_epoch+1', target=True)
        with self.assertRaises(ValueError):
            with self.coordinator(): self.fail('auth epoch mismatch')
        self.assertEqual(0, self.sql('SELECT count(*) FROM '+storage.AUTHORITIES)[0][0])

    def test_actual_generation_change_cannot_transfer_profile(self):
        with a.connect(self.config.control, write=True) as control:
            old = control.execute('SELECT * FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()
            body = load(old['body_json'])
            body.update(generation=body['generation']+1, runtime_profile_sha256=None,
                        previous_sha256=old['body_sha256'], at_utc=v._utc_now())
            control.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)', (body['generation'],canonical(body),digest(body)))
            a._audit(control,'test_generation_fenced',1,v._utc_now(),dict(generation=body['generation']))
            control.commit()
        with self.assertRaises(ValueError):
            with self.coordinator(): self.fail('generation transfer')

    def test_fresh_profile_scope_change_during_validation_rejects(self):
        original = c._current
        installation = self.sql('SELECT installation_id FROM recognition_local_installation',target=True)[0][0]
        for field, value in (('profile_sha256','f'*64), ('generation',999), ('installation_id',str(UUID(int=UUID(installation).int ^ 1)))):
            calls = []
            def changed(state):
                scope, binding, activation = original(state)
                calls.append(1)
                if len(calls) > 1:
                    self.assertNotEqual(scope[field],value)
                    scope = dict(scope, **{field:value})
                return scope, binding, activation
            with self.subTest(field=field), patch.object(c,'_current',side_effect=changed), self.assertRaises(ValueError):
                with self.coordinator(): self.fail('stale scope')
            self.assertGreater(len(calls), 1)

    def test_actual_schema_change_rejects(self):
        self.sql('CREATE TABLE coordinator_schema_drift(value)', target=True)
        with self.assertRaises(ValueError):
            with self.coordinator(): self.fail('schema change')

    def test_actual_approval_invalidation_rejects(self):
        with a.connect(self.config.control, write=True) as control:
            approvals._invalidate_all(control,'owner',v._utc_now(),'explicit fixture invalidation'); control.commit()
        with self.assertRaisesRegex(ValueError, 'not_current'):
            with self.coordinator(): self.fail('invalidated approval')

    def test_actual_duplicate_ack_rejects(self):
        with a.connect(self.config.control, write=True) as control:
            old = control.execute("SELECT body_json FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?", (records.ACK_ACTION,)).fetchone()
            ack = load(old[0])
            a._audit(control, records.ACK_ACTION, ack['actor'], v._utc_now(), ack['subject']); control.commit()
        with self.assertRaisesRegex(ValueError, 'ack_missing_or_duplicate'):
            with self.coordinator(): self.fail('duplicate ACK')

    def test_actual_dependency_mutation_rejects(self):
        self.sql("UPDATE stop_review_assignments SET status='assigned' WHERE id=(SELECT MIN(id) FROM stop_review_assignments)", target=True)
        with self.assertRaises(ValueError):
            with self.coordinator(): self.fail('changed dependencies')

    def test_actual_stop_rejects(self):
        with a.connect(self.config.control, write=True) as control:
            old = execution._stop(control)
            body = dict(sequence=old['sequence']+1, active=True, reason='fixture stop', actor='owner',
                        recorded_at_utc=v._utc_now(), previous_sha256=digest(old))
            events._insert(control,'recognition_execution_stops','sequence',(body['sequence'],),body); control.commit()
        with self.assertRaisesRegex(ValueError, 'emergency_stop'):
            with self.coordinator(): self.fail('stopped')

    def test_actual_activation_change_between_phases_invalidates(self):
        entered = []
        with self.assertRaises(ValueError):
            with self.coordinator() as owner:
                entered.append(True)
                with a.connect(self.config.control, write=True) as control:
                    binding,_,_ = v._history(control)
                    local_readiness._append(control,binding,'SUSPENDED',1,'fixture suspend',v._utc_now()); control.commit()
                _ = owner.snapshot
        self.assertTrue(entered)

    def test_protected_key_and_rehearsal_checks_are_not_bypassed(self):
        cipher = admin_auth._cipher
        calls = []
        entered = []
        def protected(config):
            calls.append(1)
            return cipher(config)
        with self.assertRaises(ValueError), patch.object(admin_auth,'_cipher',side_effect=protected):
            with self.coordinator() as owner:
                entered.append(True)
                before = len(calls)
                _ = owner.snapshot
                self.assertGreater(len(calls), before)
                with a.connect(self.config.control, write=True) as control:
                    row = control.execute("SELECT body_json FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')='local_deployment_rehearsal_recorded' ORDER BY sequence DESC LIMIT 1").fetchone()
                    subject = deepcopy(load(row[0])['subject']); subject['target']['restore_generation'] += 1
                    a._audit(control,'local_deployment_rehearsal_recorded','fixture',v._utc_now(),subject); control.commit()
                with self.assertRaisesRegex(ValueError,'readiness_blocked'): _ = owner.snapshot
                self.assertTrue(c._coordinators[owner].poisoned)
        self.assertTrue(entered)

    def test_faults_before_control_commit_rollback_all_mutations(self):
        before = self.f.dump()
        insert, audit, finish = issuer._insert, a._audit, c._finish
        for stage in ('before','consume','authority','genesis','issue','final'):
            def inserted(control, table, row):
                insert(control,table,row)
                if stage == 'authority' and table == storage.AUTHORITIES or stage == 'genesis' and table == storage.LIFECYCLE:
                    raise OSError('fixture fault')
            def audited(control, action, *args):
                result = audit(control,action,*args)
                if stage == 'consume' and action == storage.CONSUME_ACTION or stage == 'issue' and action == storage.ISSUE_ACTION:
                    raise OSError('fixture fault')
                return result
            def finalized(state):
                if stage == 'final': raise OSError('fixture fault')
                return finish(state)
            def persisted(*args): raise OSError('fixture fault')
            with self.subTest(stage=stage), patch.object(issuer,'_insert',side_effect=inserted), patch.object(a,'_audit',side_effect=audited), patch.object(c,'_finish',side_effect=finalized):
                with patch.object(issuer,'_persist',side_effect=persisted if stage == 'before' else issuer._persist), self.assertRaises(OSError):
                    with self.coordinator(): self.fail('fault published')
            self.assertEqual(before, self.f.dump())
            self.assertFalse(c._continuations)

    def test_second_private_invocation_rolls_back_not_duplicate_continuation(self):
        original = issuer._issue_for_coordinator
        before = self.f.dump()
        first_completed = []
        def duplicate(context, token):
            original(context, token)
            first_completed.append(True)
            return original(context, token)
        with patch.object(issuer,'_issue_for_coordinator',side_effect=duplicate), self.assertRaises(ValueError):
            with self.coordinator(): self.fail('duplicate')
        self.assertEqual(before, self.f.dump())
        self.assertTrue(first_completed)

    def test_concurrent_coordinators_single_durable_winner(self):
        def issue():
            try:
                with self.coordinator() as owner: return c._outer(owner).authority_sha256
            except sqlite3.OperationalError as error:
                self.assertIn(error.sqlite_errorcode, (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED))
            except ValueError as error:
                self.assertIn('already_exists', str(error))
            return None
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(lambda _:issue(), range(2)))
        self.assertEqual(1, sum(result is not None for result in results))
        self.assertEqual(1, self.sql('SELECT count(*) FROM '+storage.AUTHORITIES)[0][0])
        self.assertEqual(1, self.sql('SELECT count(*) FROM '+storage.LIFECYCLE)[0][0])
        self.assertFalse(c._continuations)
        self.assert_inert()

    def _commit_fault(self, stage):
        connect = a.sqlite3.connect
        before = self.f.dump()
        control_uri = self.config.control.resolve().as_uri()+'?'
        target_uri = self.config.target.resolve().as_uri()+'?'
        faults = []
        class Fault(sqlite3.Connection):
            def commit(conn):
                if conn.is_control:
                    if stage == 'before':
                        faults.append(stage); raise OSError('fixture commit failure')
                    if stage == 'silent':
                        faults.append(stage); return
                    super().commit()
                    if stage == 'after':
                        faults.append(stage); raise OSError('fixture uncertain commit')
                    return
                raise AssertionError('target COMMIT')
            def rollback(conn):
                super().rollback()
                if stage == 'target_cleanup' and conn.is_target:
                    faults.append(stage); raise OSError('fixture cleanup')
            def close(conn):
                super().close()
                if stage == 'control_cleanup' and conn.is_control:
                    faults.append(stage); raise OSError('fixture cleanup')
        def factory(path, *args, **kwargs):
            kwargs['factory'] = Fault
            conn = connect(path, *args, **kwargs)
            conn.is_control, conn.is_target = str(path).startswith(control_uri), str(path).startswith(target_uri)
            return conn
        count = len(issuer._issued)
        with patch.object(a.sqlite3,'connect',side_effect=factory), self.assertRaises((OSError,ValueError)):
            with self.coordinator(): self.fail('commit fault published')
        self.assertFalse(c._continuations)
        self.assertTrue(faults)
        self.assertEqual(count,len(issuer._issued))
        if stage in ('before','silent'):
            self.assertEqual(before,self.f.dump())
        else:
            self.assertEqual('PRESENT_EXACT',self.f.inspect()['status'])
            with self.assertRaises(ValueError):
                with self.coordinator(): self.fail('adopted uncertain authority')
        self.assert_inert()

    def test_before_and_silent_commit_do_not_publish(self):
        self._commit_fault('before')
        self._commit_fault('silent')

    def test_uncertain_actual_commit_requires_inspection(self):
        self._commit_fault('after')

    def test_target_cleanup_failure_requires_inspection(self):
        self._commit_fault('target_cleanup')

    def test_control_cleanup_failure_requires_inspection(self):
        self._commit_fault('control_cleanup')

    def test_partial_continuation_publication_is_removed_on_failure(self):
        promote = c._promote
        def failed(outer):
            promote(outer)
            self.assertIsNotNone(outer.continuation)
            raise OSError('fixture publication failure')
        with patch.object(c,'_promote',side_effect=failed), self.assertRaises(OSError):
            with self.coordinator(): self.fail('partial publication')
        self.assertFalse(c._continuations)
        self.assertFalse(c._coordinators)
        self.assertEqual('PRESENT_EXACT',self.f.inspect()['status'])

    def test_missing_protected_key_fails_before_issuance(self):
        from pathlib import Path
        read = Path.read_bytes
        calls = []
        def protected(path):
            if path == self.config.key_file:
                calls.append(1)
                raise OSError('fixture key unavailable')
            return read(path)
        with patch.object(Path,'read_bytes',new=protected), self.assertRaises(OSError):
            with self.coordinator(): self.fail('key check bypass')
        self.assertTrue(calls)
        self.assertEqual(0,self.sql('SELECT count(*) FROM '+storage.AUTHORITIES)[0][0])

    def _target_readonly(self, mode):
        for target in (False,True): self.sql('PRAGMA journal_mode='+mode,target=target)
        before = self.f.dump(True)
        connect, finish = a.sqlite3.connect, c._finish
        target_uri = self.config.target.resolve().as_uri()+'?'
        writes, commits, reserved = [], [], []
        class Probe(sqlite3.Connection):
            def execute(conn, sql, *args):
                if conn.is_target and sql.lstrip().split()[0].upper() in ('INSERT','UPDATE','DELETE','REPLACE','CREATE','DROP','ALTER'):
                    writes.append(sql); raise AssertionError('target DML/DDL')
                return super().execute(sql,*args)
            def commit(conn):
                if conn.is_target:
                    commits.append(1); raise AssertionError('target COMMIT')
                return super().commit()
        def factory(path, *args, **kwargs):
            kwargs['factory'] = Probe
            conn = connect(path,*args,**kwargs)
            conn.is_target = str(path).startswith(target_uri)
            return conn
        def held(state):
            self.assertTrue(state.control.in_transaction and state.target.in_transaction)
            self.assertEqual(1,state.target.execute('PRAGMA query_only').fetchone()[0])
            with closing(connect(str(self.config.target),timeout=0)) as competitor:
                with self.assertRaises(sqlite3.OperationalError) as busy: competitor.execute('BEGIN IMMEDIATE')
                self.assertIn(busy.exception.sqlite_errorcode,(sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED))
            reserved.append(1)
            return finish(state)
        with (patch.object(a.sqlite3,'connect',side_effect=factory), patch.object(c,'_finish',side_effect=held),
              patch.object(writer_boundary,'acquire',side_effect=AssertionError('writer acquired')),
              patch.object(permanent,'finalize',side_effect=AssertionError('family executed')),
              patch.object(local_execution,'execute_approved_operation',side_effect=AssertionError('legacy execution')),
              patch.object(execution,'execute_operation',side_effect=AssertionError('execution'))):
            with self.coordinator() as owner:
                _ = owner.snapshot
                with closing(connect(str(self.config.target),timeout=0)) as competitor:
                    competitor.execute('BEGIN IMMEDIATE'); competitor.rollback()
        self.assertGreaterEqual(len(reserved),2)
        self.assertEqual([],writes); self.assertEqual([],commits)
        self.assertEqual(before,self.f.dump(True))
        self.assert_inert()

    def test_query_only_reservation_and_zero_target_effects_delete(self): self._target_readonly('DELETE')

    def test_query_only_reservation_and_zero_target_effects_wal(self): self._target_readonly('WAL')


class CoordinatorProviderFenceTests(unittest.TestCase):
    def test_supplied_owner_callback_and_unregistered_state_never_run(self):
        calls = []
        class SuppliedOwner:
            def check(self, **unused):
                calls.append(True)
                raise AssertionError('supplied callback invoked')
        for outer in (SuppliedOwner(), object.__new__(c._Outer)):
            with self.subTest(kind=type(outer).__name__):
                with self.assertRaises(ValueError):
                    with c._phase(outer, issuance=True): self.fail('supplied owner')
                with self.assertRaises(ValueError): c._promote(outer)
                with self.assertRaises(ValueError): c._continuation_entry(outer)
        self.assertEqual([],calls)
        self.assertFalse(c._coordinators)
        self.assertFalse(c._admission_contexts)
        self.assertFalse(c._continuations)


if __name__ == '__main__':
    unittest.main()
