"""Disposable transition DATA only; no target DDL/enrollment producer or authority."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, administration_schema as base, authorization
from src.review.recognition import runtime_enrollment_transition_schema as s
from src.review.recognition import runtime_validation as runtime, runtime_profile_schema as p
from src.review.recognition import runtime_enrollment as enrollment, local_readiness, admin_auth, approvals
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import utc
from tests import test_recognition_runtime_execution_attempt_schema as fixtures
from tests.test_recognition_runtime_execution_attempt_creation import _cleanup_fixture_tree


class EnrollmentTransitionTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ExecutionAttemptSchemaTests()
        self.addCleanup(lambda: _cleanup_fixture_tree(self.f))
        self.f.setUp(); self.f.migrate(); self.config = self.f.config

    def migrate(self, **changes):
        options = dict(expected_generation=3,operator='transition-test',reason='inert disposable transition storage')
        options.update(changes)
        with patch.object(a,'target_identity',side_effect=authorization.target_identity):
            return s.migrate(self.config,**options)

    def plan(self, conn, **changes):
        binding = s._binding(conn,3)
        head = conn.execute('SELECT * FROM recognition_local_activation ORDER BY sequence DESC LIMIT 1').fetchone()
        latest = a._audit_head(conn); now = s.authority._record(latest)['at_utc']
        with a.connect(self.config.target) as target:
            epoch = target.execute(f'SELECT auth_epoch FROM {base.TARGET_TABLE}').fetchone()[0]
        mfa = conn.execute('SELECT epoch FROM recognition_admin_mfa WHERE actor=?',(binding['owner_id'],)).fetchone()[0]
        value = dict(format=s.FORMAT,plan_id=str(uuid4()),installation_id=binding['installation_id'],target_id=binding['target_id'],
            owner_id=binding['owner_id'],source_generation=3,source_binding_sha256=digest(binding),
            source_profile_sha256=binding['runtime_profile_sha256'],source_auth_epoch=epoch,source_mfa_epoch=mfa,
            target_schema=dict(before_sha256=binding['target']['schema_sha256'],after_sha256='a'*64,added_definitions_sha256='b'*64),
            control_schema_sha256=s.claims.manifest(conn),migration_id=s.PACKAGE,
            activation_head=dict(sequence=head['sequence'],event_sha256=head['body_sha256'],state=s.load(head['body_json'])['state']),
            created_at_utc=now,deadline_at_utc=(utc(now)+timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            operator='transition-test',reason='SYNTHETIC transition graph only')
        value.update(changes); return value

    def insert(self, conn, table, row, replace=False):
        conn.execute(('INSERT OR REPLACE' if replace else 'INSERT')+f" INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",tuple(row.values()))

    def event(self, conn, plan, sequence, evidence=None, **changes):
        prior = conn.execute(f'SELECT * FROM {s.HISTORY} WHERE plan_id=? ORDER BY sequence DESC LIMIT 1',(plan['plan_id'],)).fetchone()
        previous = prior['body_sha256'] if prior else None
        if evidence is None:
            evidence = {k:plan[k] for k in s.EVIDENCE[0]} if sequence == 1 else dict(prepared_event_sha256=previous)
        event = dict(format=s.EVENT_FORMAT,plan_id=plan['plan_id'],plan_sha256=digest(plan),sequence=sequence,state=s.STATES[sequence-1],
            at_utc=plan['created_at_utc'],previous_sha256=previous,actor_id=plan['owner_id'],operator=plan['operator'],reason=plan['reason'],evidence=evidence)
        event.update(changes)
        audit = a._audit_head(conn)['sequence']+1
        row = dict(plan_id=plan['plan_id'],sequence=sequence,state=event['state'],at=a.timestamp(event['at_utc']),previous_sha256=previous,
            body_json=canonical(event),body_sha256=digest(event),audit_sequence=audit,
            destination_generation=evidence.get('generation'),destination_binding_sha256=evidence.get('binding_sha256'),
            destination_profile_sha256=evidence.get('profile_sha256'))
        self.insert(conn,s.HISTORY,row)
        return row,event

    def audit(self, conn, plan, row, event):
        a._audit(conn,s.ACTIONS[event['sequence']-1],event['operator'],event['at_utc'],dict(plan_id=plan['plan_id'],
            plan_sha256=digest(plan),event_sequence=event['sequence'],event_sha256=row['body_sha256']))

    def prepared(self, conn, plan=None):
        a._invalidate(conn)
        now = s.authority._record(a._audit_head(conn))['at_utc']
        approvals._invalidate_all(conn,'transition-test',now,'SYNTHETIC plan preparation')
        plan = self.plan(conn) if plan is None else plan
        row = {k:plan[k] for k in ('plan_id','installation_id','source_generation','source_binding_sha256','source_profile_sha256')}
        row.update(created_at=a.timestamp(plan['created_at_utc']),deadline_at=a.timestamp(plan['deadline_at_utc']),
            body_json=canonical(plan),body_sha256=digest(plan),audit_sequence=a._audit_head(conn)['sequence']+1)
        self.insert(conn,s.PLANS,row)
        h,event = self.event(conn,plan,1); self.audit(conn,plan,h,event)
        return plan

    def prefix(self, conn, plan, sequence):
        if sequence >= 2:
            h,event = self.event(conn,plan,2); self.audit(conn,plan,h,event)
        if sequence >= 3:
            old = s._binding(conn,3); bound = deepcopy(old)
            bound.update(generation=4,previous_sha256=digest(old),at_utc=plan['created_at_utc'],runtime_profile_sha256=None)
            bound['target']['schema_sha256'] = plan['target_schema']['after_sha256']
            previous = conn.execute(f'SELECT body_sha256 FROM {s.HISTORY} WHERE plan_id=? AND sequence=2',(plan['plan_id'],)).fetchone()[0]
            h,event = self.event(conn,plan,3,dict(intent_event_sha256=previous,observed_schema_sha256=plan['target_schema']['after_sha256'],generation=4,binding_sha256=digest(bound)))
            conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(4,canonical(bound),digest(bound)))
            self.audit(conn,plan,h,event)
        return plan

    def test_migration_success_noop_manifest_and_protected_data(self):
        target = self.f.f.dump(self.config.target)
        with a.connect(self.config.control) as conn:
            before = runtime._denial_baseline(conn); old = s.claims.manifest(conn)
        with patch.object(admin_auth,'_cipher',side_effect=AssertionError('key read')):
            self.assertTrue(self.migrate()['installed'])
        snapshot = self.f.f.dump(self.config.control)
        self.assertFalse(self.migrate()['installed']); self.assertEqual(snapshot,self.f.f.dump(self.config.control))
        self.assertEqual(target,self.f.f.dump(self.config.target))
        with a.connect(self.config.control) as conn:
            base.check_control(conn); self.assertEqual(old,s.historical_manifest(conn))
            self.assertEqual(before,runtime._denial_baseline(conn))
            self.assertEqual(0,conn.execute(f'SELECT count(*) FROM {s.PLANS}').fetchone()[0])
            self.assertEqual('NOT_ACTIVATED',s._binding(conn,3)['production_state'])

    def test_codec_strictness_and_expiry(self):
        self.migrate()
        with a.connect(self.config.control) as conn: body = self.plan(conn)
        self.assertEqual(body,s.parse_plan(canonical(body),plan_sha256=s.plan_digest(body)))
        for key in s.BODY_FIELDS:
            bad = deepcopy(body); del bad[key]
            with self.subTest(missing=key),self.assertRaises(ValueError):s.validate_plan(bad)
        for key,value in (('extra',1),('plan_id','bad'),('source_generation',True),('source_generation',1.5),
                          ('owner_id',False),('source_binding_sha256',body['source_binding_sha256']+'\0'),
                          ('plan_id',body['plan_id']+'\0'),('source_generation',2**63),('created_at_utc','2026-01-01'),
                          ('reason','bad\0reason'),('migration_id','unregistered')):
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):s.validate_plan(dict(body,**{key:value}))
        for raw in (canonical(body)+' ',canonical(body)[:-1]+',"plan_id":"'+body['plan_id']+'"}'):
            with self.assertRaises(ValueError):s.parse_plan(raw,plan_sha256=digest(body))
        with self.assertRaisesRegex(ValueError,'expired'):s.validate_expiry(body,now=body['deadline_at_utc'])

    def test_partial_install_and_migration_rollback(self):
        before = self.f.f.dump(self.config.control)
        original = a._audit
        def fail(conn, action, *args, **kwargs):
            if action == s.ACTION: raise RuntimeError('synthetic audit fault')
            return original(conn,action,*args,**kwargs)
        with patch.object(a,'_audit',side_effect=fail),self.assertRaises(RuntimeError):self.migrate()
        self.assertEqual(before,self.f.f.dump(self.config.control))
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE'); conn.execute(s.definitions()[s.PLANS]); conn.commit()
        with self.assertRaises(ValueError):self.migrate()

    def test_wrong_generation_and_scope_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'generation'):self.migrate(expected_generation=2)
        self.migrate()
        for change in ({'source_generation':2},{'source_binding_sha256':'0'*64},{'source_profile_sha256':'1'*64},
                       {'installation_id':str(uuid4())},{'target_id':str(uuid4())},{'owner_id':999},
                       {'source_mfa_epoch':999},{'activation_head':dict(sequence=99,event_sha256='a'*64,state='NOT_ACTIVATED')}):
            with self.subTest(change=change),a.connect(self.config.control,write=True) as conn:
                conn.execute('BEGIN IMMEDIATE'); plan = self.plan(conn,**change)
                with self.assertRaises((sqlite3.Error,ValueError)):self.prepared(conn,plan);base.check_control(conn)

    def test_pending_prefixes_expired_fence_and_real_admission_denial(self):
        self.migrate(); target = self.f.f.dump(self.config.target)
        for count in (1,2,3):
            with self.subTest(prefix=count),a.connect(self.config.control,write=True) as conn:
                conn.execute('BEGIN IMMEDIATE'); plan = self.prepared(conn); self.prefix(conn,plan,count); base.check_control(conn)
                with self.assertRaisesRegex(ValueError,'transition_pending'):s.require_no_pending(conn)
                with self.assertRaisesRegex(ValueError,'transition_pending'):runtime._identity_snapshot(self.config,conn,None,plan['created_at_utc'])
                with self.assertRaisesRegex(ValueError,'transition_pending'):local_readiness.require_activated(conn,s._binding(conn,3 if count<3 else 4))
                with self.assertRaisesRegex(ValueError,'transition_pending'):admin_auth._owner(conn,None,s._binding(conn,3),plan['created_at_utc'])
                conn.rollback()
        self.assertEqual(target,self.f.f.dump(self.config.target))

    def test_immutable_replace_and_duplicate_guards(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE'); plan = self.prepared(conn); base.check_control(conn)
            for table in (s.PLANS,s.HISTORY):
                row = dict(conn.execute(f'SELECT * FROM {table}').fetchone())
                for statement in (f'UPDATE {table} SET body_json=body_json',f'DELETE FROM {table}'):
                    with self.subTest(table=table,statement=statement),self.assertRaises(sqlite3.Error):conn.execute(statement)
                with self.assertRaises(sqlite3.Error):self.insert(conn,table,row,replace=True)
            conflict = self.plan(conn)
            with self.assertRaises(sqlite3.Error):self.prepared(conn,conflict)

    def test_missing_genesis_or_audit_cannot_commit(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE'); plan = self.prepared(conn)
            h,event = self.event(conn,plan,2)
            with self.assertRaises(sqlite3.Error):conn.commit()
            conn.rollback()

    def test_concurrent_preparation_single_winner_and_restart_inspection(self):
        self.migrate()
        with a.connect(self.config.control) as conn: plan = self.plan(conn)
        def create(_):
            try:
                with a.connect(self.config.control,write=True) as conn:
                    conn.execute('BEGIN IMMEDIATE'); self.prepared(conn,plan);base.check_control(conn);conn.commit()
                return True
            except (ValueError,sqlite3.Error):return False
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(1,sum(pool.map(create,range(2))))
        observed = s.inspect_transition(self.config.control,plan_id=plan['plan_id'])
        self.assertEqual('PREPARED',observed['status']); self.assertTrue(observed['pending'])
        self.assertFalse(observed['execution_authority']);self.assertFalse(observed['retry_authorized'])
        with a.connect(self.config.control) as conn:base.check_control(conn)

    def test_partial_finalization_and_unlinked_generation_rejected(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE'); plan=self.prepared(conn);self.prefix(conn,plan,3)
            old=s._binding(conn,4); forged=dict(old,generation=5,previous_sha256=digest(old))
            with self.assertRaises(sqlite3.Error):conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(5,canonical(forged),digest(forged)))
            with self.assertRaises(sqlite3.Error):self.event(conn,plan,4,dict(schema_bound_event_sha256='f'*64,generation=5,
                binding_sha256='a'*64,profile_sha256='b'*64,challenge_sha256='c'*64,observation_sha256='d'*64,review_sha256='e'*64))

    def final_graph(self, conn, plan, *, private_review=True):
        """Synthetic control graph only; actual target intentionally remains H0."""
        bound = s._binding(conn,4)
        old = dict(conn.execute(f'SELECT * FROM {p.PROFILES} WHERE profile_sha256=?',(plan['source_profile_sha256'],)).fetchone())
        old_audit = s.load(conn.execute('SELECT body_json FROM recognition_admin_audit WHERE sequence=?',(old['audit_sequence'],)).fetchone()[0])
        review = deepcopy(old_audit['subject']['review']); observed = review['observations'][0]['observation']
        moment = a.timestamp(plan['created_at_utc'])
        challenge = dict(format='recognition-runtime-enrollment-challenge-v1',challenge_id=str(uuid4()),
            installation_id=plan['installation_id'],source_generation=4,source_binding_sha256=digest(bound),target_id=plan['target_id'],
            owner_id=plan['owner_id'],role='runtime',nonce_sha256='c'*64,issued_at=moment,expires_at=moment+600,
            operator=plan['operator'],reason=plan['reason'],audit_sequence=a._audit_head(conn)['sequence']+1)
        challenge['challenge_sha256']=digest(challenge)
        self.insert(conn,p.CHALLENGES,challenge)
        a._audit(conn,'runtime_enrollment_challenge_issued',plan['operator'],plan['created_at_utc'],
                 dict(challenge_sha256=challenge['challenge_sha256'],reason=plan['reason']))
        observed.update(source_generation=4,source_binding_sha256=digest(bound),challenge_id=challenge['challenge_id'],
            challenge_sha256=challenge['challenge_sha256'],nonce_sha256=challenge['nonce_sha256'],challenge_expires_at=moment+600,
            observed_at=moment,target_schema_sha256=plan['target_schema']['after_sha256'])
        review['observations']=[dict(observation=observed,observation_sha256=digest(observed))]
        review['selected_observation_sha256']=digest(observed)
        profile=dict(old,generation=5,challenge_id=challenge['challenge_id'],observation_sha256=digest(observed),
            target_schema_sha256=plan['target_schema']['after_sha256'],observed_at=moment,created_at=moment,
            operator=plan['operator'],reason=plan['reason'],audit_sequence=a._audit_head(conn)['sequence']+1)
        del profile['profile_sha256'];profile['profile_sha256']=digest(profile)
        binding=dict(bound,generation=5,previous_sha256=digest(bound),at_utc=plan['created_at_utc'],runtime_profile_sha256=profile['profile_sha256'])
        previous=conn.execute(f'SELECT body_sha256 FROM {s.HISTORY} WHERE plan_id=? AND sequence=3',(plan['plan_id'],)).fetchone()[0]
        evidence=dict(schema_bound_event_sha256=previous,generation=5,binding_sha256=digest(binding),profile_sha256=profile['profile_sha256'],
            challenge_sha256=challenge['challenge_sha256'],observation_sha256=digest(observed),review_sha256=digest(review))
        # Reserve event's deferred audit reference AFTER the enrollment audit.
        event=dict(format=s.EVENT_FORMAT,plan_id=plan['plan_id'],plan_sha256=digest(plan),sequence=4,state='FINALIZED',
            at_utc=plan['created_at_utc'],previous_sha256=previous,actor_id=plan['owner_id'],operator=plan['operator'],reason=plan['reason'],evidence=evidence)
        h=dict(plan_id=plan['plan_id'],sequence=4,state='FINALIZED',at=moment,previous_sha256=previous,body_json=canonical(event),
            body_sha256=digest(event),audit_sequence=profile['audit_sequence']+1,destination_generation=5,
            destination_binding_sha256=digest(binding),destination_profile_sha256=profile['profile_sha256'])
        self.insert(conn,s.HISTORY,h);self.insert(conn,p.PROFILES,profile)
        conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(5,canonical(binding),digest(binding)))
        a._audit(conn,'runtime_profile_enrolled',plan['operator'],plan['created_at_utc'],dict(reason=plan['reason'],previous_generation=4,generation=5,
            source_binding_sha256=digest(bound),binding_sha256=digest(binding),challenge_sha256=challenge['challenge_sha256'],
            profile_sha256=profile['profile_sha256'],observation_sha256=digest(observed),review_sha256=digest(review),
            private_log_review_confirmed=private_review,enrollment_confirmed=True,review=review))
        self.audit(conn,plan,h,event)
        return profile

    def test_atomic_finalized_graph_old_scope_denied_and_target_unchanged(self):
        self.migrate(); target=self.f.f.dump(self.config.target)
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE');plan=self.prepared(conn);self.prefix(conn,plan,3)
            self.final_graph(conn,plan);base.check_control(conn);s.require_no_pending(conn)
            current,profile,_=runtime._history(conn)
            self.assertEqual(5,current['generation']);self.assertEqual(5,profile['generation'])
            with self.assertRaises(ValueError):
                with a.connect(self.config.target) as observed:
                    runtime._identity_snapshot(self.config,conn,observed,plan['created_at_utc'])
            conn.commit()
        self.assertEqual(target,self.f.f.dump(self.config.target))
        result=s.inspect_transition(self.config.control,plan_id=plan['plan_id'])
        self.assertEqual('FINALIZED',result['status']);self.assertFalse(result['pending']);self.assertFalse(result['execution_authority'])

    def test_legacy_records_and_target_schema_unchanged(self):
        with a.connect(self.config.target) as conn:
            old_schema=a.observe_target(conn); legacy=[tuple(r) for r in conn.execute('SELECT * FROM recognition_execution_claims')]
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE');self.prepared(conn);base.check_control(conn);conn.commit()
        with a.connect(self.config.target) as conn:
            self.assertEqual(old_schema,a.observe_target(conn));self.assertEqual(legacy,[tuple(r) for r in conn.execute('SELECT * FROM recognition_execution_claims')])
            self.assertFalse(conn.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_runtime_execution_entries'").fetchone())

    def test_concurrent_finalization_single_graph(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE');plan=self.prepared(conn);self.prefix(conn,plan,3);conn.commit()
        def finalize(_):
            try:
                with a.connect(self.config.control,write=True) as conn:
                    conn.execute('BEGIN IMMEDIATE');self.final_graph(conn,plan);base.check_control(conn);conn.commit()
                return True
            except (ValueError,sqlite3.Error):return False
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(1,sum(pool.map(finalize,range(2))))
        self.assertEqual('FINALIZED',s.inspect_transition(self.config.control,plan_id=plan['plan_id'])['status'])

    def test_finalization_rollback_and_expired_pending_stays_blocking(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE');plan=self.prepared(conn);self.prefix(conn,plan,3);conn.commit()
        before=self.f.f.dump(self.config.control)
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE');self.final_graph(conn,plan);base.check_control(conn)
            # Simulated failure before manager commit. Context rolls back entire graph.
        self.assertEqual(before,self.f.f.dump(self.config.control))
        with patch.object(runtime,'_utc_now',return_value=plan['deadline_at_utc']):
            observed=s.inspect_transition(self.config.control,plan_id=plan['plan_id'])
        self.assertTrue(observed['expired']);self.assertTrue(observed['pending'])
        with a.connect(self.config.control) as conn:
            with self.assertRaisesRegex(ValueError,'transition_pending'):s.require_no_pending(conn)

    def test_migration_uncertain_commit_requires_inspection_not_retry(self):
        original=sqlite3.connect
        class LostAck(sqlite3.Connection):
            def commit(self):
                super().commit()
                raise sqlite3.OperationalError('synthetic lost commit acknowledgement')
        def connect(database,*args,**kwargs):
            if self.config.control.name in str(database):kwargs['factory']=LostAck
            return original(database,*args,**kwargs)
        with patch.object(sqlite3,'connect',side_effect=connect),self.assertRaises(sqlite3.OperationalError):self.migrate()
        # No in-memory success was returned; independently verify the durable inert extension.
        with a.connect(self.config.control) as conn:
            base.check_control(conn);self.assertTrue(s.present(conn))
            self.assertFalse(conn.execute(f'SELECT 1 FROM {s.PLANS}').fetchone())
            self.assertEqual(3,s._binding(conn,3)['generation'])

    def test_unlinked_null_profile_reset_is_denied_and_scoped_binding_still_works(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE');old=s._binding(conn,3)
            reset=dict(old,generation=4,previous_sha256=digest(old),runtime_profile_sha256=None)
            with self.assertRaisesRegex(sqlite3.Error,'transition_scope_mismatch'):
                conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(4,canonical(reset),digest(reset)))
            with self.assertRaisesRegex(sqlite3.Error,'immutable_transition_binding_digest'):
                conn.execute('INSERT OR REPLACE INTO recognition_admin_bindings VALUES(?,?,?)',(4,canonical(reset),digest(old)))
            self.assertEqual(old,s._binding(conn,3))
            plan=self.prepared(conn);self.prefix(conn,plan,3);base.check_control(conn)
            self.assertIsNone(s._binding(conn,4)['runtime_profile_sha256'])
            with self.assertRaisesRegex(ValueError,'transition_pending'):
                local_readiness.require_activated(conn,s._binding(conn,4))

    def test_changed_mfa_epoch_or_activation_head_cannot_advance(self):
        self.migrate()
        for changed in ('mfa','activation'):
            with self.subTest(changed=changed),a.connect(self.config.control,write=True) as conn:
                conn.execute('BEGIN IMMEDIATE');plan=self.prepared(conn)
                if changed == 'mfa':
                    conn.execute('UPDATE recognition_admin_mfa SET epoch=epoch+1')
                else:
                    local_readiness._append(conn,s._binding(conn,3),'DEACTIVATED',plan['owner_id'],
                                            'synthetic changed head',plan['created_at_utc'])
                h,event=self.event(conn,plan,2)
                with self.assertRaisesRegex(sqlite3.Error,'transition_audit_incomplete'):self.audit(conn,plan,h,event)
                conn.rollback()

    def test_finalization_without_private_review_cannot_commit(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE');plan=self.prepared(conn);self.prefix(conn,plan,3);conn.commit()
        before=self.f.f.dump(self.config.control)
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            with self.assertRaisesRegex(sqlite3.Error,'transition_audit_incomplete'):
                self.final_graph(conn,plan,private_review=False)
        self.assertEqual(before,self.f.f.dump(self.config.control))

    def test_populated_authority_attempt_approval_history_is_preserved_not_promoted(self):
        from src.review.recognition import writer_boundary
        body=self.f.prepare()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE');self.f.graph(conn,body)
            binding=s._binding(conn,3)
            local_readiness._append(conn,binding,'DEACTIVATED',binding['owner_id'],'synthetic nonactive storage install',body['created_at_utc'])
            conn.commit()
        tables=('recognition_runtime_execution_authorities','recognition_runtime_execution_lifecycle',
            'recognition_runtime_execution_attempts','recognition_runtime_execution_attempt_history',
            'recognition_approvals','recognition_approval_history')
        def snapshot():
            with a.connect(self.config.control) as conn:
                return {table:[tuple(row) for row in conn.execute(f'SELECT * FROM {table}')] for table in tables}
        before=snapshot();self.assertTrue(all(before[table] for table in tables))
        self.migrate();self.assertEqual(before,snapshot())
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            with self.assertRaisesRegex(sqlite3.Error,'transition_scope_mismatch'):self.prepared(conn)
        with self.assertRaises(ValueError):writer_boundary.acquire(self.f.authority,self.config.target,{})


if __name__ == '__main__': unittest.main()
