"""Bounded final-validation measurements; no metadata owner or target entry."""

from collections import Counter
from contextlib import ExitStack, contextmanager
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, administration_schema as schema
from src.review.recognition import runtime_execution_coordinator as coordinator
from src.review.recognition import runtime_activation_authority_issuance as issuer
from src.review.recognition import runtime_activation_authority_schema as authority
from src.review.recognition import runtime_execution_attempt_schema as attempts
from src.review.recognition import runtime_execution_claim_schema as claims
from src.review.recognition import runtime_enrollment_transition_schema as transitions
from src.review.recognition import runtime_validation as runtime, local_readiness as readiness
from tests import test_recognition_runtime_enrollment_transition as fixtures
from tests import test_recognition_runtime_execution_coordinator as coordinator_fixtures
from tests.test_recognition_runtime_execution_attempt_creation import _cleanup_fixture_tree


def previous_authority_manifest(conn, *, exclude=()):
    """Exact pre-Z3 projection, for equivalence/timing only."""
    if attempts.present(conn):
        attempts.check_manifest_transition(conn)
        return transitions.historical_manifest(conn,exclude=set(exclude)|set(attempts.definitions()))
    return claims.manifest(conn,exclude=exclude)


@contextmanager
def measurement(control,target):
    layers={}; stack=[]; sql=Counter(); pragmas=Counter(); opens=[0]
    def trace(statement):
        parts=statement.lstrip().split(None,1)
        if not parts:return
        kind=parts[0].upper();sql[kind]+=1;lower=statement.lower()
        if kind=='SELECT':
            for label, token in (('schema_reads','sqlite_master'),('claim_reads',claims.CLAIMS),
                                ('approval_reads','recognition_approval'),('ack_reads','runtime_proposal_acknowledged'),
                                ('activation_reads','recognition_local_activation'),('profile_reads','recognition_runtime_profiles'),
                                ('audit_reads','recognition_admin_audit')):
                if token in lower:sql[label]+=1
        if kind=='PRAGMA':pragmas[parts[1].split('(',1)[0].split('=',1)[0].strip().rstrip(';').lower()]+=1
    def timed(fn,label):
        def call(*args,**kwargs):
            frame=[time.perf_counter(),0.0];stack.append(frame)
            entry=layers.setdefault(label,dict(calls=0,inclusive_seconds=0.0,exclusive_seconds=0.0));entry['calls']+=1
            try:return fn(*args,**kwargs)
            finally:
                elapsed=time.perf_counter()-frame[0];stack.pop()
                entry['inclusive_seconds']+=elapsed;entry['exclusive_seconds']+=elapsed-frame[1]
                if stack:stack[-1][1]+=elapsed
        return call
    connect=a.connect
    @contextmanager
    def opened(*args,**kwargs):
        opens[0]+=1
        with connect(*args,**kwargs) as conn:yield conn
    watched=((coordinator,'_evaluate'),(issuer,'_subject_for_owner'),(readiness,'_assess_inventory'),
             (runtime,'_identity_snapshot'),(runtime,'_history'),(schema,'check_control'),
             (claims,'check_rows'),(transitions,'historical_manifest'))
    data=dict(layers=layers,sql=sql,pragmas=pragmas);start=time.perf_counter()
    with ExitStack() as patches:
        for module,name in watched:
            patches.enter_context(patch.object(module,name,timed(getattr(module,name),module.__name__.rsplit('.',1)[-1]+'.'+name)))
        patches.enter_context(patch.object(a,'connect',opened))
        control.set_trace_callback(trace);target.set_trace_callback(trace)
        try:yield data
        finally:
            control.set_trace_callback(None);target.set_trace_callback(None)
            data.update(elapsed_seconds=time.perf_counter()-start,connection_opens=opens[0])


class CoordinatorFinalEfficiencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.done=threading.Event();cls.addClassCleanup(cls.done.set)
        def watchdog():
            if not cls.done.wait(180):os._exit(124)
        threading.Thread(target=watchdog,daemon=True).start()
        cls.fixture=fixtures.EnrollmentTransitionTests()
        cls.addClassCleanup(_cleanup_fixture_tree,cls.fixture)
        cls.fixture.setUp();cls.fixture.migrate()

    @contextmanager
    def clone(self):
        with a.connect(self.fixture.config.control) as source:
            conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row;source.backup(conn)
        try:conn.execute('BEGIN IMMEDIATE');yield conn
        finally:conn.close()

    def test_projection_is_verified_locally_and_unreserved_adapter_paths_unchanged(self):
        with self.clone() as conn:
            expected=previous_authority_manifest(conn)
            with patch.object(transitions,'historical_manifest',wraps=transitions.historical_manifest) as reads:
                self.assertEqual(expected,attempts.authority_manifest(conn));self.assertEqual(2,reads.call_count)
            for excluded in ((),tuple(authority.definitions())):
                self.assertEqual(previous_authority_manifest(conn,exclude=excluded),attempts.authority_manifest(conn,exclude=excluded))
            conn.rollback()
            with patch.object(transitions,'historical_manifest',wraps=transitions.historical_manifest) as reads:
                self.assertEqual(expected,attempts.authority_manifest(conn));self.assertEqual(3,reads.call_count)
            conn.execute('BEGIN IMMEDIATE')
            class Adapter:
                def execute(self,*args):return conn.execute(*args)
            with patch.object(transitions,'historical_manifest',wraps=transitions.historical_manifest) as reads:
                self.assertEqual(expected,attempts.authority_manifest(Adapter()));self.assertEqual(3,reads.call_count)

    def test_auth_mode_and_transaction_changes_never_reuse_previous_call(self):
        with self.clone() as conn:
            with patch.object(attempts,'check_manifest_transition',wraps=attempts.check_manifest_transition) as checks:
                for change in ('SELECT 1','UPDATE recognition_admin_sessions SET revoked=1',
                               'UPDATE recognition_admin_mfa SET epoch=epoch+1','PRAGMA query_only=ON'):
                    conn.execute(change);attempts.authority_manifest(conn)
                conn.rollback();conn.execute('BEGIN');attempts.authority_manifest(conn)
                self.assertEqual(5,checks.call_count)

    def test_invalid_exclusion_inputs_keep_original_error_behavior(self):
        with self.clone() as conn:
            for excluded in (None,False,0):
                with self.subTest(exclude=excluded):
                    with self.assertRaises(TypeError):previous_authority_manifest(conn,exclude=excluded)
                    with self.assertRaises(TypeError):attempts.authority_manifest(conn,exclude=excluded)

    def test_changed_schema_history_and_generation_reject_on_next_validation(self):
        for corrupt in ('schema','history','generation'):
            with self.subTest(corrupt=corrupt),self.clone() as conn:
                attempts.authority_manifest(conn)
                if corrupt=='schema':conn.execute('CREATE TABLE unexpected(value TEXT)')
                else:
                    table='recognition_admin_audit' if corrupt=='history' else 'recognition_admin_bindings'
                    triggers=conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",(table,)).fetchall()
                    for row in triggers:conn.execute('DROP TRIGGER "'+row[0].replace('"','""')+'"')
                    if corrupt=='history':conn.execute("UPDATE recognition_admin_audit SET body_sha256=? WHERE json_extract(body_json,'$.action')=?",('0'*64,attempts.ACTION))
                    else:conn.execute("UPDATE recognition_admin_bindings SET body_json=json_set(body_json,'$.generation',999)")
                    for row in triggers:conn.execute(row[1])
                with self.assertRaises(ValueError):runtime._history(conn)

    def test_reservation_epoch_change_rejects_previously_borrowed_view(self):
        from src.review.recognition import runtime_proposal_transaction as proposal, runtime_admission_validation as admission
        with self.assertRaises(ValueError):
            with proposal.proposal_transaction(self.fixture.config) as context:
                view=admission.proposal_read_view(context);state=proposal._state(context)
                attempts.authority_manifest(state.control)
                state.control_reservation_epoch+=1
                admission._resolve(view)

    def test_activation_and_readiness_changes_are_read_again(self):
        from src.review.recognition import execution,events
        from src.review.recognition.rules import digest
        with self.clone() as conn:
            with patch.object(attempts,'check_manifest_transition',wraps=attempts.check_manifest_transition) as checks:
                attempts.authority_manifest(conn)
                old=execution._stop(conn)
                body=dict(old,sequence=old['sequence']+1,active=True,reason='disposable readiness change',previous_sha256=digest(old))
                events._insert(conn,'recognition_execution_stops','sequence',(body['sequence'],),body)
                attempts.authority_manifest(conn)
                self.assertTrue(execution._stop(conn)['active'])
                table='recognition_local_activation'
                triggers=conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",(table,)).fetchall()
                for row in triggers:conn.execute('DROP TRIGGER "'+row[0].replace('"','""')+'"')
                conn.execute('UPDATE '+table+' SET body_sha256=?',('0'*64,))
                for row in triggers:conn.execute(row[1])
                attempts.authority_manifest(conn)
                self.assertEqual(3,checks.call_count)
                binding=transitions._binding(conn,3)
                with self.assertRaises(ValueError):readiness._state(conn,binding)

    def test_authority_120_second_limit_unchanged(self):
        from datetime import timedelta
        from src.review.recognition.trust import utc
        body=self.fixture.f.f.body()
        self.assertEqual(body,authority.validate_authority(body))
        body['expires_at_utc']=(utc(body['issued_at_utc'])+timedelta(seconds=121)).strftime('%Y-%m-%dT%H:%M:%SZ')
        with self.assertRaisesRegex(ValueError,'runtime_authority_lifetime'):authority.validate_authority(body)

class RealCoordinatorFinalEfficiencyTests(unittest.TestCase):
    def test_real_coordinator_finish_before_after_and_fresh_owner_guards(self):
        # Separate class: the schema fixture's simulated runtime identity patch
        # must be cleaned up before a different installation fixture is built.
        done=threading.Event();self.addCleanup(done.set)
        progress=dict(phase='fixture setup');results={}
        output=Path(__file__).resolve().parents[1]/'.tmp'/'recognition-z3-final-timing.json'
        output.parent.mkdir(exist_ok=True)
        def report():output.write_text(json.dumps(dict(progress=progress,results=results),indent=2)+'\n',encoding='utf-8')
        def watchdog():
            if not done.wait(240):
                try:report()
                finally:os._exit(124)
        threading.Thread(target=watchdog,daemon=True).start()
        f=coordinator_fixtures.RuntimeExecutionCoordinatorTests()
        self.addCleanup(_cleanup_fixture_tree,f);f.setUp()
        root=f.config.target.parent;backups=(root/'z3-target.db',root/'z3-control.db')
        for path,backup in zip((f.config.target,f.config.control),backups):
            with a.connect(path) as source,sqlite3.connect(backup) as destination:source.backup(destination)
        def restore():
            for backup,path in zip(backups,(f.config.target,f.config.control)):
                with sqlite3.connect(backup) as source,sqlite3.connect(path) as destination:source.backup(destination)
        finish=coordinator._finish
        for label in ('before','after'):
            restore()
            progress['phase']=label+' issuance';report()
            def observed(state):
                if state.issuance_phase:return finish(state)
                progress['phase']=label+' final validation'
                # Fresh physical validation still rejects even after initial
                # admission. This pure read does not replace the final decision.
                observer=a.target_identity
                with patch.object(a,'target_identity',side_effect=lambda obj:replace(observer(obj),device=observer(obj).device+1)):
                    with self.assertRaises(ValueError):coordinator._current(state)
                with measurement(state.control,state.target) as stats:
                    results[label]=stats;report();finish(state)
                report()
            with ExitStack() as patches:
                if label=='before':patches.enter_context(patch.object(attempts,'authority_manifest',previous_authority_manifest))
                patches.enter_context(patch.object(coordinator,'_finish',side_effect=observed))
                with f.coordinator() as owner:
                    progress['phase']=label+' attempt creation';report()
                    result=owner.create_attempt()
                    self.assertEqual('ATTEMPT_CREATED',result.snapshot['state'])
                    self.assertFalse(result.snapshot['execution_authority'])
                    body=json.loads(coordinator._outer(owner).authority_json)
                    self.assertEqual(120,a.timestamp(body['expires_at_utc'])-a.timestamp(body['issued_at_utc']))
            stats=results[label]
            for layer in ('runtime_execution_coordinator._evaluate','runtime_activation_authority_issuance._subject_for_owner',
                          'local_readiness._assess_inventory','runtime_validation._history','administration_schema.check_control'):
                self.assertGreater(stats['layers'][layer]['calls'],0)
            for mutation in ('INSERT','UPDATE','DELETE','CREATE'):self.assertEqual(0,stats['sql'][mutation])
            self.assertEqual(1,stats['sql']['COMMIT']);self.assertEqual(0,stats['connection_opens'])
        self.assertLess(results['after']['layers']['runtime_enrollment_transition_schema.historical_manifest']['calls'],
                        results['before']['layers']['runtime_enrollment_transition_schema.historical_manifest']['calls'])
        progress['phase']='complete';report()
