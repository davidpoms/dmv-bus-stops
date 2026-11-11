"""R22 disposable fixed-effect proof; no production authority or key material."""

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import permanent, runtime_finalization_effects as effects
from src.review.recognition import runtime_finalization_contract as contract
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_permanent as legacy


class FinalizationEffectsTests(unittest.TestCase):
    def setUp(self):
        # Dedicated test-only allocation, preserving shared fixtures and SQLite
        # settings. Windows restricted Temp/0700 is not usable on this host.
        def writable(suffix=None, prefix=None, dir=None):
            root = Path(__file__).resolve().parents[1]
            path = root / ('recognition-r22-'+uuid4().hex)
            path.mkdir(mode=0o777)
            return str(path)
        alloc = patch.object(tempfile, 'mkdtemp', side_effect=writable)
        alloc.start(); self.addCleanup(alloc.stop)
        self.f = legacy.PermanentFamilyTests()
        self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.f.review(1)
        self.manifest = self.f.first()
        from tests.recognition_authorization_fixture import migrate_private
        migrate_private(self.f.path, apply=True)

    def test_complete_first_look_effect_and_actual_row_evidence(self):
        with closing(sqlite3.connect(self.f.path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('BEGIN IMMEDIATE')
            before = effects._family_snapshot(conn)
            self.assertEqual(digest(self.manifest), permanent._insert_family_effects(conn, self.manifest))
            effects._verify_delta(conn, self.manifest, before)
            source = dict(authority_id=str(uuid4()), runtime_target=dict(target_id=str(uuid4())))
            evidence = effects._evidence(conn, self.manifest, dict(authority=source), dict(sequence=2))
            self.assertEqual(1, len(evidence['records']['recognition_first_look_claims']))
            self.assertEqual(digest(self.manifest), evidence['manifest_sha256'])
            conn.rollback()
            self.assertEqual(before, effects._family_snapshot(conn))

    def test_extra_effect_rejected(self):
        with closing(sqlite3.connect(self.f.path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys=ON'); conn.execute('BEGIN IMMEDIATE')
            before = effects._family_snapshot(conn)
            permanent._insert_family_effects(conn, self.manifest)
            conn.execute('INSERT INTO recognition_private_rules VALUES(?,?,?,?)', ('unrelated', 'first_look', '{}', 'a'*64))
            with self.assertRaisesRegex(ValueError, 'finalization_effect_delta_mismatch'):
                effects._verify_delta(conn, self.manifest, before)
            conn.rollback()

    def test_no_transaction_or_public_authority(self):
        with closing(sqlite3.connect(':memory:')) as conn:
            with self.assertRaisesRegex(ValueError, 'family_transaction_required'):
                permanent._insert_family_effects(conn, self.manifest)
        self.assertFalse(hasattr(effects, 'execute'))
        self.assertFalse(hasattr(effects, 'commit'))

    def test_complete_geography_effect_and_evidence(self):
        manifest = self.f.geo()
        with closing(sqlite3.connect(self.f.path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys=ON'); conn.execute('BEGIN IMMEDIATE')
            before = effects._family_snapshot(conn)
            permanent._insert_family_effects(conn, manifest)
            effects._verify_delta(conn, manifest, before)
            source = dict(authority_id=str(uuid4()), runtime_target=dict(target_id=str(uuid4())))
            evidence = effects._evidence(conn, manifest, dict(authority=source), dict(sequence=2))
            self.assertTrue(evidence['records']['recognition_geography_snapshots'])
            self.assertTrue(evidence['records']['recognition_geography_members'])
            conn.rollback()
            self.assertEqual(before, effects._family_snapshot(conn))

    def journal_data(self):
        from tests.test_recognition_runtime_decision_outcome_journal_schema import data
        from src.review.recognition import runtime_decision_outcome_journal_schema as journal
        decision,_,_,_=data()
        body=decision['authority']
        body['operation_reference']['writer_manifest_sha256']=digest(self.manifest)
        dep=body['dependencies']['snapshot'];dep['manifest_sha256']=digest(self.manifest)
        dep['sha256']=digest({k:v for k,v in dep.items() if k!='sha256'})
        body['dependencies']['snapshot_sha256']=digest(dep)
        decision=journal.validate_decision(decision)
        genesis=journal._genesis(decision)
        pending=dict(genesis,sequence=2,state='TARGET_PENDING',previous_sha256=digest(genesis))
        return decision,genesis,journal.validate_event(pending,decision=decision,previous=genesis)

    def test_target_family_and_real_witness_rollback_and_commit_together(self):
        from src.review.recognition import runtime_decision_outcome_journal_schema as journal
        from src.review.recognition import runtime_finalization_storage as storage
        decision,_,pending=self.journal_data()
        with closing(sqlite3.connect(self.f.path)) as conn:
            conn.row_factory=sqlite3.Row;conn.execute('PRAGMA foreign_keys=ON')
            # Component-level DATA setup, never a source/issuer or executor.
            for sql in journal.definitions('target').values():conn.execute(sql)
            conn.commit()
            before=effects._family_snapshot(conn)
            for commit in (False,True):
                conn.execute('BEGIN IMMEDIATE')
                permanent._insert_family_effects(conn,self.manifest,sealed_at='2099-01-01T00:00:01Z')
                effects._verify_delta(conn,self.manifest,before)
                evidence=effects._evidence(conn,self.manifest,decision,pending)
                witness=journal.validate_witness(dict(format=journal.WITNESS_FORMAT,decision=decision,pending=pending,
                    recorded_at_utc='2099-01-01T00:00:01Z',outcome='TARGET_COMMITTED',effect_evidence_sha256=digest(evidence)))
                storage._insert(conn,journal.WITNESSES,storage._witness_row(witness))
                if commit:conn.commit()
                else:conn.rollback()
                self.assertEqual(int(commit),conn.execute('SELECT count(*) FROM '+journal.WITNESSES).fetchone()[0])
                self.assertEqual(int(commit),conn.execute('SELECT count(*) FROM recognition_private_operations').fetchone()[0])
            with closing(sqlite3.connect(self.f.path)) as observer:
                observer.row_factory=sqlite3.Row
                actual=observer.execute('SELECT body_json,body_sha256 FROM '+journal.WITNESSES).fetchone()
                self.assertEqual(witness,journal.parse_witness(actual[0],expected_sha256=actual[1]))
                self.assertEqual(witness['effect_evidence_sha256'],digest(effects._evidence(observer,self.manifest,decision,pending)))
                effects._verify_witness_effect(observer,self.manifest,decision,pending,witness)
                changed=dict(witness,effect_evidence_sha256='0'*64)
                with self.assertRaisesRegex(ValueError,'finalization_committed_effect_mismatch'):
                    effects._verify_witness_effect(observer,self.manifest,decision,pending,changed)

    def test_incomplete_family_cannot_produce_effect_evidence(self):
        decision,_,pending=self.journal_data()
        with closing(sqlite3.connect(self.f.path)) as conn:
            conn.row_factory=sqlite3.Row;conn.execute('PRAGMA foreign_keys=ON');conn.execute('BEGIN IMMEDIATE')
            planned=effects._expected(self.manifest,'2099-01-01T00:00:01Z',existing_rule=False)
            # Inject a partial writer fault: rule/operation but missing claim.
            for table in effects.TABLES[:2]:
                for row in planned[table]:
                    conn.execute('INSERT INTO '+table+' VALUES('+','.join('?' for _ in row)+')',row)
            with self.assertRaises(ValueError):effects._evidence(conn,self.manifest,decision,pending)
            conn.rollback()

    def test_process_termination_before_and_after_atomic_target_commit(self):
        from src.review.recognition import runtime_decision_outcome_journal_schema as journal
        decision,_,pending=self.journal_data()
        with closing(sqlite3.connect(self.f.path)) as conn:
            for sql in journal.definitions('target').values():conn.execute(sql)
            conn.commit()
        payload=self.f.path.parent/'r22-crash-input.json'
        payload.write_text(canonical(dict(manifest=self.manifest,decision=decision,pending=pending)))
        child=r'''
import json,sqlite3,sys,time
from src.review.recognition import permanent,runtime_finalization_effects as e,runtime_finalization_storage as s,runtime_decision_outcome_journal_schema as j
from src.review.recognition.rules import digest
data=json.load(open(sys.argv[2]));m=data['manifest'];d=data['decision'];p=data['pending']
c=sqlite3.connect(sys.argv[1]);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');c.execute('BEGIN IMMEDIATE')
permanent._insert_family_effects(c,m,sealed_at='2099-01-01T00:00:01Z')
w=j.validate_witness(dict(format=j.WITNESS_FORMAT,decision=d,pending=p,recorded_at_utc='2099-01-01T00:00:01Z',outcome='TARGET_COMMITTED',effect_evidence_sha256=digest(e._evidence(c,m,d,p))))
s._insert(c,j.WITNESSES,s._witness_row(w))
if sys.argv[3]=='after':c.commit()
print('READY',flush=True)
time.sleep(30)
'''
        for stage in ('before','after'):
            log=self.f.path.parent/('r22-crash-'+stage+'.log')
            with log.open('w+b') as stream:
                process=subprocess.Popen([sys.executable,'-B','-c',child,str(self.f.path),str(payload),stage],
                    stdout=stream,stderr=stream,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                try:
                    deadline=time.monotonic()+10
                    while time.monotonic()<deadline and process.poll() is None and b'READY' not in log.read_bytes():
                        time.sleep(0.02)
                    self.assertIn(b'READY',log.read_bytes(),log.read_text(errors='replace'))
                finally:
                    if process.poll() is None:process.kill()
                    process.wait(timeout=5)
            with closing(sqlite3.connect(self.f.path)) as conn:
                conn.row_factory=sqlite3.Row
                self.assertEqual(int(stage=='after'),conn.execute('SELECT count(*) FROM '+journal.WITNESSES).fetchone()[0])
                self.assertEqual(int(stage=='after'),conn.execute('SELECT count(*) FROM recognition_private_operations').fetchone()[0])

    def test_control_failure_after_target_fact_preserves_no_retry_fence(self):
        from src.review.recognition import runtime_decision_outcome_journal_schema as journal
        from src.review.recognition import runtime_finalization_storage as storage
        decision,genesis,pending=self.journal_data()
        path=self.f.path.parent/'r22-control-failure.db'
        with closing(sqlite3.connect(path)) as control:
            control.row_factory=sqlite3.Row
            for sql in journal.definitions('control').values():control.execute(sql)
            control.execute('BEGIN IMMEDIATE')
            storage._insert(control,journal.DECISIONS,storage._decision_row(decision))
            for event in (genesis,pending):storage._insert(control,journal.HISTORY,storage._event_row(event))
            control.commit()
            with closing(sqlite3.connect(self.f.path)) as target:
                target.row_factory=sqlite3.Row;target.execute('PRAGMA foreign_keys=ON')
                for sql in journal.definitions('target').values():target.execute(sql)
                target.commit();target.execute('BEGIN IMMEDIATE')
                permanent._insert_family_effects(target,self.manifest,sealed_at='2099-01-01T00:00:01Z')
                witness=journal.validate_witness(dict(format=journal.WITNESS_FORMAT,decision=decision,pending=pending,
                    recorded_at_utc='2099-01-01T00:00:01Z',outcome='TARGET_COMMITTED',
                    effect_evidence_sha256=digest(effects._evidence(target,self.manifest,decision,pending))))
                storage._insert(target,journal.WITNESSES,storage._witness_row(witness));target.commit()
            control.execute('BEGIN IMMEDIATE')
            control.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_INSERT else sqlite3.SQLITE_OK)
            with self.assertRaises(sqlite3.DatabaseError):
                storage._insert(control,journal.HISTORY,storage._event_row(dict(pending,sequence=3)))
            control.rollback();control.set_authorizer(None)
            self.assertEqual('TARGET_PENDING',control.execute('SELECT state FROM '+journal.HISTORY+' ORDER BY sequence DESC').fetchone()[0])
            with self.assertRaises(sqlite3.IntegrityError):
                storage._insert(control,journal.DECISIONS,storage._decision_row(decision))
            self.assertFalse(journal.inspect_rows(control,'control')['retry_authorized'])
            with closing(sqlite3.connect(self.f.path)) as observer:
                observer.row_factory=sqlite3.Row
                effects._verify_witness_effect(observer,self.manifest,decision,pending,witness)
                self.assertEqual(1,observer.execute('SELECT count(*) FROM '+journal.WITNESSES).fetchone()[0])

    def test_durable_start_fence_excludes_concurrent_and_duplicate_decisions(self):
        from concurrent.futures import ThreadPoolExecutor
        from src.review.recognition import runtime_decision_outcome_journal_schema as journal
        from src.review.recognition import runtime_finalization_storage as storage
        decision,genesis,pending=self.journal_data()
        path=self.f.path.parent/'r22-fence.db'
        with closing(sqlite3.connect(path)) as conn:
            for sql in journal.definitions('control').values():conn.execute(sql)
            conn.commit()
        def start():
            with closing(sqlite3.connect(path)) as conn:
                conn.execute('PRAGMA foreign_keys=ON');conn.execute('BEGIN IMMEDIATE')
                if conn.execute('SELECT 1 FROM '+journal.DECISIONS).fetchone():
                    conn.rollback();return False
                storage._insert(conn,journal.DECISIONS,storage._decision_row(decision))
                storage._insert(conn,journal.HISTORY,storage._event_row(genesis))
                storage._insert(conn,journal.HISTORY,storage._event_row(pending))
                conn.commit();return True
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(start) for _ in range(2)]
            self.assertEqual([False,True],sorted(f.result() for f in futures))
        self.assertFalse(start())
        with closing(sqlite3.connect(path)) as conn:
            conn.row_factory=sqlite3.Row
            self.assertEqual('TARGET_PENDING',conn.execute('SELECT state FROM '+journal.HISTORY+' ORDER BY sequence DESC').fetchone()[0])
            self.assertFalse(journal.inspect_rows(conn,'control')['retry_authorized'])


class IssuerCodecTests(unittest.TestCase):
    def body(self):
        target = dict(format='recognition-runtime-operation-target-v1',
            installation_id=str(uuid4()), target_id=str(uuid4()), generation=5,
            owner_id=1, binding_sha256='a'*64, runtime_profile_sha256='b'*64,
            auth_epoch=2, mfa_epoch=3)
        return dict(format=contract.ISSUER, mandate=contract.MANDATE,
            governance_binding_sha256='c'*64, adoption_sha256='d'*64,
            appointment_sha256='e'*64, approval_sha256='f'*64,
            issuer_role=contract.ISSUER_ROLE,
            holder=dict(actor_id=1, primary_sha256='a'*64, session_sha256='b'*64),
            intent=dict(operation_id=str(uuid4()), operation_sha256='c'*64,
                writer_manifest_sha256='d'*64, write_set_sha256='e'*64,
                family='first_look', runtime_target=target, action=contract.EFFECT),
            policy=dict(format=contract.POLICY, policy_id=contract.ISSUER_ROLE,
                version=1, action=contract.EFFECT, max_grants=1,
                lifetime_policy='recognition-runtime-authority-lifetime-120s-v1'),
            issued_at_utc='2026-11-09T12:00:00Z', expires_at_utc='2026-11-09T12:02:00Z')

    def test_issuer_exact_canonical_roundtrip_is_data_only(self):
        value = self.body()
        self.assertEqual(value, contract.parse_issuer(canonical(value), expected_sha256=digest(value)))
        self.assertFalse(hasattr(contract, 'issue'))
        self.assertFalse(hasattr(contract, 'finalize'))

    def test_issuer_closed_shape_and_policy(self):
        from copy import deepcopy
        original = self.body()
        for change in ('extra', 'holder', 'issuer', 'renewal', 'bool', 'nul'):
            value = deepcopy(original)
            if change == 'extra': value['permission'] = 'writer'
            if change == 'holder': value['holder']['actor_id'] = 2
            if change == 'issuer': value['issuer_role'] = 'arbitrary-producer'
            if change == 'renewal': value['policy']['max_grants'] = 2
            if change == 'bool': value['policy']['version'] = True
            if change == 'nul': value['mandate'] += '\0'
            with self.subTest(change=change), self.assertRaises(ValueError):
                contract.validate_issuer(value)

    def test_issuer_rejects_noncanonical_duplicate_float_and_digest(self):
        value = self.body(); body = canonical(value)
        for serialized in (body+' ', body.replace('{', '{"format":"duplicate",', 1),
                           body.replace('"version":1', '"version":1.0')):
            with self.subTest(serialized=serialized[:40]), self.assertRaises(ValueError):
                contract.parse_issuer(serialized, expected_sha256=digest(value))
        with self.assertRaises(ValueError):
            contract.parse_issuer(body, expected_sha256='0'*64)


if __name__ == '__main__':
    unittest.main()
