"""Real disposable consent; synthetic activation ledger, never a producer."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import os
import pickle
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, admin_auth, runtime_validation as v
from src.review.recognition import runtime_authority_consent as consent
from src.review.recognition import runtime_authority_consent_transaction as owner
from src.review.recognition import runtime_activation_authority_schema as storage
from src.review.recognition import runtime_scope_validation as shared, local_readiness, writer_boundary
from src.review.recognition import runtime_approval_contract, runtime_activated_owner, production_operations
from src.review.recognition import approvals, execution, events
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import utc
from tests import test_recognition_runtime_activation_authority_schema as fixtures
from tests import test_recognition_administration as totp


class AuthorityOwnerConsentTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ActivationAuthoritySchemaTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.migrate()
        self.f = self.fixture.f
        self.activation = self.f.activate_fixture()
        self.f.options['activation_sha256'] = digest(self.activation)
        self.config, self.session, self.primary = self.f.config, self.f.session, self.f.primary
        self.approval_id = self.f.approval['approval']['approval_id']
        self.clock = self.f.clock
        self.clock.return_value = (utc(self.clock.return_value)+timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.scope = dict(primary_token=self.primary, approval_sha256=self.f.approval['approval_sha256'],
            reference=self.f.reference, activation_sha256=digest(self.activation), reason='Reviewed authority consent only')
        self.intent = canonical(dict(decision='authorize_runtime_execution', reason=self.scope['reason'], confirm=True))

    def step(self):
        return consent.issue_step_up(self.config, self.session, totp.independent_code(self.clock.return_value), self.approval_id, **self.scope)

    def confirm(self, step):
        return consent.begin_confirmation(self.config, self.session, step['token'], self.approval_id, self.intent, **self.scope)

    def validate(self, confirmation, **changes):
        scope = dict(self.scope); scope.update(changes)
        return consent.validate_consent(self.config, self.session, confirmation['token'], self.approval_id, **scope)

    def sql(self, sql, args=(), *, target=False):
        return self.f.sql(sql, args, target=target)

    def test_real_step_confirmation_live_result_no_authority(self):
        before = self.fixture.dump(self.config.target)
        step = self.step(); confirmation = self.confirm(step)
        self.assertEqual(600, a.timestamp(step['artifact']['expires_at_utc'])-a.timestamp(step['artifact']['issued_at_utc']))
        self.assertEqual(step['artifact']['expires_at_utc'], confirmation['artifact']['expires_at_utc'])
        self.assertEqual(storage.STEP, step['artifact']['format'])
        self.assertEqual(storage.CONFIRMATION, confirmation['artifact']['format'])
        with self.validate(confirmation) as result:
            snapshot = result.snapshot
            self.assertEqual(digest(confirmation['artifact']), snapshot['confirmation_artifact_sha256'])
            self.assertFalse(writer_boundary.verify_local(result, self.config.target, {}))
            with self.assertRaises(ValueError): writer_boundary.acquire(result, self.config.target, {})
            with self.assertRaises(ValueError): production_operations.context_data(result)
            self.assertEqual(snapshot, result.take_binding())
            with self.assertRaises(ValueError): _ = result.snapshot
        with self.assertRaises(ValueError): _ = result.snapshot
        self.assertEqual(before, self.fixture.dump(self.config.target))
        for table in (storage.AUTHORITIES, storage.LIFECYCLE, 'recognition_runtime_execution_claims'):
            self.assertEqual(0, self.sql('SELECT count(*) FROM '+table)[0][0])
        self.assertEqual(0, self.sql('SELECT used FROM recognition_admin_confirmations WHERE token_hash=?',
                                   (a.token_hash(confirmation['token']),))[0][0])

    def test_totp_replay_and_confirmation_replay(self):
        step = self.step()
        with self.assertRaises(a.AdminError): self.step()
        confirmation = self.confirm(step)
        with self.assertRaises(ValueError): self.confirm(step)
        with self.validate(confirmation) as result: self.assertTrue(result.snapshot)
        self.sql('UPDATE recognition_admin_confirmations SET used=1 WHERE token_hash=?', (a.token_hash(confirmation['token']),))
        with self.assertRaises(ValueError):
            with self.validate(confirmation): self.fail('used confirmation accepted')

    def test_expiry_fixed_and_no_renewal(self):
        step = self.step()
        self.clock.return_value = (utc(self.clock.return_value)+timedelta(seconds=60)).strftime('%Y-%m-%dT%H:%M:%SZ')
        confirmation = self.confirm(step)
        self.assertEqual(step['artifact']['expires_at_utc'], confirmation['artifact']['expires_at_utc'])
        self.clock.return_value = confirmation['artifact']['expires_at_utc']
        with self.assertRaises((ValueError, a.AdminError)):
            with self.validate(confirmation): self.fail('expired consent')

    def test_exact_scope_inputs_and_intent(self):
        step = self.step()
        for key, value in (('activation_sha256','a'*64), ('approval_sha256','a'*64), ('reason','other reason')):
            with self.subTest(key=key), self.assertRaises((ValueError,a.AdminError)):
                consent.begin_confirmation(self.config, self.session, step['token'], self.approval_id,
                    self.intent, **dict(self.scope, **{key:value}))
        for value in (dict(decision='approve',reason=self.scope['reason'],confirm=True),
                      dict(decision='authorize_runtime_execution',reason=self.scope['reason'],confirm=1)):
            with self.assertRaises(ValueError):
                consent.begin_confirmation(self.config,self.session,step['token'],self.approval_id,canonical(value),**self.scope)
        self.confirm(step)

    def test_thread_process_serialization_and_lifetime(self):
        confirmation = self.confirm(self.step())
        with self.validate(confirmation) as result:
            errors=[]
            def other():
                try: _ = result.snapshot
                except Exception as error: errors.append(error)
            thread=threading.Thread(target=other); thread.start(); thread.join()
            self.assertEqual(1,len(errors))
            with self.assertRaises(TypeError): pickle.dumps(result)
            with patch.object(os,'getpid',return_value=os.getpid()+1), self.assertRaises(a.AdminError): _=result.snapshot
            with self.assertRaises(TypeError): consent.RuntimeAuthorityConsent()
        self.assertFalse(consent._results)

    def test_confirmation_scope_fields_tampered_in_current_validation(self):
        confirmation = self.confirm(self.step())
        original = consent._subject
        mutations = [('operation_reference','operation_id',str(uuid4())), ('operation_reference','operation_sha256','a'*64),
            ('runtime_target','target_id',str(uuid4())), ('runtime_target','runtime_profile_sha256','a'*64),
            ('runtime_target','generation',4), ('runtime_target','installation_id',str(uuid4())),
            ('runtime_target','owner_id',999), ('runtime_target','auth_epoch',99), ('runtime_target','mfa_epoch',99),
            ('activation','sequence',999)]
        for section,key,value in mutations:
            def changed(state):
                body=original(state); body[section][key]=value; return body
            with self.subTest(field=(section,key)), patch.object(consent,'_subject',side_effect=changed), self.assertRaises(ValueError):
                with self.validate(confirmation): self.fail('scope substituted')

    def test_bad_totp_persists_denial_and_no_step(self):
        with self.assertRaises(a.AdminError):
            consent.issue_step_up(self.config,self.session,'invalid',self.approval_id,**self.scope)
        self.assertEqual(1,self.sql('SELECT failures FROM recognition_admin_attempts')[0][0])
        self.assertFalse(self.sql("SELECT 1 FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",(storage.STEP_ACTION,)))

    def test_auth_denial_revokes_only_existing_records(self):
        self.sql('UPDATE recognition_admin_primary SET expires=? WHERE token_hash=?',
                 (a.timestamp(self.clock.return_value),a.token_hash(self.primary)))
        with self.assertRaises(a.AdminError): self.step()
        self.assertEqual(1,self.sql('SELECT revoked FROM recognition_admin_primary WHERE token_hash=?',(a.token_hash(self.primary),))[0][0])

    def test_confirmation_concurrent_single_winner(self):
        step=self.step()
        def reservations_released():
            # Real independent reservations prove setup/contenders left no locks.
            with a.connect(self.config.control,write=True) as control:
                control.execute('BEGIN IMMEDIATE')
                with a.connect(self.config.target,write=True) as target:
                    target.execute('BEGIN IMMEDIATE')
                    target.execute('PRAGMA query_only=ON')
        reservations_released()
        def attempt():
            try: return self.confirm(step)
            except (ValueError,a.AdminError): return None
            except sqlite3.OperationalError as error:
                # Bounded lock rejection is safe; never retry or hide I/O errors.
                self.assertIn(error.sqlite_errorcode,(sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED))
                return None
        with ThreadPoolExecutor(max_workers=2) as pool: values=list(pool.map(lambda _:attempt(),range(2)))
        self.assertEqual(1,sum(x is not None for x in values))
        self.assertEqual(1,self.sql("SELECT count(*) FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",(storage.CONFIRM_ACTION,))[0][0])
        reservations_released()

    def test_rollback_after_each_mutation(self):
        before=self.fixture.dump(self.config.control)
        with patch.object(consent,'_append',side_effect=RuntimeError('stage fault')), self.assertRaises(RuntimeError): self.step()
        self.assertEqual(before,self.fixture.dump(self.config.control))
        step=self.step(); before=self.fixture.dump(self.config.control)
        original=consent._append
        def after(*args): original(*args); raise RuntimeError('audit fault')
        with patch.object(consent,'_append',side_effect=after), self.assertRaises(RuntimeError):self.confirm(step)
        self.assertEqual(before,self.fixture.dump(self.config.control))

    def test_current_stop_approval_and_readiness_rejection(self):
        confirmation=self.confirm(self.step())
        with patch.object(local_readiness,'_assess_authority_consent',return_value=dict(code_ready=False,rehearsal_evidence_present=True,activation_state='ACTIVATED')):
            with self.assertRaises(ValueError):
                with self.validate(confirmation):self.fail('readiness bypass')
        self.sql("INSERT INTO recognition_execution_blocks VALUES(?,?,?)",(self.f.reference['operation_id'],'{}',digest({})))
        with self.assertRaises((ValueError,sqlite3.Error)):
            with self.validate(confirmation):self.fail('block bypass')

    def test_protected_adapters_do_not_accept_other_owners(self):
        with self.f.validate() as context:
            state=runtime_activated_owner._state(context)
            with self.assertRaises(a.AdminError): local_readiness._assess_authority_consent(state.view,self.session,self.primary)
        with self.assertRaises(a.AdminError): shared._register_consent_view({})

    def test_premature_lifecycle_and_connection_replacement_poison(self):
        confirmation=self.confirm(self.step())
        for method in ('commit','rollback','cursor','execute'):
            with self.subTest(method=method), self.assertRaises(a.AdminError):
                with owner.consent_transaction(self.config,self.session,self.approval_id,**self.scope) as context:
                    try: getattr(context,method)
                    except a.AdminError:pass
        with self.assertRaises(a.AdminError):
            with owner.consent_transaction(self.config,self.session,self.approval_id,**self.scope) as context:
                owner._state(context).control_reservation_epoch += 1
        with self.assertRaises(a.AdminError):
            with owner.consent_transaction(self.config,self.session,self.approval_id,**self.scope) as context:
                owner._state(context).control = object()

    def test_actual_physical_identity_and_target_metadata(self):
        confirmation=self.confirm(self.step())
        observe=a.target_identity.side_effect
        for which in ('control','target'):
            for key,value in (('hostname','other-host'),('device',999),('inode',999),('database',str(self.config.target.parent/'other.db'))):
                def changed(subject):
                    observation=observe(subject)
                    return replace(observation,**{key:value}) if observation.database==str(getattr(self.config,which)) else observation
                with self.subTest(which=which,key=key),patch.object(a,'target_identity',side_effect=changed),self.assertRaises(ValueError):
                    with self.validate(confirmation):self.fail('physical drift')
        for key,value in (('installation_id',str(uuid4())),('target_id',str(uuid4())),('owner_id',999)):
            old=self.sql('SELECT '+key+' FROM recognition_local_installation',target=True)[0][0]
            self.sql('UPDATE recognition_local_installation SET '+key+'=?',(value,),target=True)
            with self.subTest(key=key),self.assertRaises(ValueError):
                with self.validate(confirmation):self.fail('metadata drift')
            self.sql('UPDATE recognition_local_installation SET '+key+'=?',(old,),target=True)

    def test_actual_schema_and_authentication_epoch_changes(self):
        confirmation=self.confirm(self.step())
        self.sql('CREATE TABLE consent_schema_drift(value)',target=True)
        with self.assertRaises(ValueError):
            with self.validate(confirmation):self.fail('schema drift')
        self.sql('DROP TABLE consent_schema_drift',target=True)
        self.sql('UPDATE recognition_local_installation SET auth_epoch=auth_epoch+1',target=True)
        with self.assertRaises((ValueError,a.AdminError)):
            with self.validate(confirmation):self.fail('epoch drift')

    def test_actual_mfa_epoch_revokes_session(self):
        confirmation=self.confirm(self.step())
        self.sql('UPDATE recognition_admin_mfa SET epoch=epoch+1')
        with self.assertRaises(a.AdminError):
            with self.validate(confirmation):self.fail('MFA drift')
        self.assertEqual(1,self.sql('SELECT revoked FROM recognition_admin_sessions WHERE token_hash=?',(a.token_hash(self.session),))[0][0])

    def test_actual_approval_and_dependency_invalidation(self):
        confirmation=self.confirm(self.step())
        self.sql("UPDATE stop_review_assignments SET status='assigned' WHERE id=(SELECT MIN(id) FROM stop_review_assignments)",target=True)
        with self.assertRaises(ValueError):
            with self.validate(confirmation):self.fail('changed dependency')
        with a.connect(self.config.control,write=True) as control:
            approvals._invalidate_all(control,'owner',v._utc_now(),'explicit test invalidation');control.commit()
        with self.assertRaisesRegex(ValueError,'runtime_approval_not_current'):
            with self.validate(confirmation):self.fail('invalidated approval')

    def test_actual_emergency_stop_and_activation_incarnation(self):
        confirmation=self.confirm(self.step())
        with a.connect(self.config.control,write=True) as control:
            previous=execution._stop(control)
            body=dict(sequence=previous['sequence']+1,active=True,reason='test stop',actor='owner',
                      recorded_at_utc=v._utc_now(),previous_sha256=digest(previous))
            events._insert(control,'recognition_execution_stops','sequence',(body['sequence'],),body);control.commit()
        with self.assertRaisesRegex(ValueError,'emergency_stop'):
            with self.validate(confirmation):self.fail('stop bypass')
        with a.connect(self.config.control,write=True) as control:
            binding,_,_=v._history(control)
            local_readiness._append(control,binding,'DEACTIVATED',1,'test deactivation',v._utc_now());control.commit()
        with self.assertRaises(ValueError):
            with self.validate(confirmation):self.fail('activation ended')

    def test_immutable_artifacts_and_plaintext_secret_isolation(self):
        code=totp.independent_code(self.clock.return_value)
        step=self.step();confirmation=self.confirm(step)
        persisted=self.fixture.dump(self.config.control)
        for raw in (step['token'],confirmation['token'],self.primary,self.session):self.assertNotIn(raw,persisted)
        with self.validate(confirmation) as result:
            serialized=repr(result.snapshot)
            for forbidden in ('seed_ciphertext','owner_key_sha256','key_hash','reviewer_key',self.primary,self.session,step['token'],confirmation['token']):
                self.assertNotIn(forbidden,serialized)
        with self.assertRaises(sqlite3.IntegrityError):self.sql('UPDATE recognition_admin_audit SET body_json=body_json')

    def test_target_readonly_delete_wal_and_control_commit_keeps_reservation(self):
        confirmation=self.confirm(self.step())
        original=a.sqlite3.connect;target_commits=[];commits=[]
        class Probe(sqlite3.Connection):
            def commit(conn):
                path=conn.execute('PRAGMA database_list').fetchone()[2]
                if path==str(self.config.control):
                    with closing(original(self.config.target,timeout=0)) as competitor:
                        with self.assertRaises(sqlite3.OperationalError):competitor.execute('BEGIN IMMEDIATE')
                    commits.append(path)
                elif path==str(self.config.target):target_commits.append(path)
                return super().commit()
        def connect(*args,**kwargs):kwargs['factory']=Probe;return original(*args,**kwargs)
        for mode in ('DELETE','WAL'):
            self.sql('PRAGMA journal_mode='+mode,target=True)
            before=self.fixture.dump(self.config.target)
            with patch.object(a.sqlite3,'connect',side_effect=connect):
                with self.validate(confirmation) as result:
                    state=owner._state(consent._results[result]['context'])
                    self.assertEqual(1,state.target.execute('PRAGMA query_only').fetchone()[0])
                    self.assertEqual(state.target_changes,state.target.total_changes)
                    self.assertEqual(0,state.target.total_changes)
            self.assertEqual(before,self.fixture.dump(self.config.target))
        self.assertEqual(2,len(commits));self.assertFalse(target_commits)

    def test_control_commit_faults_and_cleanup_do_not_publish(self):
        step=self.step();original=a.sqlite3.connect
        for stage in ('before','after','silent','cleanup'):
            prior_count=self.sql("SELECT count(*) FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",(storage.CONFIRM_ACTION,))[0][0]
            class Fault(sqlite3.Connection):
                def commit(conn):
                    if conn.execute('PRAGMA database_list').fetchone()[2]==str(self.config.control):
                        if stage=='before':raise OSError('before commit')
                        if stage=='silent':return None
                        super(Fault,conn).commit()
                        if stage=='after':raise OSError('after commit')
                        return None
                    return super(Fault,conn).commit()
                def rollback(conn):
                    path=conn.execute('PRAGMA database_list').fetchone()[2]
                    super(Fault,conn).rollback()
                    if stage=='cleanup' and path==str(self.config.target):raise OSError('cleanup')
            def connect(*args,**kwargs):kwargs['factory']=Fault;return original(*args,**kwargs)
            # Before/silent are rollback-safe. After/cleanup may have committed;
            # inspect only, never reuse that step to manufacture another token.
            with self.subTest(stage=stage),patch.object(a.sqlite3,'connect',side_effect=connect),self.assertRaises((OSError,a.AdminError)):
                self.confirm(step)
            count=self.sql("SELECT count(*) FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",(storage.CONFIRM_ACTION,))[0][0]
            if stage in ('before','silent'):self.assertEqual(prior_count,count)
            else:
                self.assertEqual(prior_count+1,count)
                if stage=='after':
                    self.clock.return_value=(utc(self.clock.return_value)+timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
                    step=self.step()

    def test_existing_protected_records_and_schema_preserved(self):
        def rows(table):return [tuple(row) for row in self.sql('SELECT * FROM '+table+' ORDER BY 1')]
        tables=('recognition_admin_primary','recognition_admin_sessions','recognition_admin_stepups',
                'recognition_runtime_auth_bindings','recognition_runtime_profiles','recognition_admin_bindings',
                'recognition_approvals','recognition_approval_history','recognition_runtime_execution_claims',
                'recognition_runtime_execution_claim_history','recognition_local_activation')
        before={table:rows(table) for table in tables}
        self.assertTrue(before['recognition_admin_primary']);self.assertTrue(before['recognition_admin_sessions'])
        self.assertTrue(before['recognition_approvals']);self.assertTrue(before['recognition_approval_history'])
        old_confirmations=rows('recognition_admin_confirmations')
        schema=self.sql("SELECT name,sql FROM sqlite_master ORDER BY name")
        step=self.step();confirmation=self.confirm(step)
        with self.validate(confirmation) as result:result.take_binding()
        self.assertEqual(before,{table:rows(table) for table in tables})
        self.assertTrue(all(row in rows('recognition_admin_confirmations') for row in old_confirmations))
        self.assertEqual(len(old_confirmations)+1,len(rows('recognition_admin_confirmations')))
        self.assertEqual(schema,self.sql("SELECT name,sql FROM sqlite_master ORDER BY name"))

    def test_live_result_expiry_transaction_swap_and_forbidden_sql(self):
        confirmation=self.confirm(self.step())
        with self.assertRaises((ValueError,a.AdminError)):
            with self.validate(confirmation) as result:
                self.clock.return_value=confirmation['artifact']['expires_at_utc']
                _=result.snapshot

    def test_forbidden_target_and_authority_writes_poison_owner(self):
        for target,sql in ((True,'UPDATE recognition_local_installation SET auth_epoch=auth_epoch'),
                           (False,f'DELETE FROM {storage.AUTHORITIES}'),
                           (True,'CREATE TABLE forbidden_consent_table(value)')):
            with self.subTest(target=target,sql=sql),self.assertRaises((ValueError,sqlite3.Error)):
                with owner.consent_transaction(self.config,self.session,self.approval_id,**self.scope) as context:
                    state=owner._state(context)
                    try:(state.target if target else state.control).execute(sql)
                    except sqlite3.Error:pass

    def test_restart_cannot_reconstruct_registry_result(self):
        confirmation=self.confirm(self.step())
        with self.validate(confirmation) as result:
            binding=digest(confirmation['artifact'])
            script='''
import sys
from src.review.recognition.runtime_authority_consent import RuntimeAuthorityConsent
value=object.__new__(RuntimeAuthorityConsent)
try:
    value.snapshot
except ValueError:
    print('restart-rejected')
else:
    raise SystemExit('forged result accepted')
'''
            child=subprocess.run([sys.executable,'-B','-c',script,binding],capture_output=True,text=True,timeout=30)
            self.assertEqual(0,child.returncode,child.stderr)
            self.assertEqual('restart-rejected',child.stdout.strip())
            self.assertTrue(result.snapshot)

    def test_complete_artifact_limit_precedes_durable_write(self):
        # The wrapper's bound must be checked before touching even an audit head.
        with self.assertRaisesRegex(ValueError,'size_limit'):
            consent._append(None,dict(payload='x'*storage.MAX_BYTES),None,storage.STEP_ACTION,2)
        before=self.fixture.dump(self.config.control)
        original=storage._json
        def bounded(value):
            if type(value) is dict and value.get('format')==storage.STEP:
                raise ValueError('runtime_authority_size_limit')
            return original(value)
        with patch.object(storage,'_json',side_effect=bounded),self.assertRaisesRegex(ValueError,'size_limit'):
            self.step()
        self.assertEqual(before,self.fixture.dump(self.config.control))
        self.confirm(self.step())

    def test_final_audit_comparison_rejects_boolean_integer_alias(self):
        original=a._audit
        before=self.fixture.dump(self.config.control)
        def changed(control,action,actor,now,subject=None):
            if action==storage.STEP_ACTION:
                subject=deepcopy(subject)
                subject['actor_id']=True
            return original(control,action,actor,now,subject)
        with patch.object(a,'_audit',side_effect=changed),self.assertRaisesRegex(ValueError,'mutation_integrity'):
            self.step()
        self.assertEqual(before,self.fixture.dump(self.config.control))


