"""Slice 2b: synthetic WSGI requests and disposable databases only."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import json
import sqlite3
import unittest
from unittest.mock import patch

from flask import Flask

from src.review.recognition import administration as a, administration_schema as s
from src.review.recognition import runtime_evidence as e, runtime_profile_schema as r
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_runtime_challenges as challenge_fixture
from tests import test_recognition_administration as f


class RuntimeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = challenge_fixture.RuntimeChallengeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture.f
        self.issued = self.fixture.issue()
        self.challenge = self.issued['challenge']
        self.binding = self.fixture.binding

    def collect(self, **changes):
        options = dict(challenge_id=self.challenge['challenge_id'],
                       challenge_sha256=self.challenge['challenge_sha256'], now=f.at(181))
        options.update(changes)
        return e._collect(self.f.path, self.f.control, **options)

    def snapshot(self):
        return self.f.path.read_bytes(), self.f.control.read_bytes()

    def runtime(self, original, *, device=60, hostname='actual-web-worker'):
        def observe(subject):
            return replace(original(subject), hostname=hostname, device=device)
        return observe

    def test_valid_distinct_runtime_identity_canonical_evidence_and_readonly(self):
        before = self.snapshot()
        original_connect, original_identity = a.connect, a.target_identity
        opened = []
        @contextmanager
        def readonly(path, **kwargs):
            self.assertFalse(kwargs.get('write', False))
            with original_connect(path, **kwargs) as conn:
                self.assertEqual(1, conn.execute('PRAGMA query_only').fetchone()[0])
                conn.execute('PRAGMA query_only=OFF')
                with self.assertRaises(sqlite3.OperationalError):
                    conn.execute('CREATE TABLE forbidden_write(x)')
                conn.execute('PRAGMA query_only=ON')
                opened.append(path)
                def authorize(action, *args):
                    if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
                        self.fail('collector attempted a write')
                    return sqlite3.SQLITE_OK
                conn.set_authorizer(authorize)
                yield conn
        with patch.object(a,'connect',side_effect=readonly), \
             patch.object(a,'target_identity',side_effect=self.runtime(original_identity)), \
             patch.object(a,'transaction',side_effect=AssertionError('administration transaction')), \
             patch.object(a,'_verify',side_effect=AssertionError('ordinary deployment verification')), \
             patch('src.review.recognition.admin_auth._cipher',side_effect=AssertionError('key read')):
            result = self.collect()
            self.assertEqual(result, self.collect())
        observation = result['observation']
        self.assertEqual('actual-web-worker',observation['hostname'])
        self.assertEqual('60',observation['target_device'])
        self.assertEqual('60',observation['control_device'])
        self.assertEqual(str(self.binding['target']['observation']['inode']),observation['target_inode'])
        self.assertEqual(self.binding['generation'],observation['source_generation'])
        self.assertEqual('REQUIRES_OPERATOR_REVIEW',observation['provenance'])
        self.assertEqual(digest(observation),result['observation_sha256'])
        self.assertEqual(canonical(result), canonical(json.loads(canonical(result))))
        self.assertNotIn(self.issued['nonce'],canonical(result))
        self.assertIn(self.f.path,opened)
        self.assertIn(self.f.control,opened)
        self.assertEqual(before,self.snapshot())
        with a.connect(self.f.control) as conn:
            for table in (r.PROFILES,r.AUTH):
                self.assertEqual(0,conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0])
        with self.assertRaisesRegex(a.AdminError,'runtime_profile_contract_not_enabled'):
            a.get_installation_control(self.f.config)

    def test_missing_expired_future_digest_and_malformed_inputs(self):
        for changes in (dict(challenge_id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),
                dict(challenge_sha256='0'*64), dict(now=f.at(780)),dict(now=f.at(179)),
                dict(challenge_id=self.challenge['challenge_id']+'\x00'),
                dict(challenge_sha256=self.challenge['challenge_sha256']+'\x00'),
                dict(challenge_sha256='x'*64)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.collect(**changes)

    def test_generation_change_rejects_unconsumed_challenge(self):
        with a.connect(self.f.control,write=True) as conn:
            body = dict(self.binding,generation=3,previous_sha256=digest(self.binding))
            conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(3,canonical(body),digest(body)))
            conn.commit()
        with self.assertRaisesRegex(a.AdminError,'runtime_challenge_stale'):
            self.collect()

    def corrupt(self, table, key, change):
        """Test-only malformed storage, with exact protections restored."""
        with a.connect(self.f.control,write=True) as conn:
            conn.execute('BEGIN')
            trigger=table+'_immutable_update'
            definition=conn.execute('SELECT sql FROM sqlite_master WHERE name=?',(trigger,)).fetchone()[0]
            conn.execute('DROP TRIGGER '+trigger)
            row=conn.execute(f'SELECT * FROM {table} ORDER BY rowid DESC LIMIT 1').fetchone()
            body=json.loads(row['body_json'])
            change(body)
            conn.execute(f'UPDATE {table} SET body_json=?,body_sha256=? WHERE {key}=?',
                         (canonical(body),digest(body),row[key]))
            conn.execute(definition)
            conn.commit()

    def test_malformed_binding_and_audit_history_fail_closed(self):
        self.corrupt('recognition_admin_bindings','generation',lambda b:b.pop('previous_sha256'))
        with self.assertRaisesRegex(a.AdminError,'history_integrity'):
            self.collect()

    def test_malformed_audit_history_fail_closed(self):
        self.corrupt('recognition_admin_audit','sequence',lambda b:b.update(previous_sha256='0'*64))
        with self.assertRaisesRegex(a.AdminError,'audit_integrity'):
            self.collect()

    def test_partial_schema_rejected(self):
        with a.connect(self.f.control,write=True) as conn:
            conn.execute('DROP TRIGGER '+r.CHALLENGES+'_immutable_update')
            conn.commit()
        with self.assertRaisesRegex(ValueError,'schema_mismatch'):
            self.collect()

    def test_malformed_constraint_data_rejected_even_with_consistent_digests(self):
        with a.connect(self.f.control,write=True) as conn:
            conn.execute('BEGIN')
            conn.execute('PRAGMA ignore_check_constraints=ON')
            for table in (r.CHALLENGES,'recognition_admin_audit'):
                conn.execute('DROP TRIGGER '+table+'_immutable_update')
            row=dict(self.challenge,operator='bad\x00operator',expires_at=self.challenge['expires_at']+1)
            row['challenge_sha256']=digest({k:v for k,v in row.items() if k!='challenge_sha256'})
            conn.execute(f'UPDATE {r.CHALLENGES} SET operator=?,expires_at=?,challenge_sha256=?',
                         (row['operator'],row['expires_at'],row['challenge_sha256']))
            audit=json.loads(conn.execute('SELECT body_json FROM recognition_admin_audit WHERE sequence=?',
                                        (row['audit_sequence'],)).fetchone()[0])
            audit['actor']=row['operator']
            audit['subject']['challenge_sha256']=row['challenge_sha256']
            conn.execute('UPDATE recognition_admin_audit SET body_json=?,body_sha256=? WHERE sequence=?',
                         (canonical(audit),digest(audit),row['audit_sequence']))
            conn.execute(r.definitions()[r.CHALLENGES+'_immutable_update'])
            conn.execute(s.definitions()['recognition_admin_audit_immutable_update'])
            conn.commit()
        with self.assertRaisesRegex(a.AdminError,'runtime_challenge_constraint_failure'):
            self.collect(challenge_sha256=row['challenge_sha256'])

    def test_challenge_nul_and_bad_source_digest_rejected(self):
        for field,value in (('nonce_sha256','a'*64+'\x00'),('source_binding_sha256','0'*64)):
            with self.subTest(field=field):
                with a.connect(self.f.control,write=True) as conn:
                    conn.execute('BEGIN')
                    trigger=r.CHALLENGES+'_immutable_update'
                    definition=r.definitions()[trigger]
                    conn.execute('DROP TRIGGER '+trigger)
                    conn.execute('PRAGMA ignore_check_constraints=ON')
                    conn.execute(f'UPDATE {r.CHALLENGES} SET {field}=?',(value,))
                    conn.execute(definition)
                    conn.commit()
                with self.assertRaises(ValueError): self.collect()
                # Restore exact original row for the next malformed case.
                with a.connect(self.f.control,write=True) as conn:
                    conn.execute('DROP TRIGGER '+trigger)
                    conn.execute(f'UPDATE {r.CHALLENGES} SET {field}=?',(self.challenge[field],))
                    conn.execute(definition)
                    conn.commit()

    def test_target_and_control_path_or_inode_mismatch(self):
        original=a.target_identity
        for selected in (self.f.path,self.f.control):
            for field,value in (('inode',999),('database','/wrong/path')):
                with self.subTest(selected=selected,field=field):
                    def observed(subject):
                        actual=original(subject)
                        return replace(actual,**{field:value}) if actual.database == str(selected) else actual
                    with patch.object(a,'target_identity',side_effect=observed),self.assertRaises(ValueError):
                        self.collect()

    def test_hostname_and_device_drift_during_collection_rejected(self):
        original=a.target_identity
        for field,value in (('hostname','changed-worker'),('device',999),('inode',999)):
            calls=[]
            def observed(subject):
                actual=original(subject)
                calls.append(1)
                return replace(actual,**{field:value}) if len(calls)>2 else actual
            with self.subTest(field=field),patch.object(a,'target_identity',side_effect=observed),self.assertRaises(ValueError):
                self.collect()

    def test_target_control_hostname_disagreement_and_nul(self):
        original=a.target_identity
        for hostname in ('other-worker','bad\x00hostname'):
            def observed(subject):
                actual=original(subject)
                return replace(actual,hostname=hostname) if actual.database==str(self.f.control) else actual
            with self.subTest(hostname=hostname),patch.object(a,'target_identity',side_effect=observed),self.assertRaises(ValueError):
                self.collect()

    def test_schema_and_installation_relationship_mismatch(self):
        with a.connect(self.f.path,write=True) as conn:
            conn.execute(f"UPDATE {s.TARGET_TABLE} SET target_id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'")
            conn.commit()
        with self.assertRaisesRegex(a.AdminError,'installation_target_mismatch'): self.collect()
        with a.connect(self.f.path,write=True) as conn:
            conn.execute('CREATE TABLE unrelated_schema_change(x)')
            conn.commit()
        with self.assertRaisesRegex(a.AdminError,'runtime_schema_mismatch'): self.collect()

    def test_concurrent_and_repeated_collection_does_not_consume_or_write(self):
        before=self.snapshot()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.collect(),range(2)))
        self.assertEqual(results[0],results[1])
        self.assertEqual(results[0],self.collect())
        self.assertEqual(before,self.snapshot())

    def test_unsigned_observations_are_lossless(self):
        original=a.target_identity
        huge=2**64-1
        binding=json.loads(canonical(self.binding))
        binding['control_identity']['inode']=huge
        binding['target']['observation']['inode']=huge
        with patch.object(a,'target_identity',side_effect=lambda subject:replace(original(subject),device=huge,inode=huge)):
            with a.connect(self.f.control) as control,a.connect(self.f.path) as target:
                observed,actual=e._observation(control,target,self.f.path,self.f.control,binding)
        self.assertEqual(str(huge),str(observed['observation']['inode']))
        self.assertEqual(str(huge),str(actual['device']))

    def test_noncanonical_device_inode_and_path_observations_rejected(self):
        original=a.target_identity
        for field,value in (('device','60\x00'),('device',True),('device',-1),
                            ('inode','42\x00'),('inode',0),('database',str(self.f.path)+'\x00')):
            with self.subTest(field=field,value=value), \
                 patch.object(a,'target_identity',side_effect=lambda subject:replace(original(subject),**{field:value})), \
                 self.assertRaises(ValueError):
                self.collect()

    def test_malformed_deployment_observations_not_ignored(self):
        for field,value in (('hostname','bad\x00host'),('device','58\x00'),('device',True),('inode',0)):
            with self.subTest(field=field):
                binding=json.loads(canonical(self.binding))
                binding['control_identity'][field]=value
                with a.connect(self.f.control) as control,a.connect(self.f.path) as target,self.assertRaises(ValueError):
                    e._observation(control,target,self.f.path,self.f.control,binding)

    def test_actual_application_hook_uses_configured_paths(self):
        from src.api import app as api
        values=dict(TESTING=True,RECOGNITION_ADMIN_CONTROL=str(self.f.control),
            RECOGNITION_RUNTIME_CHALLENGE_ID=self.challenge['challenge_id'],
            RECOGNITION_RUNTIME_CHALLENGE_SHA256=self.challenge['challenge_sha256'])
        with patch.dict(api.app.config,values),patch.object(api,'DATABASE_PATH',self.f.path), \
             patch.object(api.app.logger,'warning') as log,patch.object(e,'datetime',wraps=datetime) as clock:
            clock.now.return_value=datetime.strptime(f.at(181),'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            with api.app.test_client() as client:
                response=client.get('/slice-2b-no-such-route')
            self.assertEqual(404,response.status_code)
            record=json.loads(log.call_args.args[2])
            self.assertEqual(str(self.f.path),record['observation']['target_path'])
            self.assertEqual(str(self.f.control),record['observation']['control_path'])

    def app(self):
        app=Flask(__name__)
        app.config.update(TESTING=True,RECOGNITION_ADMIN_CONTROL=str(self.f.control),
            RECOGNITION_RUNTIME_CHALLENGE_ID=self.challenge['challenge_id'],
            RECOGNITION_RUNTIME_CHALLENGE_SHA256=self.challenge['challenge_sha256'])
        e.register_runtime_evidence(app,lambda:self.f.path)
        app.add_url_rule('/ordinary',endpoint='ordinary',view_func=lambda:'ordinary response')
        return app

    def test_wsgi_hook_once_per_pid_no_request_claims_or_response_evidence(self):
        app=self.app()
        before=self.snapshot()
        with patch.object(app.logger,'warning') as log, patch.object(e,'datetime',wraps=datetime) as clock:
            clock.now.return_value=datetime.strptime(f.at(181),'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            with app.test_client() as client:
                for _ in range(2):
                    response=client.get('/ordinary?hostname=forged&nonce=secret',headers={'X-Hostname':'forged'})
                    self.assertEqual(b'ordinary response',response.data)
            self.assertEqual(1,log.call_count)
            record=json.loads(log.call_args.args[2])
            self.assertEqual(digest(record['observation']),record['observation_sha256'])
            self.assertNotIn('forged',canonical(record))
            self.assertNotIn(self.issued['nonce'],canonical(record))
            self.assertEqual(['ordinary'],[rule.endpoint for rule in app.url_map.iter_rules() if rule.endpoint!='static'])
        self.assertEqual(before,self.snapshot())

    def test_hook_disabled_at_import_and_unarmed_no_collection(self):
        app=self.app()
        app.config.update(RECOGNITION_RUNTIME_CHALLENGE_ID=None,RECOGNITION_RUNTIME_CHALLENGE_SHA256=None)
        with patch.object(e,'_collect',side_effect=AssertionError('not armed')):
            with app.test_client() as client:self.assertEqual(200,client.get('/ordinary').status_code)

    def test_hook_errors_sanitized_no_secret_or_request_failure(self):
        app=self.app()
        app.config['RECOGNITION_RUNTIME_CHALLENGE_ID']='sensitive\x00invalid'
        with patch.object(app.logger,'warning') as log:
            with app.test_client() as client:self.assertEqual(200,client.get('/ordinary').status_code)
        line=log.call_args.args[2]
        self.assertNotIn('sensitive',line)
        self.assertNotIn(self.issued['nonce'],line)
        self.assertEqual('REJECTED',json.loads(line)['status'])

    def test_successful_collection_logging_failure_preserves_response(self):
        app=self.app()
        before=self.snapshot()
        with patch.object(e,'_collect',wraps=e._collect) as collect, \
             patch.object(app.logger,'warning',side_effect=OSError('private log sink failed')) as log, \
             patch.object(e,'datetime',wraps=datetime) as clock:
            clock.now.return_value=datetime.strptime(f.at(181),'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            with app.test_client() as client:
                for _ in range(2):
                    response=client.get('/ordinary')
                    self.assertEqual(200,response.status_code)
                    self.assertEqual(b'ordinary response',response.data)
                    self.assertEqual('text/html; charset=utf-8',response.content_type)
            self.assertEqual(1,collect.call_count)
            self.assertEqual(1,log.call_count)
            record=json.loads(log.call_args.args[2])
            self.assertNotIn('status',record)
            self.assertEqual(self.challenge['challenge_id'],record['observation']['challenge_id'])
            self.assertEqual(digest(record['observation']),record['observation_sha256'])
        self.assertEqual(before,self.snapshot())

    def test_rejected_collection_logging_failure_preserves_response(self):
        app=self.app()
        before=self.snapshot()
        # The real collector continues to reject; only emission failure is
        # contained. No fake collection result or injected rejection is used.
        with self.assertRaisesRegex(a.AdminError,'runtime_challenge_expired_or_not_yet_valid'):
            self.collect(now=f.at(780))
        with patch.object(e,'_collect',wraps=e._collect) as collect, \
             patch.object(app.logger,'warning',side_effect=OSError('private log sink failed')) as log, \
             patch.object(e,'datetime',wraps=datetime) as clock:
            clock.now.return_value=datetime.strptime(f.at(780),'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            with app.test_client() as client:
                for _ in range(2):
                    response=client.get('/ordinary')
                    self.assertEqual(200,response.status_code)
                    self.assertEqual(b'ordinary response',response.data)
                    self.assertEqual('text/html; charset=utf-8',response.content_type)
            self.assertEqual(1,collect.call_count)
            self.assertEqual(1,log.call_count)
            self.assertEqual({'status':'REJECTED','error':'runtime_evidence_collection_failed','pid':e.os.getpid()},
                             json.loads(log.call_args.args[2]))
        self.assertEqual(before,self.snapshot())


    def test_consumed_challenge_rejected(self):
        # Synthetic completed graph solely to exercise consumption detection.
        with a.connect(self.f.control,write=True) as conn:
            conn.execute('BEGIN')
            head=a._audit_head(conn)
            row=dict(format='recognition-runtime-profile-v1',installation_id=self.binding['installation_id'],
                generation=3,role='runtime',hostname='synthetic-worker',
                target_path=str(self.f.path),target_device='60',
                target_inode=str(self.binding['target']['observation']['inode']),
                control_path=str(self.f.control),control_device='60',
                control_inode=str(self.binding['control_identity']['inode']),
                target_schema_sha256=self.binding['target']['schema_sha256'],target_id=self.binding['target_id'],
                owner_id=self.binding['owner_id'],challenge_id=self.challenge['challenge_id'],observation_sha256='a'*64,
                evidence_channel=e.CHANNEL,observed_at=a.timestamp(f.at(181)),created_at=a.timestamp(f.at(182)),
                operator='fixture',reason='consumed graph test',audit_sequence=head['sequence']+1)
            row['profile_sha256']=digest(row)
            conn.execute(f"INSERT INTO {r.PROFILES} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",tuple(row.values()))
            body=dict(self.binding,generation=3,previous_sha256=digest(self.binding),runtime_profile_sha256=row['profile_sha256'])
            conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(3,canonical(body),digest(body)))
            a._audit(conn,'synthetic_profile_fixture','fixture',f.at(182),dict(profile_sha256=row['profile_sha256']))
            s.check_control(conn)
            conn.commit()
        with self.assertRaisesRegex(a.AdminError,'runtime_challenge_consumed'):
            self.collect(now=f.at(183))

    def test_hook_independent_workers_and_restart_do_not_enroll(self):
        app=self.app()
        with patch.object(app.logger,'warning') as log, patch.object(e,'datetime',wraps=datetime) as clock:
            clock.now.return_value=datetime.strptime(f.at(181),'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            for pid in (123,456,123):
                with patch.object(e.os,'getpid',return_value=pid),app.test_client() as client:
                    self.assertEqual(200,client.get('/ordinary').status_code)
            self.assertEqual(2,log.call_count)
            records=[json.loads(call.args[2]) for call in log.call_args_list]
            self.assertEqual([123,456],[record['observation']['pid'] for record in records])
        with a.connect(self.f.control) as conn:
            self.assertEqual(0,conn.execute(f'SELECT count(*) FROM {r.PROFILES}').fetchone()[0])

    def test_hook_never_emits_success_after_challenge_expires(self):
        app=self.app()
        moments=[181,780]
        with patch.object(app.logger,'warning') as log,patch.object(e,'datetime',wraps=datetime) as clock:
            clock.now.side_effect=[datetime.strptime(f.at(n),'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc) for n in moments]
            with app.test_client() as client:self.assertEqual(200,client.get('/ordinary').status_code)
        self.assertEqual('REJECTED',json.loads(log.call_args.args[2])['status'])


if __name__ == '__main__':
    unittest.main()
