"""One bounded disposable R22 lifecycle, never a production activation path."""
from contextlib import contextmanager, ExitStack
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
import time
import unittest
from uuid import uuid4
from unittest.mock import patch

from tests.runtime_deadline_harness import run_child, MARKER
from tests import recognition_finalization_fixture as isolated
from tests import test_recognition_runtime_coordinator_final_validation_profile as fixture
from tests import test_recognition_runtime_target_entry_owner as z
from src.review.recognition import runtime_finalization as finalization
from src.review.recognition import runtime_finalization_contract as contract
from src.review.recognition import runtime_activation_authority_schema as source
from src.review.recognition import runtime_activation_authority_issuance as issuer
from src.review.recognition.rules import canonical,digest
from src.review.recognition.trust import utc,load
from src.review.recognition import runtime_authority_lifetime_policy as lifetime
from src.review.recognition import runtime_schema_package_lineage as lineage
from src.review.recognition import runtime_authority_consent as consent


class FinalizationLifecycleTests(unittest.TestCase):
    def test_one_disposable_original_lifecycle(self):
        v2=os.environ.get('RECOGNITION_R26_V2')=='1'
        tranche='R26' if v2 else 'R24'
        policy_id=lineage.V2 if v2 else source.LIFETIME
        artifact_prefix='recognition-r26' if v2 else 'recognition-r24'
        if os.environ.get('RECOGNITION_R22_CHILD')!='1':
            env=dict(os.environ,RECOGNITION_R22_CHILD='1')
            result=run_child([sys.executable,'-B','-m','pytest',__file__+'::FinalizationLifecycleTests::test_one_disposable_original_lifecycle',
                              '-q','-s','-p','no:cacheprovider','--tb=short'],env=env,timeout=540)
            path=Path(__file__).resolve().parents[1]/'.tmp'/(artifact_prefix+'-parent.json')
            path.write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(tranche+'_PARENT_REPORT '+json.dumps(result))
            self.assertEqual('child_exited',result['status'])
            self.assertTrue(result['reaped']);self.assertTrue(result['cleanup_complete'])
            self.assertFalse(result['parent_bound_exceeded'])
            self.assertTrue(result['reports'],'no valid child lifecycle trace')
            self.assertNotEqual('D',result['reports'][-1]['classification'])
            self.assertEqual(0,result['exit_code'])
            return
        started=time.monotonic();stages=[];authority=[None];failure=[None];current=[None];current_row=[None]
        report=dict(classification='D',stages=stages,production=False,lifetime_policy=policy_id,
                    tranche=tranche,run_id=str(uuid4()),complete=False)
        output=Path(__file__).resolve().parents[1]/'.tmp'/(artifact_prefix+'-lifecycle.json')
        isolation=dict(lifetime_migrations=0,verified=False)
        report['isolation']=isolation
        def checkpoint():
            # A bounded parent timeout must not erase already reached stages.
            temporary=output.with_name(output.name+'.'+report['run_id']+'.next')
            temporary.write_text(json.dumps(report,indent=2),encoding='utf-8')
            temporary.replace(output)
        def budget():
            return None if authority[0] is None else max(0,z.a.timestamp(authority[0]['expires_at_utc'])-z.a.timestamp(z.v._utc_now()))
        def last_budget():
            # The fixture's live clock patch closes on exception. Preserve the
            # last product observation made INSIDE that clock/owner lifetime.
            return next((r['remaining_budget'] for r in reversed(stages)
                         if r.get('remaining_budget') is not None),None)
        @contextmanager
        def span(name):
            row=dict(stage=name,start_seconds=time.monotonic()-started,start_budget=budget(),status='running')
            stages.append(row);old=current[0];old_row=current_row[0];current[0]=name;current_row[0]=row
            checkpoint()
            try:
                yield
                row['status']='success'
            except BaseException as error:
                row['status']='failure';row['exception_class']=type(error).__name__
                row['error_code']=getattr(error,'code',str(error) if isinstance(error,ValueError) else None)
                if failure[0] is None:failure[0]=dict(row)
                raise
            finally:
                row.update(end_seconds=time.monotonic()-started,remaining_budget=budget())
                row['duration_seconds']=row['end_seconds']-row['start_seconds'];current[0]=old;current_row[0]=old_row
                checkpoint()
        real_body=issuer._body
        def body(state,artifact):
            value=real_body(state,artifact)
            self.assertIsNone(authority[0],'more than one original authority issued')
            if v2:
                # Existing R12 disposable selection: before persistence, retain
                # the real original subject/consent and all expiry clipping.
                self.assertTrue(isolation['verified']);self.assertTrue(state.issuance_phase)
                self.assertIsNone(state.pending)
                assert_disposable(state.config)
                step=source._artifact(state.control,artifact['step_artifact_sha256'],source.STEP_ACTION,source.STEP)
                deadlines=[state.control.execute('SELECT expires FROM '+table+' WHERE token_hash=?',
                    (value['authentication'][kind+'_sha256'],)).fetchone()[0]
                    for kind,table in (('primary','recognition_admin_primary'),('session','recognition_admin_sessions'))]
                deadlines.extend([z.a.timestamp(step['expires_at_utc']),z.a.timestamp(artifact['expires_at_utc'])])
                issued=z.a.timestamp(value['issued_at_utc'])
                value.update(lifetime_policy=policy_id,expires_at_utc=consent._time(min(issued+lifetime.seconds(policy_id),*deadlines)))
                value=source.validate_authority(value)
                report['original_deadline_remaining_seconds']=[x-issued for x in deadlines]
            self.assertEqual(policy_id,value['lifetime_policy'])
            self.assertEqual(lifetime.seconds(policy_id),z.a.timestamp(value['expires_at_utc'])-z.a.timestamp(value['issued_at_utc']))
            authority[0]=value
            report.update(authority_issued_elapsed=time.monotonic()-started,
                          authority_issued_at=value['issued_at_utc'],authority_expires_at=value['expires_at_utc'])
            return value
        def assert_disposable(config):
            from tests.recognition_authorization_fixture import workspace_for
            root=Path(workspace_for(config.target).name).resolve()
            self.assertEqual(Path(__file__).resolve().parents[1],root.parent)
            self.assertTrue(root.name.startswith('recognition-r22-'))
            self.assertTrue(all(p.resolve().is_relative_to(root) for p in (config.target,config.control,config.key_file)))
        real_migrate=z.s.migrate
        def migrated(config,**options):
            result=real_migrate(config,**options)
            assert_disposable(config)
            self.assertEqual(0,isolation['lifetime_migrations'])
            installed=lifetime.migrate(config,expected_generation=options['expected_generation'],
                operator='r26-disposable',reason='explicit isolated v2 representation before G+2 enrollment')
            self.assertTrue(installed['installed'])
            isolation.update(lifetime_migrations=1,verified=True)
            return result
        def observe(stack,module,name,label):
            # Call the real implementation once. No returned observation is
            # reused, and no security clock or predicate is substituted.
            original=getattr(module,name)
            def measured(*args,**kwargs):
                title=label(*args,**kwargs) if callable(label) else label
                with span(title):return original(*args,**kwargs)
            stack.enter_context(patch.object(module,name,new=measured))
        real_history=z.v._history_fresh
        def measured_history(control):
            row=current_row[0];start=time.perf_counter()
            try:return real_history(control)
            finally:
                if row is not None:
                    data=row.setdefault('full_history_validation',dict(calls=0,seconds=0.0))
                    data['calls']+=1;data['seconds']+=time.perf_counter()-start
        try:
            with isolated.bootstrap(), ExitStack() as timings:
                timings.enter_context(patch.object(z.v,'_history_fresh',new=measured_history))
                observe(timings,z.coordinator,'_finish',lambda state:
                    'coordinator issuance final validation' if state.issuance_phase else 'coordinator attempt final validation')
                observe(timings,z.coordinator,'_evaluate',lambda state:
                    'coordinator issuance live evaluation' if state.issuance_phase else 'coordinator attempt live evaluation')
                observe(timings,z.coordinator,'_persist_attempt','attempt preparation and exact graph INSERT')
                observe(timings,finalization,'_claim_issuer','prospective issuer-start validation and commit')
                observe(timings,z.metadata,'_evaluate','metadata fresh validation')
                observe(timings,z.metadata,'_mode','metadata target mode transition')
                observe(timings,z.metadata,'_commit_target','metadata target commit')
                observe(timings,z.metadata,'_reacquire','metadata reservation reacquisition')
                observe(timings,finalization,'_fresh','finalizer fresh validation')
                observe(timings,finalization,'_start','durable decision and pending fence')
                observe(timings,finalization,'_commit_control','finalization control commit')
                observe(timings,finalization,'_commit_target','atomic family and witness target commit')
                observe(timings,finalization.permanent,'_insert_family_effects','fixed family INSERT kernel')
                observe(timings,finalization.effects,'_evidence','actual family-effect witness evidence')
                observe(timings,finalization.storage,'_insert',lambda conn,table,row:
                    'target witness INSERT' if table==finalization.journal.WITNESSES else 'durable journal INSERT / '+table)
                with span('preparation / finalized G+2 fixture'),(patch.object(z.s,'migrate',migrated) if v2 else ExitStack()):
                    config,session,_,approval_id,options=fixture.CoordinatorFinalValidationProfileTests.prepare_g2(self)
                # Fixture-only pre-authority MFA ordering. Each new phase uses a
                # live monotonic clock; no issued authority exists or is renewed.
                origin=utc(z.v._utc_now())+timedelta(seconds=30);anchor=time.monotonic_ns();offset=[0]
                live=patch.object(z.v,'_utc_now',side_effect=lambda:(origin+timedelta(seconds=offset[0]+(time.monotonic_ns()-anchor)//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ'))
                with live:
                    with z.a.connect(config.control) as control,z.a.connect(config.target) as target:
                        binding,profile,_=z.v._history(control)
                        scope=z.v._identity_snapshot(config,control,target,z.v._utc_now())
                        runtime_target=dict(format=z.operation.TARGET_FORMAT) if hasattr(z,'operation') else dict(format='recognition-runtime-operation-target-v1')
                        runtime_target.update(installation_id=binding['installation_id'],target_id=binding['target_id'],
                            generation=binding['generation'],owner_id=binding['owner_id'],binding_sha256=digest(binding),
                            runtime_profile_sha256=profile['profile_sha256'],auth_epoch=scope['auth_epoch'],mfa_epoch=z.shared._mfa(control,binding))
                        op=load(target.execute('SELECT body_json FROM recognition_operation_contracts WHERE operation_id=?',
                            (options['reference']['operation_id'],)).fetchone()[0])
                        manifest=z.events.get_event(target,op['event_id'])['preparation']['manifest']
                    intent=dict(operation_id=op['operation_id'],operation_sha256=digest(op),writer_manifest_sha256=digest(manifest),
                        write_set_sha256=finalization._write_set(manifest),family=manifest['family'],runtime_target=runtime_target,action=contract.EFFECT)
                    policy=dict(format=contract.POLICY,policy_id=contract.ISSUER_ROLE,version=1,action=contract.EFFECT,max_grants=1,lifetime_policy=policy_id)
                    with span('issuer governance / MFA validation'):
                        receipt=finalization.authorize_issuer(config,session,z.totp.independent_code(z.v._utc_now()),intent,
                            primary_token=options['primary_token'],lifetime_policy=policy_id,**isolated.governance(config,intent,policy))
                    offset[0]+=30
                    with span('fresh original source consent'):
                        step=z.consent.issue_step_up(config,session,z.totp.independent_code(z.v._utc_now()),approval_id,**options)
                        confirmation=z.consent.begin_confirmation(config,session,step['token'],approval_id,
                            canonical(dict(decision='authorize_runtime_execution',reason=options['reason'],confirm=True)),**options)
                    with patch.object(issuer,'_body',side_effect=body):
                        manager=z.coordinator.coordinator(config,session,confirmation['token'],approval_id,**options,
                                                          finalization_issuer=receipt['issuer_sha256'])
                        with span('authority issuance / original coordinator admission'):
                            owner=manager.__enter__()
                        try:
                            outer=z.coordinator._outer(owner)
                            durable=load(outer.authority_json)
                            self.assertEqual(authority[0],durable)
                            self.assertEqual(policy_id,durable['lifetime_policy'])
                            report['authority_sha256']=digest(durable)
                            report['authority_id']=durable['authority_id']
                            with span('attempt creation / final validation'):attempt=owner.create_attempt()
                            with span('protected target-entry metadata'):entry=z.metadata.create_target_entry(attempt)
                            with span('fresh finalization / atomic effect and witness / control outcome'):
                                result=finalization.finalize(attempt,entry)
                            with span('durable outcome inspection'):
                                inspected=finalization.inspect_outcome(config,result['authority_id'])
                                self.assertEqual('COMPLETED',inspected['state'])
                                self.assertTrue(inspected['target_commit_verified'])
                                self.assertFalse(inspected['retry_authorized'])
                                self.assertEqual(result['authority_id'],inspected['authority_id'])
                                report['outcome']=dict(state=inspected['state'],target_commit_verified=True,
                                    retry_authorized=False,authority_id=result['authority_id'])
                        finally:
                            with span('cleanup / result publication'):manager.__exit__(*sys.exc_info())
                    report['classification']='A'
        except BaseException as error:
            code=getattr(error,'code',str(error) if isinstance(error,ValueError) else None)
            report.update(exception_class=type(error).__name__,error_code=code,
                          interrupted_stage=None if failure[0] is None else failure[0]['stage'])
            expired=authority[0] is not None and last_budget()==0 and code in (
                'administrative_session_expired_or_revoked','coordinator_authority_expired','metadata_authority_expired',
                'finalization_expired','finalization_issuer_expired','runtime_attempt_expired_or_clock_rollback')
            report['classification']=('B' if expired else 'D' if isinstance(error,OSError) else 'C') if v2 else ('C' if expired else 'B')
        finally:
            report.update(elapsed_seconds=time.monotonic()-started,remaining_authority_seconds=last_budget())
            report['complete']=True
            output.write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(MARKER+json.dumps(report),flush=True)
        self.assertIn(report['classification'],('A','B') if v2 else ('A','C'),
                      'implementation/fixture defect: inspect sanitized trace')
