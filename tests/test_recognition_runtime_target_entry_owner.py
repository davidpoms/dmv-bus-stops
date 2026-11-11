"""Disposable finalized G+2 -> fresh auth/approval -> real coordinator metadata."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import pickle
import sqlite3
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, authorization, runtime_validation as v
from src.review.recognition import runtime_target_entry_owner as metadata, runtime_target_entry_storage as storage
from src.review.recognition import runtime_enrollment_transition as transition, runtime_enrollment_transition_schema as s
from src.review.recognition import runtime_enrollment as enrollment, runtime_challenges, runtime_evidence, runtime_profile_schema as profiles
from src.review.recognition import runtime_auth, runtime_proposals, runtime_approvals, runtime_approval_ceremony as approval_ceremony
from src.review.recognition import runtime_authority_consent as consent, runtime_execution_coordinator as coordinator
from src.review.recognition import runtime_scope_validation as shared, runtime_admission_validation as admission
from src.review.recognition import events, writer_boundary, execution, local_execution, permanent
from src.review.recognition.rules import canonical,digest
from src.review.recognition.trust import load,utc
from tests import test_recognition_runtime_enrollment_transition as fixtures
from tests import test_recognition_runtime_activated_owner as activated_fixture
from tests import test_recognition_administration as totp
from tests.test_recognition_runtime_execution_attempt_creation import _cleanup_fixture_tree
from tests.recognition_z_timing import bounded_diagnostic,phase


class TargetEntryOwnerTests(unittest.TestCase):
    @bounded_diagnostic
    def test_real_finalized_lifecycle_mode_fences_crashes_and_metadata_only(self):
        phase('disposable fixture setup')
        f=fixtures.EnrollmentTransitionTests();self.addCleanup(_cleanup_fixture_tree,f)
        f.setUp();f.migrate();config=f.config;self.config=config
        root=config.target.parent
        backups=(root/'z-before-target.db',root/'z-before-control.db')
        for source,path in zip((config.target,config.control),backups):
            with a.connect(source) as src,sqlite3.connect(path) as dst:src.backup(dst)
        with a.connect(config.control) as control:plan=f.plan(control)
        with a.connect(config.target) as target:
            plan['target_schema'].update(after_sha256=transition._preview(target),added_definitions_sha256=digest(storage.definitions()))
        now=[plan['created_at_utc']]
        clock=patch.object(v,'_utc_now',side_effect=lambda:now[0]);clock.start();self.addCleanup(clock.stop)
        def advance():now[0]=(utc(now[0])+timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        with patch.object(a,'target_identity',side_effect=authorization.target_identity):
            phase('W schema transition')
            transition.transition(config,plan=plan,plan_sha256=digest(plan),target_backup=backups[0],control_backup=backups[1])
            with a.connect(config.control) as control:
                bound=s._binding(control,4)
                old=dict(control.execute(f'SELECT * FROM {profiles.PROFILES} WHERE profile_sha256=?',(plan['source_profile_sha256'],)).fetchone())
            issued=runtime_challenges.issue_challenge(config,expected_generation=4,installation_id=bound['installation_id'],
                target_id=bound['target_id'],owner_id=bound['owner_id'],source_binding_sha256=digest(bound),operator='z-test',reason='fresh worker review',now=now[0])
            def runtime_identity(subject):
                actual=authorization.target_identity(subject)
                prefix='target' if actual.database==str(config.target) else 'control'
                return replace(actual,hostname=old['hostname'],device=int(old[prefix+'_device']),inode=int(old[prefix+'_inode']))
            with patch.object(a,'target_identity',side_effect=runtime_identity):
                observation=runtime_evidence._collect(config.target,config.control,challenge_id=issued['challenge']['challenge_id'],
                    challenge_sha256=issued['challenge']['challenge_sha256'],now=now[0])
            review=dict(format=enrollment.REVIEW_FORMAT,observations=[observation],selected_observation_sha256=observation['observation_sha256'])
            phase('Y profile finalization')
            transition.enroll_transition_runtime_profile(config,canonical(review),issued['nonce'],plan_id=plan['plan_id'],plan_sha256=digest(plan),
                expected_generation=4,installation_id=bound['installation_id'],target_id=bound['target_id'],owner_id=bound['owner_id'],source_binding_sha256=digest(bound),
                challenge_id=issued['challenge']['challenge_id'],challenge_sha256=issued['challenge']['challenge_sha256'],approved_review_sha256=digest(review),
                approved_observation_sha256=observation['observation_sha256'],operator='z-test',reason='reviewed original runtime physical tuple',
                confirm_private_log_review=True,confirm_enroll_runtime_profile=True)
        # Existing fixture's simulated runtime observers remain active, matching P0/P1.
        phase('fresh G+2 authentication')
        advance();primary=runtime_auth.record_primary_authentication(config,actor_id=1,reviewer_key='owner-key')
        session=runtime_auth.open_admin_session(config,primary,totp.independent_code(now[0]));self.session=session
        with a.connect(config.target) as target:
            op=load(target.execute("SELECT body_json FROM recognition_operation_contracts WHERE json_extract(body_json,'$.format')='recognition-local-operation-v2' LIMIT 1").fetchone()[0])
            source=events.get_event(target,op['event_id'])['preparation']['request']
        request=dict(request_id=str(uuid4()),family=source['family'],inputs=deepcopy(source['inputs']),evaluation_at_utc=source['evaluation_at_utc'],
            review_reference='fresh G+2 metadata test',parent_operation_id=None)
        phase('fresh G+2 proposal')
        pair=runtime_proposals.create_proposal(config,session,request,primary_token=primary)
        reference=pair['reference']
        phase('fresh G+2 approval')
        advance();step=approval_ceremony.issue_step_up(config,session,totp.independent_code(now[0]),reference,primary_token=primary)
        confirmation=approval_ceremony.begin_confirmation(config,session,step['token'],reference,
            canonical(dict(decision='approve',reason='fresh exact operation',confirm=True)),primary_token=primary)
        approved=runtime_approvals.issue_approval(config,session,confirmation['token'],canonical(dict(approval_id=str(uuid4()),reference=reference)),primary_token=primary)
        phase('disposable activation ledger fixture')
        activation=activated_fixture.RuntimeActivatedOwnerTests.activate_fixture(self)  # Existing disposable ledger fixture; real verifier, never production activation.
        scope=dict(primary_token=primary,approval_sha256=approved['approval_sha256'],reference=reference,
            activation_sha256=digest(activation),reason='exact metadata only')
        approval_id=approved['approval']['approval_id']
        advance()
        origin=utc(now[0]);anchor=time.monotonic_ns()
        clock.stop()
        live_clock=patch.object(v,'_utc_now',side_effect=lambda:(origin+timedelta(seconds=(time.monotonic_ns()-anchor)//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ'))
        live_clock.start();self.addCleanup(live_clock.stop)
        phase('fresh authority consent')
        step=consent.issue_step_up(config,session,totp.independent_code(v._utc_now()),approval_id,**scope)
        confirmation=consent.begin_confirmation(config,session,step['token'],approval_id,
            canonical(dict(decision='authorize_runtime_execution',reason=scope['reason'],confirm=True)),**scope)
        baseline=(root/'z-ready-target.db',root/'z-ready-control.db')
        for source,path in zip((config.target,config.control),baseline):
            with a.connect(source) as src,sqlite3.connect(path) as dst:src.backup(dst)
        def restore():
            for srcpath,path in zip(baseline,(config.target,config.control)):
                with sqlite3.connect(srcpath) as src,sqlite3.connect(path) as dst:src.backup(dst)
        def own():
            phase('coordinator issuance')
            return coordinator.coordinator(config,session,confirmation['token'],approval_id,**scope)
        def count():
            with a.connect(config.target) as target:return target.execute(f'SELECT count(*) FROM {storage.TABLE}').fetchone()[0]
        # A nonce, dictionary, durable body or fabricated opaque shell is not provenance.
        for forged in ({},object(),object.__new__(coordinator.CreatedAttempt)):
            with self.subTest(forgery=type(forged).__name__),self.assertRaises(ValueError):metadata.create_target_entry(forged)
        for cls in (metadata.MetadataContext,metadata.TargetEntry):
            with self.assertRaises(TypeError):cls()

        original_mode,original_commit,original_reacquire=metadata._mode,metadata._commit_target,metadata._reacquire
        for point,committed in (('before_mode',False),('after_mode',False),('before_commit',False),('after_commit',True),('reacquire',True)):
            restore()
            def mode(state,query_only):
                if not query_only and point=='before_mode':raise OSError('before mode')
                original_mode(state,query_only)
                if not query_only and point=='after_mode':raise OSError('after mode')
            def commit(state):
                if point=='before_commit':raise OSError('before commit')
                original_commit(state)
                if point=='after_commit':raise OSError('uncertain target commit')
            def reacquire(state,target):
                if point=='reacquire':raise OSError('reservation reacquisition failure')
                original_reacquire(state,target)
            # Unexpected coordinator/creation failures must escape immediately.
            # subTest previously suppressed them, then referenced an uncreated
            # attempt and masked the real failure (or continued expensive cases).
            with self.assertRaises(OSError):
                with own() as owner:
                    phase('create_attempt: '+point)
                    attempt=owner.create_attempt()
                    phase('metadata owner: '+point)
                    with patch.object(metadata,'_mode',side_effect=mode),patch.object(metadata,'_commit_target',side_effect=commit),patch.object(metadata,'_reacquire',side_effect=reacquire):
                        metadata.create_target_entry(attempt)
            self.assertEqual(1 if committed else 0,count())
            with self.assertRaises(ValueError):metadata.create_target_entry(attempt)  # exited/restarted lifetime cannot adopt

        # Ownership corruption cannot be excused by changing the current epoch.
        evaluate=metadata._evaluate
        for fault in ('epoch','connection','thread','authority','attempt'):
            restore()
            def damaged(state):
                if fault=='epoch':state.target_reservation_epoch+=1
                elif fault=='connection':state.target=state.control
                elif fault=='thread':state.ident+=1
                elif fault=='authority':state.outer.authority_sha256='0'*64
                else:state.source['row']['body_sha256']='0'*64
                return evaluate(state)
            with self.subTest(ownership=fault),self.assertRaises(ValueError):
                with own() as owner:
                    attempt=owner.create_attempt()
                    with patch.object(metadata,'_evaluate',side_effect=damaged):metadata.create_target_entry(attempt)
            self.assertEqual(0,count())

        restore()
        with self.assertRaises(ValueError):
            with own() as owner:
                attempt=owner.create_attempt()
                from src.review.recognition import local_readiness
                with a.connect(config.control,write=True) as control:
                    binding=v._history(control)[0]
                    local_readiness._append(control,binding,'SUSPENDED',1,'disposable activation change',v._utc_now());control.commit()
                metadata.create_target_entry(attempt)
        self.assertEqual(0,count())
        restore()
        with self.assertRaises(ValueError):
            with own() as owner:
                attempt=owner.create_attempt()
                observer=a.target_identity
                with patch.object(a,'target_identity',side_effect=lambda obj:replace(observer(obj),device=observer(obj).device+99)):
                    metadata.create_target_entry(attempt)
        self.assertEqual(0,count())

        restore();seen=[]
        def checked(state):
            # Old opaque views cannot cross a mode/epoch, INSERT or commit boundary.
            for context,view,admission_view in seen:
                if context is not state.context:
                    with self.assertRaises(ValueError):metadata._state(context)
                    with self.assertRaises(ValueError):shared._view_parts(view)
                    with self.assertRaises(ValueError):admission._resolve(admission_view)
            result=evaluate(state)
            seen.append((state.context,state.view,state.admission_view))
            return result
        with own() as owner:
            attempt=owner.create_attempt()
            with a.connect(config.control) as control,a.connect(config.target) as target:
                control_before=transition._data(control);target_before=transition._data(target,exclude=(storage.TABLE,))
            with (patch.object(metadata,'_evaluate',side_effect=checked),
                  patch.object(writer_boundary,'acquire',side_effect=AssertionError('writer capability')),
                  patch.object(execution,'execute_operation',side_effect=AssertionError('execution')),
                  patch.object(local_execution,'execute_approved_operation',side_effect=AssertionError('execution')),
                  patch.object(permanent,'finalize',side_effect=AssertionError('business mutation'))):
                result=metadata.create_target_entry(attempt)
            self.assertEqual(1,count());snapshot=result.snapshot
            self.assertEqual(5,snapshot['entry']['runtime_target']['generation'])
            self.assertFalse(snapshot['execution_authority']);self.assertFalse(snapshot['retry_authorized'])
            with self.assertRaises(TypeError):pickle.dumps(result)
            with self.assertRaises(TypeError):snapshot['entry']['attempt_id']='changed'
            with self.assertRaises(ValueError):metadata.create_target_entry(attempt)
            self.assertFalse(writer_boundary.verify_local(result,config.target,{}))
            with a.connect(config.control) as control,a.connect(config.target) as target:
                storage.check_rows(target,control)
                self.assertEqual(control_before,transition._data(control))
                self.assertEqual(target_before,transition._data(target,exclude=(storage.TABLE,)))
                for table in ('recognition_execution_claims','recognition_execution_seals','recognition_execution_audit','recognition_operation_receipts'):
                    self.assertEqual(0,target.execute('SELECT count(*) FROM '+table).fetchone()[0])
        with self.assertRaises(ValueError):_ = result.snapshot
        for context,view,admission_view in seen:
            with self.assertRaises(ValueError):metadata._state(context)


if __name__=='__main__':unittest.main()
