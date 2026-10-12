"""Synthetic disposable fixtures only; never use retained historical databases."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts.active import rehearse_explorer_issuance as rehearsal
from src.review.recognition.backfill import source_plan, dry_run
from src.review.recognition.rules import RULE_KEY, canonical, digest
from src.review.recognition.schema import connection, migrate


class IssuanceRehearsalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / 'source.db'
        self.manifest = root / 'issuance.json'
        self.output = root / 'rehearsals'
        self.target = self.output / 'disposable-test.db'
        override = patch.object(rehearsal, 'OUTPUT_ROOT', self.output)
        override.start()
        self.addCleanup(override.stop)
        conn = sqlite3.connect(self.source)
        try:
            conn.executescript('''
                CREATE TABLE community_reviewers(id INTEGER PRIMARY KEY,reviewer_key TEXT);
                CREATE TABLE physical_stops(id INTEGER PRIMARY KEY);
                CREATE TABLE stop_review_assignments(id INTEGER PRIMARY KEY,stop_id INTEGER,
                  reviewer_id INTEGER,status TEXT,completed_at TEXT);
                CREATE TABLE stop_observations(id INTEGER PRIMARY KEY,assignment_id INTEGER,
                  reviewer_id INTEGER,physical_stop_id INTEGER,source TEXT);
            ''')
            conn.executemany('INSERT INTO community_reviewers VALUES(?,?)',
                             [(i, 'synthetic-key-' + str(i)) for i in (158, 160, 169, 170)])
            for i in range(142, 211):
                owner = 169 if i < 184 else 158 if i < 191 else 160 if i < 196 else 170
                conn.execute('INSERT INTO physical_stops VALUES(?)', (i,))
                conn.execute('INSERT INTO stop_review_assignments VALUES(?,?,?,?,?)',
                             (i, i, owner, 'completed' if i <= 196 else 'assigned',
                              f'2026-09-29T00:{(i-142)//60:02d}:{(i-142)%60:02d}Z' if i <= 196 else None))
                if i <= 196:
                    conn.execute("INSERT INTO stop_observations VALUES(?,?,?,?,'community_review')", (i,i,owner,i))
            conn.commit()
        finally:
            conn.close()
        migrate(self.source, apply=True)
        # Fixture data only: no capture service or production command is executed.
        with connection(self.source, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            plan = source_plan(conn, RULE_KEY, after_assignment=141, through_assignment=210)
            capture = dict(plan, candidate_basis='existing_immutable_ledger_only', candidates=[])
            for seq, fact in enumerate(plan['qualified'], 1):
                conn.execute('''INSERT INTO recognition_completions
                  (assignment_id,observation_id,reviewer_id,physical_stop_id,completed_at_utc,
                   original_completed_at,timestamp_provenance,qualification_rule_key,origin,recorded_at_utc,ledger_sequence)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                   (*fact.values(), RULE_KEY, 'backfill', '2026-10-02T00:00:00Z', seq))
                conn.execute("INSERT INTO recognition_jobs(assignment_id,rule_key,updated_at_utc) VALUES(?,?,?)",
                             (fact['assignment_id'],RULE_KEY,'2026-10-02T00:00:00Z'))
            conn.execute('INSERT INTO recognition_runs VALUES(?,?,?,?,?,?,?,?)',
                         (digest(capture),'backfill','2026-10-02T00:00:00Z','2026-10-02T00:00:00Z',
                          canonical(capture),digest(capture),'complete','{}'))
            conn.commit()
        manifest = dry_run(self.source, RULE_KEY, after_assignment=141, through_assignment=210)
        self.manifest.write_text(canonical(manifest), encoding='utf-8')
        self.args = dict(source_sha256=rehearsal.file_hash(self.source),
                         manifest_sha256=rehearsal.file_hash(self.manifest), test_only=True)

    def run_rehearsal(self, **kwargs):
        return rehearsal.rehearse(self.source,self.manifest,self.target,**dict(self.args,**kwargs))

    def test_exact_awards_witnesses_api_retry_and_source_preservation(self):
        before = self.source.read_bytes()
        with patch.object(rehearsal, 'lease_jobs', wraps=rehearsal.lease_jobs) as leases, \
             patch.object(rehearsal, 'check_award_integrity', wraps=rehearsal.check_award_integrity) as integrity, \
             patch('src.review.recognition.qualification.capture', side_effect=AssertionError('capture forbidden')), \
             patch('src.review.recognition.backfill.capture_batch', side_effect=AssertionError('capture forbidden')):
            result = self.run_rehearsal()
        self.assertEqual((4,35,30,55),(result['awards'],result['witness_rows'],result['unique_witness_assignments'],result['done_jobs']))
        self.assertTrue(result['retry_unchanged'])
        self.assertEqual(4,result['api']['authenticated_awards'])
        self.assertGreaterEqual(integrity.call_count,8)
        self.assertTrue(all(not call.kwargs['gate'].capture and call.kwargs['gate'].issuance for call in leases.call_args_list))
        self.assertEqual(before,self.source.read_bytes())

    def test_hash_and_explicit_mode_fail_before_copy_or_leases(self):
        for change,reason in [({'source_sha256':'0'*64},'source_hash'),
                              ({'manifest_sha256':'0'*64},'manifest_hash'),
                              ({'test_only':False},'explicit_test')]:
            with self.subTest(change=change), patch.object(rehearsal,'lease_jobs',side_effect=AssertionError('lease')):
                with self.assertRaisesRegex(ValueError,reason):self.run_rehearsal(**change)
            self.assertFalse(self.target.exists())

    def test_alias_existing_and_application_targets_rejected(self):
        with self.assertRaisesRegex(ValueError,'source_target_alias'):
            rehearsal.rehearse(self.source,self.manifest,self.source,**self.args)
        with self.assertRaisesRegex(ValueError,'reserved_disposable'):
            rehearsal.rehearse(self.source,self.manifest,self.source.parent/'application.db',**self.args)
        self.output.mkdir()
        self.target.write_bytes(b'do not overwrite')
        with self.assertRaisesRegex(ValueError,'destination_exists'):self.run_rehearsal()
        self.assertEqual(b'do not overwrite',self.target.read_bytes())

    def test_changed_candidate_evidence_rejected_before_copy(self):
        value=json.loads(self.manifest.read_text())
        value['candidates'][0]['earned_at_utc']='2026-09-30T00:00:00Z'
        self.manifest.write_text(canonical(value))
        with patch.object(rehearsal,'lease_jobs',side_effect=AssertionError('lease')):
            with self.assertRaisesRegex(ValueError,'candidate_set_mismatch'):
                self.run_rehearsal(manifest_sha256=rehearsal.file_hash(self.manifest))
        self.assertFalse(self.target.exists())

    def test_production_wrapper_and_binding_are_not_used(self):
        from scripts.active import issue_historical_explorer as production
        with patch.object(production,'issue',side_effect=AssertionError('production issuance')), \
             patch.object(production,'target_binding',side_effect=AssertionError('production binding')):
            self.run_rehearsal()
        text=Path(rehearsal.__file__).read_text()
        self.assertNotIn('issue_historical_explorer',text)
        self.assertNotIn('BINDING_PATH',text)

    def test_later_finalization_failure_rolls_back_whole_rehearsal(self):
        real=rehearsal.finalize_job
        def fail(conn,*args,**kwargs):
            result=real(conn,*args,**kwargs)
            raise ValueError('injected after award writes')
        with patch.object(rehearsal,'finalize_job',side_effect=fail):
            with self.assertRaisesRegex(ValueError,'injected'):self.run_rehearsal()
        self.assertEqual(self.source.read_bytes(),self.target.read_bytes())

    def test_schema_change_on_copy_prevents_leasing(self):
        real=rehearsal.evaluate
        def mutate(database,manifest):
            result=real(database,manifest)
            if database==self.target:
                with connection(database,write=True) as conn:
                    conn.execute("CREATE TRIGGER extra AFTER UPDATE ON recognition_jobs BEGIN SELECT 1; END")
                    conn.commit()
            return result
        with patch.object(rehearsal,'evaluate',side_effect=mutate), \
             patch.object(rehearsal,'lease_jobs',side_effect=AssertionError('lease')):
            with self.assertRaisesRegex(ValueError,'unexpected_capture_trigger'):self.run_rehearsal()


if __name__=='__main__':
    unittest.main()
