"""R22 bounded source-owner component profile; no authority or metadata entry."""
import cProfile
import json
import os
from pathlib import Path
import pstats
import sys
import time
import unittest
from unittest.mock import patch

from tests.runtime_deadline_harness import run_child, MARKER
from tests import test_recognition_runtime_finalization_integration as integration
from src.review.recognition import runtime_execution_coordinator as coordinator
from src.review.recognition import runtime_finalization as finalization
from src.review.recognition import runtime_activation_authority_issuance as issuer


class _DiagnosticStop(BaseException):
    pass


class FinalizationProfileTests(unittest.TestCase):
    def test_bounded_source_owner_profile(self):
        root=Path(__file__).resolve().parents[1]/'.tmp'
        if os.environ.get('RECOGNITION_R22_PROFILE_CHILD') != '1':
            result=run_child([sys.executable,'-B','-m','pytest',__file__+
                '::FinalizationProfileTests::test_bounded_source_owner_profile','-q','-s',
                '-p','no:cacheprovider','--tb=short'],timeout=120,
                env=dict(os.environ,RECOGNITION_R22_PROFILE_CHILD='1'))
            (root/'recognition-r22-profile-parent.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            self.assertEqual('child_exited',result['status'])
            self.assertEqual(0,result['exit_code'])
            self.assertTrue(result['reaped'])
            return
        profile=cProfile.Profile();started=[None];stopped=[False];counts=dict(checks=0,deadlines=0,unique=0)
        claim=finalization._claim_issuer;check=coordinator._Outer.check
        def measured_claim(*args):
            started[0]=time.monotonic();profile.enable()
            try:
                claim(*args)
                stopped[0]=True
                raise _DiagnosticStop('source component completed; authority construction forbidden')
            finally:profile.disable()
        def checked_owner(owner,**kwargs):
            if started[0] is not None:
                counts['checks']+=1
                if counts['checks']%128==1:
                    counts['deadlines']=len(owner.auth_expiries)
                    counts['unique']=len(set(owner.auth_expiries))
                if time.monotonic()-started[0]>=12:
                    stopped[0]=True
                    raise _DiagnosticStop('bounded pre-authority component profile stop')
            return check(owner,**kwargs)
        f=integration.GovernanceIntegrationTests('test_original_source_binding_and_single_issuer_consumption')
        authority_calls=[0]
        def forbidden_authority(*args):
            authority_calls[0]+=1
            raise AssertionError('authority issuance forbidden in component profile')
        try:
            f.setUp()
            with patch.object(finalization,'_claim_issuer',new=measured_claim), \
                 patch.object(coordinator._Outer,'check',new=checked_owner), \
                 patch.object(issuer,'_body',new=forbidden_authority):
                with self.assertRaises(_DiagnosticStop):f.test_original_source_binding_and_single_issuer_consumption()
        finally:
            profile.disable();f.doCleanups()
            rows=[]
            for (filename,line,name),(primitive,calls,exclusive,total,callers) in pstats.Stats(profile).stats.items():
                rows.append(dict(file=Path(filename).name,line=line,function=name,calls=calls,
                                 exclusive_seconds=exclusive,inclusive_seconds=total))
            report=dict(diagnostic_only=True,stage='pre-authority original-owner claim',counts=counts,
                        elapsed_seconds=None if started[0] is None else time.monotonic()-started[0],
                        authority_calls=authority_calls[0],rows=sorted(rows,key=lambda r:r['exclusive_seconds'],reverse=True))
            (root/'recognition-r22-source-profile.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print(MARKER+json.dumps(dict(diagnostic='R22 source component',counts=counts,
                elapsed_seconds=report['elapsed_seconds'],top=report['rows'][:20])),flush=True)
        self.assertTrue(stopped[0]);self.assertEqual(0,authority_calls[0])
