"""Disposable real coordinator lifecycle; no writer/execution providers."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
import os
import pickle
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4
from types import SimpleNamespace

from src.review.recognition import administration as a, administration_schema, authorization
from src.review.recognition import runtime_execution_coordinator as c
from src.review.recognition import runtime_execution_attempt_schema as attempts
from src.review.recognition import runtime_activation_authority_issuance as issuer
from src.review.recognition import runtime_activation_authority_schema as storage
from src.review.recognition import runtime_validation as v, local_readiness, writer_boundary
from src.review.recognition import execution, local_execution, production_operations, permanent
from src.review.recognition import approvals, events, runtime_proposal_records as records
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import load, utc
from tests import test_recognition_runtime_execution_coordinator as fixtures
from tests import test_recognition_runtime_execution_attempt_schema as schema_fixtures


def _cleanup_fixture_tree(case, seen=None):
    """Unwind even a nested fixture that failed before registering its child."""
    seen = set() if seen is None else seen
    if id(case) in seen:
        return
    seen.add(id(case))
    children = [value for value in vars(case).values() if isinstance(value,unittest.TestCase)]
    case.doCleanups()
    for child in children:
        _cleanup_fixture_tree(child,seen)


class ExecutionAttemptCreationTests(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.RuntimeExecutionCoordinatorTests()
        self.addCleanup(_cleanup_fixture_tree,self.base)
        self.base.setUp()
        self.f, self.config = self.base.f, self.base.config

    def coordinator(self):
        return self.base.coordinator()

    def sql(self, *args, **kwargs):
        return self.base.sql(*args, **kwargs)

    def count(self, table):
        return self.sql('SELECT count(*) FROM '+table)[0][0]

    def protected(self):
        with a.connect(self.config.control) as control:
            return {table:[tuple(row) for row in control.execute('SELECT * FROM '+table+' ORDER BY 1')]
                for table in ('recognition_admin_primary','recognition_admin_sessions','recognition_admin_mfa',
                    'recognition_admin_stepups','recognition_admin_confirmations','recognition_approvals',
                    'recognition_approval_history',v.r.AUTH,'recognition_admin_bindings',storage.AUTHORITIES,storage.LIFECYCLE)}

    def assert_no_downstream(self):
        for table in ('recognition_execution_claims','recognition_execution_audit','recognition_execution_seals',
                      'recognition_operation_receipts'):
            self.assertEqual(0,self.sql('SELECT count(*) FROM '+table,target=True)[0][0])
        self.assertEqual(0,self.count('recognition_runtime_execution_claims'))

    def test_real_creation_exact_authority_graph_protected_state_and_no_downstream(self):
        before_target = self.f.dump(True)
        before_schema = self.sql('SELECT name,sql FROM sqlite_master ORDER BY name')
        with self.coordinator() as owner:
            protected = self.protected()
            for table in ('recognition_admin_primary','recognition_admin_sessions','recognition_admin_mfa',
                          'recognition_admin_confirmations','recognition_approvals','recognition_approval_history',v.r.AUTH):
                self.assertTrue(protected[table],table)
            outer = c._outer(owner)
            authority_json, authority_sha = outer.authority_json, outer.authority_sha256
            head = self.sql('SELECT max(sequence) FROM recognition_admin_audit')[0][0]
            with (patch.object(issuer,'issue',side_effect=AssertionError('public issuance')),
                  patch.object(issuer,'_issue_for_coordinator',side_effect=AssertionError('fresh issuance')),
                  patch.object(writer_boundary,'acquire',side_effect=AssertionError('writer')),
                  patch.object(execution,'execute_operation',side_effect=AssertionError('execution')),
                  patch.object(local_execution,'execute_approved_operation',side_effect=AssertionError('execution')),
                  patch.object(permanent,'finalize',side_effect=AssertionError('mutation'))):
                result = owner.create_attempt()
                value = result.snapshot
                self.assertEqual('ATTEMPT_CREATED',value['state'])
                self.assertFalse(value['execution_authority'])
                self.assertFalse(value['retry_authorized'])
                self.assertEqual(authority_sha,value['attempt']['authority_sha256'])
                self.assertEqual(load(authority_json)['authority_id'],value['attempt']['authority_id'])
                self.assertEqual(load(authority_json)['expires_at_utc'],value['attempt']['expires_at_utc'])
                self.assertEqual(protected,self.protected())
                self.assertEqual(1,self.count(attempts.ATTEMPTS))
                self.assertEqual(1,self.count(attempts.HISTORY))
                self.assertEqual(head+1,self.sql('SELECT max(sequence) FROM recognition_admin_audit')[0][0])
                for item in (owner,result,value):
                    self.assertFalse(writer_boundary.verify_local(item,self.config.target,{}))
                    with self.assertRaises(ValueError): execution._context(item)
                    with self.assertRaises(ValueError): production_operations.context_data(item)
                for secret in (self.f.session,self.f.primary,self.f.confirmation['token']):
                    self.assertNotIn(secret,repr(value))
            with a.connect(self.config.control) as conn:
                administration_schema.check_control(conn)
                body = attempts.parse_attempt(canonical(dict(value['attempt'])),attempt_sha256=value['attempt_sha256'])
                authority = attempts.validate_binding(conn,body)
                self.assertEqual(load(authority_json),authority)
            with self.assertRaises(TypeError): value['attempt']['attempt_id'] = str(uuid4())
            self.assert_no_downstream()
        with self.assertRaises(ValueError): _ = result.snapshot
        self.assertFalse(c._attempt_results)
        self.assertEqual(before_target,self.f.dump(True))
        self.assertEqual(before_schema,self.sql('SELECT name,sql FROM sqlite_master ORDER BY name'))

    def test_same_continuation_cannot_create_twice_or_adopt(self):
        with self.assertRaisesRegex(ValueError,'already_spent'):
            with self.coordinator() as owner:
                result = owner.create_attempt()
                body = result.snapshot['attempt']
                before = self.f.dump()
                owner.create_attempt()
        self.assertEqual(before,self.f.dump())
        self.assertEqual('VALID',attempts.inspect_attempt(self.config.control,attempt_id=body['attempt_id'])['status'])
        with self.assertRaises(ValueError): _ = result.snapshot
        with self.assertRaises(ValueError):
            with self.coordinator(): self.fail('adopted existing authority')
        self.assertEqual(1,self.count(attempts.ATTEMPTS))

    def test_forgery_serialization_restart_and_public_authority_denied(self):
        public = self.f.issue()
        for value in (public,public.snapshot,object.__new__(c.CoordinatorContext),{'authority_id':str(uuid4())}):
            with self.subTest(value=type(value)), self.assertRaises(ValueError): c._create_attempt(value)
        with self.assertRaises(TypeError): c.CreatedAttempt()
        with self.assertRaises(ValueError): _ = object.__new__(c.CreatedAttempt).snapshot
        self.assertEqual(0,self.count(attempts.ATTEMPTS))

    def test_result_is_original_owner_local_nonserializable_and_unusable_after_restart(self):
        with self.coordinator() as owner:
            result = owner.create_attempt()
            with self.assertRaises(TypeError): pickle.dumps(result)
            with self.assertRaises(AttributeError): result.replacement = 1
            child = subprocess.run([sys.executable,'-B','-c',
                'from src.review.recognition import runtime_execution_coordinator as c\n'
                'try: object.__new__(c.CreatedAttempt).snapshot\n'
                'except ValueError: print("REJECTED")\n'
                'else: raise AssertionError("adopted")'],capture_output=True,text=True,timeout=30)
            self.assertEqual(0,child.returncode,child.stderr)
            self.assertEqual('REJECTED',child.stdout.strip())
        self.assertEqual(1,self.count(attempts.ATTEMPTS))

    def _existing_attempt(self,same_id):
        with self.assertRaises(ValueError):
            with self.coordinator() as owner:
                authority = load(c._outer(owner).authority_json)
                body = dict(format=attempts.FORMAT,attempt_id=str(uuid4()),authority_id=authority['authority_id'],
                    authority_sha256=digest(authority),created_at_utc=v._utc_now(),expires_at_utc=authority['expires_at_utc'])
                codec = schema_fixtures.ExecutionAttemptSchemaTests()
                codec.authority,codec.f = authority,SimpleNamespace(insert=issuer._insert)
                with a.connect(self.config.control,write=True) as conn:
                    conn.execute('BEGIN IMMEDIATE'); codec.graph(conn,body); conn.commit()
                before = self.f.dump()
                proposed_id = body['attempt_id'] if same_id else str(uuid4())
                with patch.object(c,'uuid4',return_value=proposed_id),self.assertRaisesRegex(ValueError,'incomplete_attempt'):
                    owner.create_attempt()
                self.assertEqual(before,self.f.dump())
                self.assertEqual(1,self.count(attempts.ATTEMPTS))
                owner.create_attempt()

    def test_identical_existing_attempt_is_inspection_only_never_adopted(self): self._existing_attempt(True)
    def test_same_authority_different_attempt_is_rejected(self): self._existing_attempt(False)

    def rejected_change(self, change):
        reached = []
        with self.assertRaises(ValueError):
            with self.coordinator() as owner:
                reached.append(True)
                change(owner)
                owner.create_attempt()
        self.assertTrue(reached)
        self.assertEqual(0,self.count(attempts.ATTEMPTS))
        self.assertEqual(0,self.count(attempts.HISTORY))
        self.assertFalse(c._attempt_results)
        self.assert_no_downstream()

    def test_expired_authority_cannot_extend_original_deadline(self):
        def expired(owner):
            outer = c._outer(owner)
            body = load(outer.authority_json)
            deadline = a.timestamp(body['expires_at_utc'])
            self.assertIn(deadline,[item[0] for item in outer.auth_expiries])
            clock = patch.object(outer.clock,'read',return_value=(body['expires_at_utc'],deadline))
            clock.start(); self.addCleanup(clock.stop)
        self.rejected_change(expired)

    def test_stale_lifetime_and_unregistered_continuation_rejected(self):
        with self.coordinator() as owner: pass
        with self.assertRaises(ValueError): owner.create_attempt()
        self.assertEqual(0,self.count(attempts.ATTEMPTS))

    def test_wrong_thread_cannot_spend_original_continuation(self):
        def changed(owner):
            def consume():
                with self.assertRaises(ValueError): owner.create_attempt()
            with ThreadPoolExecutor(max_workers=1) as pool: pool.submit(consume).result()
        self.rejected_change(changed)

    def test_wrong_pid_cannot_spend_original_continuation(self):
        def changed(owner):
            mock = patch.object(os,'getpid',return_value=-1)
            mock.start(); self.addCleanup(mock.stop)
        self.rejected_change(changed)

    def test_actual_activation_change_rejected(self):
        def changed(owner):
            with a.connect(self.config.control,write=True) as conn:
                binding,_,_ = v._history(conn)
                local_readiness._append(conn,binding,'SUSPENDED',1,'fixture suspension',v._utc_now())
                conn.commit()
        self.rejected_change(changed)

    def test_actual_generation_change_does_not_transfer_profile(self):
        def changed(owner):
            with a.connect(self.config.control,write=True) as conn:
                old = conn.execute('SELECT * FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()
                body = load(old['body_json'])
                body.update(generation=body['generation']+1,runtime_profile_sha256=None,
                            previous_sha256=old['body_sha256'],at_utc=v._utc_now())
                conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(body['generation'],canonical(body),digest(body)))
                a._audit(conn,'test_generation_fenced',1,v._utc_now(),dict(generation=body['generation']))
                conn.commit()
        self.rejected_change(changed)

    def test_changed_profile_observation_rejected(self):
        original = c._current
        def changed(owner):
            def observed(state):
                scope,binding,activation = original(state)
                self.assertNotEqual('f'*64,scope['profile_sha256'])
                return dict(scope,profile_sha256='f'*64),binding,activation
            mock = patch.object(c,'_current',side_effect=observed)
            mock.start(); self.addCleanup(mock.stop)
        self.rejected_change(changed)

    def test_actual_installation_change_rejected(self):
        self.rejected_change(lambda owner:self.sql('UPDATE recognition_local_installation SET installation_id=?',
                                                    (str(uuid4()),),target=True))

    def test_actual_owner_access_change_rejected(self):
        self.rejected_change(lambda owner:self.sql("UPDATE community_reviewers SET role='reviewer' WHERE id=1",target=True))

    def test_actual_auth_epoch_change_rejected(self):
        self.rejected_change(lambda owner:self.sql('UPDATE recognition_local_installation SET auth_epoch=auth_epoch+1',target=True))

    def test_actual_mfa_epoch_change_rejected(self):
        self.rejected_change(lambda owner:self.sql('UPDATE recognition_admin_mfa SET epoch=epoch+1'))

    def test_actual_approval_invalidation_rejected(self):
        def changed(owner):
            with a.connect(self.config.control,write=True) as conn:
                approvals._invalidate_all(conn,'owner',v._utc_now(),'fixture invalidation'); conn.commit()
        self.rejected_change(changed)

    def test_actual_ack_conflict_rejected(self):
        def changed(owner):
            with a.connect(self.config.control,write=True) as conn:
                row = conn.execute("SELECT body_json FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",
                                   (records.ACK_ACTION,)).fetchone()
                ack = load(row[0])
                a._audit(conn,records.ACK_ACTION,ack['actor'],v._utc_now(),ack['subject']); conn.commit()
        self.rejected_change(changed)

    def test_actual_proposal_dependency_mutation_rejected(self):
        self.rejected_change(lambda owner:self.sql("UPDATE stop_review_assignments SET status='assigned' "
            'WHERE id=(SELECT MIN(id) FROM stop_review_assignments)',target=True))

    def test_actual_schema_mutation_rejected(self):
        self.rejected_change(lambda owner:self.sql('CREATE TABLE attempt_schema_drift(value)',target=True))

    def test_actual_physical_identity_mismatch_rejected(self):
        observe = a.target_identity.side_effect
        def changed(owner):
            def actual(conn):
                value = observe(conn)
                return replace(value,inode=value.inode+1) if value.database == str(self.config.target) else value
            mock = patch.object(a,'target_identity',side_effect=actual)
            mock.start(); self.addCleanup(mock.stop)
        self.rejected_change(changed)

    def test_actual_readiness_rehearsal_change_rejected(self):
        def changed(owner):
            with a.connect(self.config.control,write=True) as conn:
                row = conn.execute("SELECT body_json FROM recognition_admin_audit WHERE "
                    "json_extract(body_json,'$.action')='local_deployment_rehearsal_recorded' ORDER BY sequence DESC LIMIT 1").fetchone()
                subject = deepcopy(load(row[0])['subject']); subject['target']['restore_generation'] += 1
                a._audit(conn,'local_deployment_rehearsal_recorded','fixture',v._utc_now(),subject); conn.commit()
        self.rejected_change(changed)

    def test_actual_emergency_stop_rejected(self):
        def changed(owner):
            with a.connect(self.config.control,write=True) as conn:
                old = execution._stop(conn)
                body = dict(sequence=old['sequence']+1,active=True,reason='fixture stop',actor='owner',
                            recorded_at_utc=v._utc_now(),previous_sha256=digest(old))
                events._insert(conn,'recognition_execution_stops','sequence',(body['sequence'],),body); conn.commit()
        self.rejected_change(changed)

    def test_transaction_replacement_and_final_scope_change_rollback(self):
        original = c._persist_attempt
        with self.assertRaises(ValueError):
            with self.coordinator() as owner:
                before = self.f.dump()
                def replaced(state):
                    original(state)
                    state.target_reservation_epoch += 1
                with patch.object(c,'_persist_attempt',side_effect=replaced),self.assertRaises(ValueError): owner.create_attempt()
                self.assertEqual(before,self.f.dump())
                self.assertEqual(0,self.count(attempts.ATTEMPTS))
                self.assertTrue(c._coordinators[owner].poisoned)
                c._outer(owner)

    def _mutation_failure(self,stage):
        insert, audit, final = issuer._insert, a._audit, c._final_attempt
        with self.assertRaises(ValueError):
            with self.coordinator() as owner:
                before = self.f.dump()
                def inserted(control,table,row):
                    insert(control,table,row)
                    if table == (attempts.ATTEMPTS if stage == 'attempt' else attempts.HISTORY if stage == 'history' else None):
                        raise OSError('fixture insert failure')
                def audited(control,action,*args):
                    result = audit(control,action,*args)
                    if action == attempts.CREATE_ACTION and stage == 'audit': raise OSError('fixture audit failure')
                    return result
                def finalized(state):
                    final(state)
                    if stage == 'final': raise OSError('fixture final failure')
                with (patch.object(issuer,'_insert',side_effect=inserted),patch.object(a,'_audit',side_effect=audited),
                      patch.object(c,'_final_attempt',side_effect=finalized),self.assertRaises(OSError)):
                    owner.create_attempt()
                self.assertEqual(before,self.f.dump())
                self.assertEqual(0,self.count(attempts.ATTEMPTS))
                owner.create_attempt()

    def test_attempt_insert_failure_rolls_back(self): self._mutation_failure('attempt')
    def test_history_insert_failure_rolls_back(self): self._mutation_failure('history')
    def test_audit_insert_failure_rolls_back(self): self._mutation_failure('audit')
    def test_final_validation_failure_rolls_back(self): self._mutation_failure('final')

    def _commit_fault(self, stage):
        connect = a.sqlite3.connect
        control_uri, target_uri = (path.resolve().as_uri()+'?' for path in (self.config.control,self.config.target))
        faults = []
        class Fault(sqlite3.Connection):
            def commit(conn):
                if conn.is_control:
                    if stage == 'before': faults.append(stage); raise OSError('fixture before commit')
                    if stage == 'silent': faults.append(stage); return
                    super().commit()
                    if stage == 'after': faults.append(stage); raise OSError('fixture uncertain commit')
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
        def factory(path,*args,**kwargs):
            kwargs['factory'] = Fault
            conn = connect(path,*args,**kwargs)
            conn.is_control,conn.is_target = str(path).startswith(control_uri),str(path).startswith(target_uri)
            return conn
        with self.assertRaises(ValueError):
            with self.coordinator() as owner:
                before = self.f.dump()
                with patch.object(a.sqlite3,'connect',side_effect=factory),self.assertRaises((OSError,ValueError)):
                    owner.create_attempt()
                self.assertTrue(faults)
                self.assertFalse(c._attempt_results)
                if stage in ('before','silent'): self.assertEqual(before,self.f.dump())
                else:
                    self.assertEqual(1,self.count(attempts.ATTEMPTS))
                    self.assertEqual(1,self.count(attempts.HISTORY))
                    with a.connect(self.config.control) as conn: administration_schema.check_control(conn)
                owner.create_attempt()  # Never automatic retry/adoption.
        self.assert_no_downstream()

    def test_commit_failure_before_effect_rolls_back(self): self._commit_fault('before')
    def test_silent_unconfirmed_commit_rolls_back(self): self._commit_fault('silent')
    def test_uncertain_actual_commit_publishes_nothing(self): self._commit_fault('after')
    def test_target_cleanup_failure_publishes_nothing(self): self._commit_fault('target_cleanup')
    def test_control_cleanup_failure_publishes_nothing(self): self._commit_fault('control_cleanup')

    def test_partial_publication_failure_clears_result_and_requires_inspection(self):
        publish = c._publish_attempt
        def failed(outer,state):
            publish(outer,state)
            raise OSError('fixture result publication failure')
        with self.assertRaises(ValueError):
            with self.coordinator() as owner:
                with patch.object(c,'_publish_attempt',side_effect=failed),self.assertRaises(OSError): owner.create_attempt()
                self.assertFalse(c._attempt_results)
                self.assertEqual(1,self.count(attempts.ATTEMPTS))
                owner.create_attempt()

    def test_concurrent_coordinators_single_durable_attempt(self):
        def create():
            try:
                with self.coordinator() as owner: return owner.create_attempt().snapshot['attempt']['attempt_id']
            except sqlite3.OperationalError as error:
                self.assertIn(error.sqlite_errorcode,(sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED))
            except ValueError as error:
                self.assertTrue(any(code in str(error) for code in ('already_exists','incomplete_attempt')))
            return None
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(lambda _:create(),range(2)))
        self.assertEqual(1,sum(result is not None for result in results))
        self.assertEqual(1,self.count(attempts.ATTEMPTS)); self.assertEqual(1,self.count(attempts.HISTORY))
        self.assertEqual(1,self.count(storage.AUTHORITIES))
        with a.connect(self.config.control) as conn: administration_schema.check_control(conn)
        self.assert_no_downstream()

    def _readonly(self, mode):
        for target in (False,True): self.sql('PRAGMA journal_mode='+mode,target=target)
        before = self.f.dump(True)
        connect, finish = a.sqlite3.connect,c._finish
        target_uri = self.config.target.resolve().as_uri()+'?'
        writes, commits, reserved = [],[],[]
        class Probe(sqlite3.Connection):
            def execute(conn,sql,*args):
                if conn.is_target and sql.lstrip().split()[0].upper() in ('INSERT','UPDATE','DELETE','REPLACE','CREATE','DROP','ALTER'):
                    writes.append(sql); raise AssertionError('target mutation')
                return super().execute(sql,*args)
            def commit(conn):
                if conn.is_target: commits.append(1); raise AssertionError('target COMMIT')
                return super().commit()
        def factory(path,*args,**kwargs):
            kwargs['factory'] = Probe
            conn = connect(path,*args,**kwargs); conn.is_target = str(path).startswith(target_uri)
            return conn
        def held(state):
            if state.attempt_pending is not None:
                self.assertTrue(state.control.in_transaction and state.target.in_transaction)
                self.assertEqual(1,state.target.execute('PRAGMA query_only').fetchone()[0])
                with closing(connect(str(self.config.target),timeout=0)) as other:
                    with self.assertRaises(sqlite3.OperationalError) as busy: other.execute('BEGIN IMMEDIATE')
                    self.assertIn(busy.exception.sqlite_errorcode,(sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED))
                reserved.append(1)
            return finish(state)
        with (patch.object(a.sqlite3,'connect',side_effect=factory),patch.object(c,'_finish',side_effect=held),
              patch.object(writer_boundary,'acquire',side_effect=AssertionError('writer')),
              patch.object(execution,'execute_operation',side_effect=AssertionError('execution'))):
            with self.coordinator() as owner:
                result = owner.create_attempt()
                self.assertEqual('ATTEMPT_CREATED',result.snapshot['state'])
                with closing(connect(str(self.config.target),timeout=0)) as other:
                    other.execute('BEGIN IMMEDIATE'); other.rollback()
        self.assertEqual([1],reserved); self.assertEqual([],writes); self.assertEqual([],commits)
        self.assertEqual(before,self.f.dump(True)); self.assert_no_downstream()

    def test_target_query_only_reserved_until_control_commit_delete(self): self._readonly('DELETE')
    def test_target_query_only_reserved_until_control_commit_wal(self): self._readonly('WAL')


class AttemptCreationProviderFenceTests(unittest.TestCase):
    def test_nested_setup_failure_does_not_leak_fixture_patches(self):
        root,child = unittest.TestCase(),unittest.TestCase()
        root.fixture = child  # Parent has not yet registered child.doCleanups.
        value = SimpleNamespace(observation='original')
        changed = patch.object(value,'observation','changed')
        changed.start(); child.addCleanup(changed.stop)
        self.addCleanup(changed.stop)
        self.assertEqual('changed',value.observation)
        _cleanup_fixture_tree(root)
        _cleanup_fixture_tree(root)  # Normal successful cleanups remain idempotent.
        self.assertEqual('original',value.observation)

    def test_incoming_state_cannot_supply_validation_or_persistence_callbacks(self):
        class Supplied:
            def __getattr__(self,name):
                raise AssertionError('incoming callback invoked: '+name)
        for value in (Supplied(),object()):
            for fn in (c._persist_attempt,c._check_attempt_graph,c._final_attempt):
                with self.subTest(fn=fn.__name__),self.assertRaises(ValueError): fn(value)
        with self.assertRaises(ValueError): c._create_attempt(Supplied())


if __name__ == '__main__':
    unittest.main()
