"""One clean R28 owner/production-topology measurement after focused tests."""
from contextlib import contextmanager,ExitStack
import json,os,sys,time,unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from tests.runtime_deadline_harness import run_child,MARKER
from tests import recognition_production_owner_ceremony as owner
from tests import recognition_production_owner_fixture as fixture
from src.review.recognition import runtime_finalization as f,runtime_execution_coordinator as coordinator
from src.review.recognition import runtime_target_entry_owner as metadata
from src.review.recognition.rules import digest


class OwnerLifecycleTests(unittest.TestCase):
    def test_one_clean_owner_lifecycle(self):
        root=Path(__file__).resolve().parents[1]
        if os.environ.get('RECOGNITION_R28_OWNER_CHILD')!='1':
            env=dict(os.environ,RECOGNITION_R28_OWNER_CHILD='1')
            result=run_child([sys.executable,'-B','-m','pytest',__file__+'::OwnerLifecycleTests::test_one_clean_owner_lifecycle','-q','-s','-p','no:cacheprovider','--tb=short'],env=env,timeout=540)
            (root/'.tmp'/'recognition-r28-owner-parent.json').write_text(json.dumps(result,indent=2)+'\n')
            self.assertEqual('child_exited',result['status']);self.assertEqual(0,result['exit_code'],result)
            self.assertTrue(result['reaped'] and result['cleanup_complete'] and not result['parent_bound_exceeded'])
            self.assertEqual('A',result['reports'][-1]['classification'])
            return
        started=time.monotonic();rows=[];last_budget=[None]
        report=dict(classification='F',run_id=str(uuid4()),actual_production=False,stages=rows,lifetime_policy='recognition-runtime-authority-lifetime-300s-v2')
        output=root/'.tmp'/'recognition-r28-owner-lifecycle.json'
        def remaining():
            body=getattr(self,'owner_authority',None)
            return None if body is None else owner.a.timestamp(body['expires_at_utc'])-owner.a.timestamp(owner.v._utc_now())
        @contextmanager
        def span(name):
            row=dict(stage=name,start_seconds=time.monotonic()-started,start_budget=remaining(),status='running');rows.append(row)
            output.write_text(json.dumps(report,indent=2))
            try:yield;row['status']='success'
            except BaseException as error:
                row.update(status='failure',exception_class=type(error).__name__,error_code=getattr(error,'code',str(error) if isinstance(error,ValueError) else None));raise
            finally:
                row.update(end_seconds=time.monotonic()-started,remaining_budget=remaining())
                row['duration_seconds']=row['end_seconds']-row['start_seconds']
                if row['remaining_budget'] is not None:last_budget[0]=row['remaining_budget']
                output.write_text(json.dumps(report,indent=2))
        def observe(stack,module,name,label):
            real=getattr(module,name)
            def measured(*args,**kwargs):
                with span(label):return real(*args,**kwargs)
            stack.enter_context(patch.object(module,name,side_effect=measured))
        try:
            with ExitStack() as timings:
                for module,name,label in [(coordinator,'_finish','coordinator final validation'),(metadata,'_evaluate','metadata fresh validation'),(metadata,'_commit_target','metadata commit'),(metadata,'_reacquire','metadata reservation reacquisition'),(f,'_fresh','fresh finalizer validation'),(f,'_start','durable decision and pending'),(f.permanent,'_insert_family_effects','fixed family business effect'),(f.effects,'_evidence','complete-effect witness evidence'),(f,'_commit_target','atomic effect/witness target commit'),(f,'_commit_control','control commit')]:observe(timings,module,name,label)
                with owner.ceremony(self,stage=span) as info:
                    with span('protected owner finalization'):result=f.finalize(info['attempt'],info['entry'])
                    with span('independent production-path outcome inspection'):
                        proof,_,_=fixture.signed(info['config'],info['session'],info['primary'],dict(kind='inspect',authority_id=result['authority_id'],authority_sha256=result['authority_sha256']),info['key'])
                        inspected=f.inspect_outcome(info['config'],result['authority_id'],approval=proof['approvals'][0],authority=proof['authority'])
                        self.assertEqual('COMPLETED',inspected['state']);self.assertTrue(inspected['target_commit_verified']);self.assertFalse(inspected['retry_authorized'])
                        self.assertEqual(result['authority_id'],inspected['authority_id'])
                        report['outcome']=dict(inspected)
                    report.update(authority_issued_at=self.owner_authority['issued_at_utc'],authority_expires_at=self.owner_authority['expires_at_utc'],authority_elapsed_seconds=time.monotonic()-self.owner_issued_tick)
            self.assertGreater(last_budget[0],0)
            report['classification']='A'
        except BaseException as error:
            code=getattr(error,'code',str(error) if isinstance(error,ValueError) else None)
            report.update(classification='B' if last_budget[0] is not None and last_budget[0]<=0 else 'C',exception_class=type(error).__name__,error_code=code)
        finally:
            report.update(elapsed_seconds=time.monotonic()-started,remaining_authority_seconds=last_budget[0])
            output.write_text(json.dumps(report,indent=2)+'\n')
            print(MARKER+json.dumps(report),flush=True)
        self.assertEqual('A',report['classification'],'inspect owner lifecycle trace; no automatic rerun')
