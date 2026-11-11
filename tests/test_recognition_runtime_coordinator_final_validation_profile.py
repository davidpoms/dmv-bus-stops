"""Z4 diagnostic only: real G+2 coordinator, no metadata entry or authority reuse."""

from collections import Counter
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from datetime import timedelta
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from tests import test_recognition_runtime_target_entry_owner as z
from src.review.recognition import administration_schema as control_schema, admin_auth
from src.review.recognition import runtime_profile_schema as profile_schema
from src.review.recognition import runtime_execution_claim_schema as claim_schema
from src.review.recognition import runtime_execution_attempt_schema as attempt_schema
from src.review.recognition import runtime_activation_authority_schema as authority_schema
from src.review.recognition import runtime_approval_contract as approval, runtime_proposal_records as records
from src.review.recognition import runtime_scope_validation as scope, local_readiness as readiness
from src.review.recognition import runtime_operation_contract as contract, dependencies
from src.review.recognition import runtime_execution_coordinator as coordinator
from src.review.recognition import runtime_activation_authority_issuance as issuer
from src.review.recognition.rules import canonical,digest
from src.review.recognition.trust import utc


class _ProfileStop(BaseException):
    pass


class _Profile:
    """Test-only nested accounting. Never returns a security observation."""
    def __init__(self):
        self.start=time.perf_counter();self.stage='G+2 fixture setup';self.stack=[]
        self.stages={};self.boundaries=[];self.previous=None
        self.finishing=0;self.persisting=0;self.subject=0
        self.cutoff=None;self.expires=None;self.lifetime=None
        self.stopped=False;self.stop_stack=[];self.done=threading.Event()
        self.output=Path(__file__).resolve().parents[1]/'.tmp'/'recognition-z4-final-profile.json'
        self.output.parent.mkdir(exist_ok=True)
        def watchdog():
            if not self.done.wait(250):
                try:
                    self.output.write_text(json.dumps(dict(status='hard diagnostic bound',stage=self.stage,
                        elapsed_seconds=time.perf_counter()-self.start,
                        active_components=[f['label'] for f in list(self.stack)]))+'\n',encoding='utf-8')
                finally:os._exit(124)
        threading.Thread(target=watchdog,daemon=True).start()

    def check_bound(self):
        if self.stopped:return
        now=time.perf_counter()
        if now-self.start>=240 or (self.cutoff is not None and now>=self.cutoff):
            self.stopped=True
            self.stop_stack=[dict(component=f['label'],elapsed_seconds=now-f['start']) for f in self.stack]
            raise _ProfileStop('diagnostic stopped before authority deadline / at wall-time bound')

    def bucket(self,category,subject=False):
        stage=self.stages.setdefault(self.stage,dict(components={},subject_components={},connection_opens=0))
        entries=stage['subject_components' if subject else 'components']
        return entries.setdefault(category,dict(calls=0,exclusive_seconds=0.0,SELECT=0,PRAGMA=0))

    def trace(self,database,statement):
        words=statement.lstrip().split(None,1)
        if not words:return
        kind=words[0].upper()
        category=self.stack[-1]['category'] if self.stack else 'other'
        entry=self.bucket(category)
        if kind in ('SELECT','PRAGMA'):entry[kind]+=1
        if self.subject and kind in ('SELECT','PRAGMA'):self.bucket(category,True)[kind]+=1
        counters=self.stages[self.stage].setdefault('sql',{})
        key=database+'_'+kind;counters[key]=counters.get(key,0)+1

    def boundary(self,state):
        # Compare privately; never serialize tokens, hashes, paths or scope data.
        key=dict(pid=os.getpid(),thread=threading.current_thread(),
            connections=(state.control,state.target),epochs=(state.control_reservation_epoch,state.target_reservation_epoch),
            phase=state.phase_id,changes=(state.control.total_changes,state.target.total_changes),
            transactions=(state.control.in_transaction,state.target.in_transaction),
            scope=canonical(dict(state.snapshot)),authentication=(state.session,state.primary),
            activation=state.activation_sha256)
        changed=[] if self.previous is None else [name for name in key if key[name]!=self.previous[name]]
        self.boundaries.append(dict(stage=self.stage,changed_since_previous_evaluation=changed,
            elapsed_seconds=time.perf_counter()-self.start))
        self.previous=key

    def wrap(self,fn,label,category):
        def call(*args,**kwargs):
            self.check_bound()
            saved_stage=self.stage;is_finish=label=='coordinator._finish'
            is_persist=label=='coordinator._persist_attempt';is_eval=label=='coordinator._evaluate'
            is_subject=label=='issuer._subject_for_owner'
            if is_finish:
                self.finishing+=1
                self.stage='issuance-final' if args[0].issuance_phase else 'attempt-final'
            if is_persist:self.persisting+=1;self.stage='attempt-insertion'
            if is_eval:
                state=args[0]
                self.stage=('issuance-final' if self.finishing else 'initial-coordinator-admission') if state.issuance_phase else (
                    'attempt-final' if self.finishing else 'attempt-before-insert' if self.persisting else 'attempt-admission')
                self.boundary(state)
            if is_subject:self.subject+=1
            entry=self.bucket(category);entry['calls']+=1
            sub=self.bucket(category,True) if self.subject else None
            if sub is not None:sub['calls']+=1
            frame=dict(label=label,category=category,start=time.perf_counter(),children=0.0)
            self.stack.append(frame)
            try:
                result=fn(*args,**kwargs)
                if label=='issuer._persist':
                    issued=z.a.timestamp(result['issued_at_utc']);expires=z.a.timestamp(result['expires_at_utc'])
                    remaining=expires-z.a.timestamp(z.v._utc_now())
                    self.lifetime=expires-issued;self.expires=time.perf_counter()+remaining
                    self.cutoff=self.expires-5  # Stop only. Never changes a security clock/deadline.
                return result
            finally:
                elapsed=time.perf_counter()-frame['start'];self.stack.pop()
                exclusive=max(0.0,elapsed-frame['children']);entry['exclusive_seconds']+=exclusive
                if sub is not None:sub['exclusive_seconds']+=exclusive
                if self.stack:self.stack[-1]['children']+=elapsed
                if is_subject:self.subject-=1
                if is_finish:self.finishing-=1
                if is_persist:self.persisting-=1
                if is_eval or is_finish or is_persist:self.stage=saved_stage
        return call

    @contextmanager
    def installed(self,config):
        watched=[(coordinator,'_finish','other'),(coordinator,'_evaluate','other'),
            (coordinator,'_persist_attempt','other'),(issuer,'_persist','other'),
            (issuer,'_subject_for_owner','other'),(readiness,'_assess_inventory','readiness inventory'),
            (scope,'_session','authentication'),(scope,'_primary','authentication'),
            (scope,'_mfa','authentication'),(admin_auth,'_session','authentication'),
            (admin_auth,'_primary','authentication'),(admin_auth,'_owner','authentication'),
            (issuer.consent,'_fresh','authentication'),
            (approval,'read_current','approval/proposal/ACK'),(approval,'_historical','approval/proposal/ACK'),
            (records,'_read_pair','approval/proposal/ACK'),(records,'_graph','approval/proposal/ACK'),
            (records,'parse_acknowledgement','approval/proposal/ACK'),
            (records,'match_acknowledgement','approval/proposal/ACK'),
            (profile_schema,'check_rows','runtime profile'),
            (readiness,'require_activated','activation'),(readiness,'_state','activation'),
            (z.v,'_identity_snapshot','identity/physical schema'),
            (z.a,'observe_target','identity/physical schema'),(z.a,'target_identity','identity/physical schema'),
            (control_schema,'check_target','identity/physical schema'),
            (z.v,'_history','history'),(z.a,'_audit_head','history'),
            (z.s,'check_rows','history'),(attempt_schema,'check_rows','history'),
            (authority_schema,'check_rows','history'),
            (claim_schema,'check_rows','claim validation'),(control_schema,'check_control','control validation'),
            (dependencies,'recheck','dependency validation'),(z.execution,'_stop','emergency stop'),
            (z.s,'historical_manifest','manifest/schema'),(claim_schema,'manifest','manifest/schema')]
        for module in (control_schema,profile_schema,claim_schema,attempt_schema,authority_schema,z.s):
            watched.append((module,'definitions','manifest/schema'))
        connect=z.a.connect
        @contextmanager
        def opened(path,**kwargs):
            self.check_bound()
            self.stages.setdefault(self.stage,dict(components={},subject_components={},connection_opens=0))['connection_opens']+=1
            with connect(path,**kwargs) as conn:
                database='target' if Path(path)==config.target else 'control'
                conn.set_trace_callback(lambda statement:self.trace(database,statement))
                try:yield conn
                finally:conn.set_trace_callback(None)
        with ExitStack() as patches:
            for module,name,category in watched:
                label=('coordinator' if module is coordinator else 'issuer' if module is issuer else module.__name__.rsplit('.',1)[-1])+'.'+name
                patches.enter_context(patch.object(module,name,self.wrap(getattr(module,name),label,category)))
            patches.enter_context(patch.object(z.a,'connect',opened))
            self.stage='coordinator reservation setup'
            yield

    def report(self,completed):
        now=time.perf_counter()
        result=dict(status='completed' if completed else 'bounded diagnostic stop',elapsed_seconds=now-self.start,
            authority_lifetime_seconds=self.lifetime,
            estimated_authority_remaining_seconds=None if self.expires is None else self.expires-now,
            boundaries=self.boundaries,stages=self.stages,interrupted_components=self.stop_stack)
        self.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        return result


class CoordinatorFinalValidationProfileTests(unittest.TestCase):
    def prepare_g2(self):
        # Same disposable W/Y and fresh authentication/approval/consent ceremonies
        # as Z. No Z test invocation, metadata call, authority fixture or shortcut.
        f=z.fixtures.EnrollmentTransitionTests();self.addCleanup(z._cleanup_fixture_tree,f)
        f.setUp();f.migrate();config=f.config;self.config=config
        backups=(config.target.parent/'z4-before-target.db',config.target.parent/'z4-before-control.db')
        for source,path in zip((config.target,config.control),backups):
            with z.a.connect(source) as src,sqlite3.connect(path) as dst:src.backup(dst)
        with z.a.connect(config.control) as control:plan=f.plan(control)
        with z.a.connect(config.target) as target:
            plan['target_schema'].update(after_sha256=z.transition._preview(target),added_definitions_sha256=digest(z.storage.definitions()))
        now=[plan['created_at_utc']]
        clock=patch.object(z.v,'_utc_now',side_effect=lambda:now[0]);clock.start();self.addCleanup(clock.stop)
        def advance():now[0]=(utc(now[0])+timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        with patch.object(z.a,'target_identity',side_effect=z.authorization.target_identity):
            z.transition.transition(config,plan=plan,plan_sha256=digest(plan),target_backup=backups[0],control_backup=backups[1])
            with z.a.connect(config.control) as control:
                bound=z.s._binding(control,4)
                old=dict(control.execute(f'SELECT * FROM {z.profiles.PROFILES} WHERE profile_sha256=?',(plan['source_profile_sha256'],)).fetchone())
            challenge=z.runtime_challenges.issue_challenge(config,expected_generation=4,installation_id=bound['installation_id'],
                target_id=bound['target_id'],owner_id=bound['owner_id'],source_binding_sha256=digest(bound),operator='z4-test',reason='fresh runtime review',now=now[0])
            def observed(subject):
                actual=z.authorization.target_identity(subject);prefix='target' if actual.database==str(config.target) else 'control'
                return replace(actual,hostname=old['hostname'],device=int(old[prefix+'_device']),inode=int(old[prefix+'_inode']))
            with patch.object(z.a,'target_identity',side_effect=observed):
                observation=z.runtime_evidence._collect(config.target,config.control,challenge_id=challenge['challenge']['challenge_id'],
                    challenge_sha256=challenge['challenge']['challenge_sha256'],now=now[0])
            review=dict(format=z.enrollment.REVIEW_FORMAT,observations=[observation],selected_observation_sha256=observation['observation_sha256'])
            z.transition.enroll_transition_runtime_profile(config,canonical(review),challenge['nonce'],plan_id=plan['plan_id'],plan_sha256=digest(plan),
                expected_generation=4,installation_id=bound['installation_id'],target_id=bound['target_id'],owner_id=bound['owner_id'],source_binding_sha256=digest(bound),
                challenge_id=challenge['challenge']['challenge_id'],challenge_sha256=challenge['challenge']['challenge_sha256'],approved_review_sha256=digest(review),
                approved_observation_sha256=observation['observation_sha256'],operator='z4-test',reason='reviewed same runtime tuple',
                confirm_private_log_review=True,confirm_enroll_runtime_profile=True)
        advance();primary=z.runtime_auth.record_primary_authentication(config,actor_id=1,reviewer_key='owner-key')
        session=z.runtime_auth.open_admin_session(config,primary,z.totp.independent_code(now[0]));self.session=session
        with z.a.connect(config.target) as target:
            op=z.load(target.execute("SELECT body_json FROM recognition_operation_contracts WHERE json_extract(body_json,'$.format')='recognition-local-operation-v2' LIMIT 1").fetchone()[0])
            source=z.events.get_event(target,op['event_id'])['preparation']['request']
        request=dict(request_id=str(uuid4()),family=source['family'],inputs=z.deepcopy(source['inputs']),evaluation_at_utc=source['evaluation_at_utc'],
            review_reference='fresh G+2 profile diagnostic',parent_operation_id=None)
        pair=z.runtime_proposals.create_proposal(config,session,request,primary_token=primary);reference=pair['reference']
        advance();step=z.approval_ceremony.issue_step_up(config,session,z.totp.independent_code(now[0]),reference,primary_token=primary)
        confirmation=z.approval_ceremony.begin_confirmation(config,session,step['token'],reference,
            canonical(dict(decision='approve',reason='fresh exact operation',confirm=True)),primary_token=primary)
        approved=z.runtime_approvals.issue_approval(config,session,confirmation['token'],canonical(dict(approval_id=str(uuid4()),reference=reference)),primary_token=primary)
        activation=z.activated_fixture.RuntimeActivatedOwnerTests.activate_fixture(self)
        scope_args=dict(primary_token=primary,approval_sha256=approved['approval_sha256'],reference=reference,
            activation_sha256=digest(activation),reason='profile only, no metadata')
        advance();origin=utc(now[0]);anchor=time.monotonic_ns();clock.stop()
        live=patch.object(z.v,'_utc_now',side_effect=lambda:(origin+timedelta(seconds=(time.monotonic_ns()-anchor)//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ'))
        live.start();self.addCleanup(live.stop)
        approval_id=approved['approval']['approval_id']
        step=z.consent.issue_step_up(config,session,z.totp.independent_code(z.v._utc_now()),approval_id,**scope_args)
        confirmation=z.consent.begin_confirmation(config,session,step['token'],approval_id,
            canonical(dict(decision='authorize_runtime_execution',reason=scope_args['reason'],confirm=True)),**scope_args)
        return config,session,confirmation['token'],approval_id,scope_args

    def test_bounded_real_g2_component_profile(self):
        profiler=_Profile();self.addCleanup(profiler.done.set)
        completed=False
        try:
            config,session,confirmation,approval_id,options=self.prepare_g2()
            with profiler.installed(config),patch.object(z.metadata,'create_target_entry',side_effect=AssertionError('metadata entry forbidden')):
                try:
                    with coordinator.coordinator(config,session,confirmation,approval_id,**options) as owner:
                        attempt=owner.create_attempt()
                        self.assertFalse(attempt.snapshot['execution_authority'])
                    completed=True
                except _ProfileStop:pass
        finally:report=profiler.report(completed)
        self.assertTrue(report['stages'],'no coordinator observations captured')
        self.assertTrue(completed or profiler.stopped)
        for data in report['stages'].values():
            for kind in ('INSERT','UPDATE','DELETE','CREATE','COMMIT'):
                self.assertEqual(0,data.get('sql',{}).get('target_'+kind,0))
        self.assertEqual(120,report['authority_lifetime_seconds'])
        print('Z4_PROFILE '+str(profiler.output))
