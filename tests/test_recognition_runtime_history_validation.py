"""R24 genuine-owner, one-evaluation history reuse and invalidation."""
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import time
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from tests import test_recognition_runtime_finalization_integration as fixture
from src.review.recognition import runtime_finalization as f, runtime_history_validation as history
from src.review.recognition import runtime_validation as v, administration as a


class HistoryValidationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.GovernanceIntegrationTests();self.f.setUp();self.addCleanup(self.f.doCleanups)

    def reserved(self):return f._reserved(self.f.config,self.f.session,self.f.primary)

    def test_each_evaluation_fresh_and_results_do_not_alias(self):
        with self.reserved() as state:
            with patch.object(v,'_history_fresh',wraps=v._history_fresh) as fresh:
                with history.operation(state):
                    first=v._history(state.control);original=first[0]['owner_id']
                    first[0]['owner_id']=-1
                    self.assertEqual(original,v._history(state.control)[0]['owner_id'])
                    self.assertEqual(1,fresh.call_count)
                self.assertIsNone(history.read(state.control))
                with history.operation(state):v._history(state.control)
                self.assertEqual(2,fresh.call_count)
            f.p._rollback(state,state.control)

    def test_zero_row_mutation_invalidates_even_without_total_changes(self):
        with self.reserved() as state:
            with history.operation(state),patch.object(v,'_history_fresh',wraps=v._history_fresh) as fresh:
                v._history(state.control);before=state.control.total_changes
                state.writes='MFA';state.control.set_authorizer(state.control_authorizer)
                state.control.execute('UPDATE recognition_admin_mfa SET last_counter=last_counter WHERE actor=-1')
                state.writes=None;state.control.set_authorizer(state.control_authorizer)
                self.assertEqual(before,state.control.total_changes)
                v._history(state.control);self.assertEqual(2,fresh.call_count)
            f.p._rollback(state,state.control)

    def test_physical_change_rejected_on_consumption(self):
        with self.assertRaisesRegex(ValueError,'history_validation_physical_changed'):
            with self.reserved() as state,history.operation(state):
                v._history(state.control)
                actual=a.target_identity
                def changed(path):
                    value=actual(path)
                    return replace(value,inode=value.inode+1) if path==state.config.target else value
                with patch.object(a,'target_identity',side_effect=changed):v._history(state.control)

    def test_noncurrent_historical_path_is_reresolved_on_consumption(self):
        from src.review.recognition import runtime_enrollment as enrollment
        original=v._history_fresh
        old=str(self.f.config.target.parent/'historical-noncurrent.db')
        def full_history(control):
            value=original(control)
            enrollment._path(old)  # Same kernel used by older binding/review paths.
            return value
        with self.assertRaisesRegex(a.AdminError,'runtime_enrollment_path_invalid'):
            with self.reserved() as state,history.operation(state),patch.object(v,'_history_fresh',new=full_history):
                v._history(state.control)
                real=Path.resolve
                def changed(path,*args,**kwargs):
                    return Path(old+'.changed') if str(path)==old else real(path,*args,**kwargs)
                with patch.object(Path,'resolve',new=changed):v._history(state.control)

    def test_owner_epoch_change_and_cross_thread_rejected(self):
        with self.reserved() as state:
            with history.operation(state):
                v._history(state.control)
                with ThreadPoolExecutor(max_workers=1) as pool:
                    with self.assertRaises(a.AdminError):pool.submit(lambda:history._key(state)).result()
            # No foreign-thread result is issued. Manager rollback remains
            # responsible for resolution in the original thread.
            f.p._rollback(state,state.control)

    def test_forged_state_rejected(self):
        with self.assertRaisesRegex(ValueError,'history_validation_owner_invalid'):
            with history.operation(object()):pass

    def test_scope_and_mode_change_cannot_rebind_an_active_operation(self):
        with self.assertRaisesRegex(ValueError,'history_validation_scope_changed'):
            with self.reserved() as state,history.operation(state):
                v._history(state.control)
                f._mode(state,query_only=False)
                v._history(state.control)

    def test_fresh_authentication_still_observes_revocation(self):
        with self.assertRaises(a.AdminError):
            with self.reserved() as state,history.operation(state):
                v._history(state.control)
                state.kernel_control.execute('UPDATE recognition_admin_sessions SET revoked=1 WHERE token_hash=?',
                                            (a.token_hash(self.f.session),))
                state.view.validate_session(self.f.session,primary_token=self.f.primary)

    def test_query_and_elapsed_reduction_with_same_result_and_fresh_physical_reads(self):
        with self.reserved() as state:
            counts=[0];times={};results=[]
            state.control.set_trace_callback(lambda sql:counts.__setitem__(0,counts[0]+1))
            try:
                start=time.perf_counter();before=counts[0]
                for _ in range(4):results.append(v._history(state.control))
                times['fresh']=dict(seconds=time.perf_counter()-start,statements=counts[0]-before)
                with history.operation(state),patch.object(history,'_physical',wraps=history._physical) as physical:
                    start=time.perf_counter();before=counts[0]
                    for _ in range(4):self.assertEqual(results[0],v._history(state.control))
                    times['one_evaluation']=dict(seconds=time.perf_counter()-start,statements=counts[0]-before)
                    self.assertEqual(4,physical.call_count)
                self.assertLess(times['one_evaluation']['statements'],times['fresh']['statements'])
            finally:state.control.set_trace_callback(None)
            path=Path(__file__).resolve().parents[1]/'.tmp'/'recognition-r24-history-cost.json'
            path.write_text(json.dumps(times,indent=2)+'\n',encoding='utf-8')
            f.p._rollback(state,state.control)
