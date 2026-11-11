"""Bounded disposable readiness/claim reader measurements; no Z or target entry."""

from collections import Counter
from contextlib import ExitStack, contextmanager
import json
from datetime import timedelta
from pathlib import Path
import sqlite3
import threading
import time
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, administration_schema as schema
from src.review.recognition import runtime_activation_authority_schema as authority
from src.review.recognition import runtime_execution_attempt_schema as attempts
from src.review.recognition import runtime_execution_claim_schema as claims
from src.review.recognition import runtime_enrollment_transition_schema as transitions
from src.review.recognition import runtime_validation as runtime, runtime_scope_validation as scope
from src.review.recognition import runtime_proposal_transaction as proposal
from src.review.recognition import local_readiness as readiness, execution
from tests import test_recognition_runtime_enrollment_transition as fixtures
from tests.test_recognition_runtime_execution_attempt_creation import _cleanup_fixture_tree


def previous_claim_manifest(conn, *, exclude=()):
    # Exact pre-Z2 reader: full transition validation followed by reconstruction.
    if authority._present(conn):
        authority.check_manifest_transition(conn)
        return attempts.authority_manifest(conn, exclude=set(exclude) | set(authority.definitions()))
    return attempts.authority_manifest(conn, exclude=exclude)


@contextmanager
def measured(control, target=None):
    stats = {}; stack = []; sql = Counter(); pragmas = Counter(); opens = [0]
    def trace(statement):
        words = statement.lstrip().split(None, 1)
        if not words: return
        kind = words[0].upper(); sql[kind] += 1
        lower = statement.lower()
        if kind == 'SELECT':
            for label, token in (('schema_reads','sqlite_master'), ('claim_reads', claims.CLAIMS),
                                 ('claim_history_reads',claims.HISTORY), ('audit_reads','recognition_admin_audit')):
                if token in lower: sql[label] += 1
        if kind == 'PRAGMA':
            pragmas[words[1].split('(',1)[0].split('=',1)[0].strip().rstrip(';').lower()] += 1
    def timed(fn, label):
        def call(*args, **kwargs):
            frame = [time.perf_counter(),0.0]; stack.append(frame)
            entry = stats.setdefault(label, dict(calls=0, exclusive_seconds=0.0, inclusive_seconds=0.0))
            entry['calls'] += 1
            try: return fn(*args, **kwargs)
            finally:
                elapsed = time.perf_counter()-frame[0]
                stack.pop(); entry['inclusive_seconds'] += elapsed; entry['exclusive_seconds'] += elapsed-frame[1]
                if stack: stack[-1][1] += elapsed
        return call
    connect = a.connect
    @contextmanager
    def opened(*args, **kwargs):
        opens[0] += 1
        with connect(*args, **kwargs) as conn: yield conn
    watched = ((schema,'check_control'), (claims,'check_rows'), (authority,'check_rows'),
               (attempts,'check_rows'), (transitions,'historical_manifest'), (claims,'manifest'),
               (runtime,'_history'), (readiness,'_assess_inventory'), (readiness,'_runtime_inventory'))
    result = dict(layers=stats, sql=sql, pragmas=pragmas)
    start = time.perf_counter()
    with ExitStack() as patches:
        for module, name in watched:
            patches.enter_context(patch.object(module,name,timed(getattr(module,name), module.__name__.rsplit('.',1)[-1]+'.'+name)))
        patches.enter_context(patch.object(a,'connect',opened))
        control.set_trace_callback(trace)
        if target is not None: target.set_trace_callback(trace)
        try: yield result
        finally:
            control.set_trace_callback(None)
            if target is not None: target.set_trace_callback(None)
            result.update(elapsed_seconds=time.perf_counter()-start,connection_opens=opens[0])


class ReadinessClaimEfficiencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Hard bound includes fixture setup, all focused cases and cleanup.
        import os
        cls.done = threading.Event()
        cls.addClassCleanup(cls.done.set)
        def watchdog():
            if not cls.done.wait(120): os._exit(124)
        threading.Thread(target=watchdog,daemon=True).start()
        cls.fixture = fixtures.EnrollmentTransitionTests()
        cls.addClassCleanup(_cleanup_fixture_tree, cls.fixture)
        cls.fixture.setUp(); cls.fixture.migrate()
        cls.config = cls.fixture.config
        cls.auth_fixture = cls.fixture.f.f.f

    @contextmanager
    def clone(self):
        with a.connect(self.config.control) as source:
            conn = sqlite3.connect(':memory:'); conn.row_factory = sqlite3.Row
            source.backup(conn)
        try:
            conn.execute('BEGIN IMMEDIATE'); yield conn
        finally: conn.close()

    def test_real_readiness_and_claim_validation_before_after(self):
        results = {}; values = []
        for label in ('before','after'):
            with ExitStack() as patches:
                if label == 'before':
                    patches.enter_context(patch.object(authority,'historical_claim_manifest',previous_claim_manifest))
                with proposal.proposal_transaction(self.config) as context:
                    view = proposal.read_view(context)
                    _, (control, _, binding, _), _ = scope._view_parts(view)
                    state = proposal._state(context)
                    with measured(state.control,state.target) as result:
                        value = readiness._assess_inventory(control,state.target,binding,runtime._utc_now(),config=self.config,
                            runtime=(view,self.auth_fixture.session,self.auth_fixture.primary))
                    values.append(readiness._assessment_binding(value)); results[label] = result
                    self.assertGreater(result['layers']['administration_schema.check_control']['calls'],0)
                    self.assertGreater(result['layers']['runtime_execution_claim_schema.check_rows']['calls'],0)
                    self.assertEqual(0,result['connection_opens'])
                    for mutation in ('INSERT','UPDATE','DELETE','CREATE','COMMIT'):
                        self.assertEqual(0,result['sql'][mutation])
        self.assertEqual(values[0],values[1])
        self.assertLess(results['after']['layers']['runtime_enrollment_transition_schema.historical_manifest']['calls'],
                        results['before']['layers']['runtime_enrollment_transition_schema.historical_manifest']['calls'])
        output = Path(__file__).resolve().parents[1]/'.tmp'/'recognition-z2-readiness-timing.json'
        output.parent.mkdir(exist_ok=True); output.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')

    def test_exact_projection_and_fallbacks(self):
        with self.clone() as conn:
            expected = previous_claim_manifest(conn)
            with patch.object(attempts,'authority_manifest',wraps=attempts.authority_manifest) as reads:
                self.assertEqual(expected,authority.historical_claim_manifest(conn)); self.assertEqual(2,reads.call_count)
            for exclude in ((), tuple(claims.definitions())):
                self.assertEqual(previous_claim_manifest(conn,exclude=exclude),authority.historical_claim_manifest(conn,exclude=exclude))
            conn.rollback()
            with patch.object(attempts,'authority_manifest',wraps=attempts.authority_manifest) as reads:
                self.assertEqual(expected,authority.historical_claim_manifest(conn)); self.assertEqual(3,reads.call_count)
            conn.execute('BEGIN IMMEDIATE')
            class Adapter:
                def execute(self,*args): return conn.execute(*args)
            with patch.object(attempts,'authority_manifest',wraps=attempts.authority_manifest) as reads:
                self.assertEqual(expected,authority.historical_claim_manifest(Adapter())); self.assertEqual(3,reads.call_count)

    def test_each_call_revalidates_after_transaction_auth_and_mode_changes(self):
        with self.clone() as conn:
            with patch.object(authority,'check_manifest_transition',wraps=authority.check_manifest_transition) as validate:
                for change in ('SELECT 1','UPDATE recognition_admin_sessions SET revoked=1',
                               'UPDATE recognition_admin_mfa SET epoch=epoch+1','PRAGMA query_only=ON'):
                    conn.execute(change); authority.historical_claim_manifest(conn)
                conn.rollback(); conn.execute('BEGIN'); authority.historical_claim_manifest(conn)
                self.assertEqual(5,validate.call_count)

    def test_changed_history_and_schema_rejected_on_next_call(self):
        for corrupt in ('schema','audit'):
            with self.subTest(corrupt=corrupt), self.clone() as conn:
                authority.historical_claim_manifest(conn)
                if corrupt == 'schema': conn.execute('CREATE TABLE unexpected(value TEXT)')
                else:
                    triggers=conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='recognition_admin_audit'").fetchall()
                    for row in triggers: conn.execute('DROP TRIGGER "'+row[0].replace('"','""')+'"')
                    conn.execute("UPDATE recognition_admin_audit SET body_sha256=? WHERE json_extract(body_json,'$.action')=?", ('0'*64,authority.ACTION))
                    for row in triggers: conn.execute(row[1])
                with self.assertRaises(ValueError): authority.historical_claim_manifest(conn)

    def test_changed_readiness_emergency_stop_is_detected(self):
        # New reads within the SAME reserved validation operation must see DML.
        # This uses disposable clones, not a production owner or mutation API.
        with self.clone() as conn:
            authority.historical_claim_manifest(conn)
            before=execution._stop(conn)
            from src.review.recognition import events
            from src.review.recognition.rules import digest
            body=dict(before,sequence=before['sequence']+1,active=True,reason='disposable stop change',previous_sha256=digest(before))
            events._insert(conn,'recognition_execution_stops','sequence',(body['sequence'],),body)
            authority.historical_claim_manifest(conn)
            self.assertTrue(execution._stop(conn)['active'])

    def test_reservation_epoch_change_rejects_borrowed_admission_view(self):
        from src.review.recognition import runtime_admission_validation as admission
        with self.assertRaises(ValueError):
            with proposal.proposal_transaction(self.config) as context:
                view=admission.proposal_read_view(context)
                state=proposal._state(context)
                authority.historical_claim_manifest(state.control)
                state.target_reservation_epoch+=1
                admission._resolve(view)

    def test_generation_activation_mutation_does_not_reuse_manifest_observation(self):
        with self.clone() as conn:
            with patch.object(authority,'check_manifest_transition',wraps=authority.check_manifest_transition) as validate:
                authority.historical_claim_manifest(conn)
                for table,assignment in (
                    ('recognition_local_activation', "body_sha256='"+'0'*64+"'"),
                    ('recognition_admin_bindings', "body_json=json_set(body_json,'$.generation',999)"),
                ):
                    triggers=conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",(table,)).fetchall()
                    for row in triggers:conn.execute('DROP TRIGGER "'+row[0].replace('"','""')+'"')
                    self.assertGreater(conn.execute('UPDATE '+table+' SET '+assignment).rowcount,0)
                    for row in triggers:conn.execute(row[1])
                    authority.historical_claim_manifest(conn)
                self.assertEqual(3,validate.call_count)
                # Manifest inspection is not a current generation/activation verdict.
                with self.assertRaises(ValueError):runtime._history(conn)

    def test_original_authority_lifetime_boundary_remains_120_seconds(self):
        from src.review.recognition.trust import utc
        body=self.fixture.f.f.body()  # Existing synthetic codec fixture, never inserted.
        self.assertEqual(body,authority.validate_authority(body))
        body['expires_at_utc']=(utc(body['issued_at_utc'])+timedelta(seconds=121)).strftime('%Y-%m-%dT%H:%M:%SZ')
        with self.assertRaisesRegex(ValueError,'runtime_authority_lifetime'):
            authority.validate_authority(body)

    def test_z_real_claim_lifecycle_change_is_fresh_and_corruption_rejected(self):
        from src.review.recognition import runtime_claim_disposition as disposition
        from src.review.recognition import runtime_execution_claims as claim_owner
        from src.review.recognition.trust import utc
        from tests.test_recognition_runtime_claim_disposition import RuntimeClaimDispositionTests
        claim=self.auth_fixture.f.acquire()
        self.body=json.loads(claim.canonical_json)
        self.assertEqual(300,a.timestamp(self.body['expires_at_utc'])-a.timestamp(self.body['issued_at_utc']))
        def observed():
            with a.connect(self.config.control) as conn:
                conn.execute('BEGIN')
                with measured(conn) as stats:
                    binding,profile,head=runtime._history(conn)
                    result=disposition._inspect_reserved(conn,binding,profile,head,claim_owner._Clock())
                self.assertGreater(stats['sql']['claim_history_reads'],0)
                self.assertGreater(stats['layers']['runtime_execution_claim_schema.check_rows']['calls'],0)
                return result
        self.assertEqual('ISSUED',observed()['claims'][0]['state'])
        self.at=lambda seconds:(utc(self.body['issued_at_utc'])+timedelta(seconds=seconds)).strftime('%Y-%m-%dT%H:%M:%SZ')
        RuntimeClaimDispositionTests.transition(self,'CONSUMED',1)
        with patch.object(runtime,'_utc_now',return_value=self.at(1)):
            after=observed()
        self.assertEqual('CONSUMED',after['claims'][0]['state'])
        self.assertFalse(after['execution_authority'])
        # The unchanged historical reader must also reject a modified lifecycle.
        with self.clone() as conn:
            triggers=conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",(claims.HISTORY,)).fetchall()
            for row in triggers:conn.execute('DROP TRIGGER "'+row[0].replace('"','""')+'"')
            conn.execute('UPDATE '+claims.HISTORY+' SET body_sha256=? WHERE sequence=2',('0'*64,))
            for row in triggers:conn.execute(row[1])
            with self.assertRaises(ValueError):schema.check_control(conn)


if __name__=='__main__': unittest.main()
