"""Slice 2a: disposable local deployment ceremonies, never runtime enrollment."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
import sqlite3
import threading
import io
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, administration_schema as s
from src.review.recognition import runtime_challenges as c, runtime_profile_schema as r
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_administration as f


class RuntimeChallengeTests(unittest.TestCase):
    PROTECTED = ('recognition_admin_primary', 'recognition_admin_sessions',
                 'recognition_admin_stepups', 'recognition_admin_confirmations',
                 'recognition_approvals', 'recognition_approval_history')

    def setUp(self):
        self.f = f.AdministrationTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        # Other cases exercise a real migrated store. The preservation case
        # below instead retains live records in a synthetic v3 storage fixture.
        from src.review.recognition import approvals
        approvals.install(self.f.config, operator='fixture', reason='test', now=f.NOW)
        session, step, confirmation = self.f.confirmation()
        self.approved = approvals.create_approval(self.f.config, session, step, confirmation,
            operation_id=self.f.oid, reason='fixture approval', now=f.at(60))
        if self._testMethodName == 'test_success_exact_fields_digest_expiry_nonce_and_no_authority':
            from src.review.recognition import admin_auth
            self.session = session
            self.step = admin_auth.create_step_up(self.f.config, session,
                f.independent_code(f.at(90)), action='approve', operation_id=self.f.oid, now=f.at(90))
            self.confirmation = admin_auth.begin_operation_confirmation(self.f.config,
                session, self.step, operation_id=self.f.oid, now=f.at(90))
            # Synthetic storage fixture, NOT the migration: retain generation 1
            # and live records. Real v3 migration must continue revoking them.
            with a.connect(self.f.control, write=True) as conn:
                conn.execute('BEGIN IMMEDIATE')
                body = a._binding(conn)
                s.install_runtime_extension(conn)
                trigger = 'recognition_admin_bindings_immutable_update'
                conn.execute('DROP TRIGGER '+trigger)
                body = dict(body, format=r.V3, runtime_profile_sha256=None)
                conn.execute('UPDATE recognition_admin_bindings SET body_json=?,body_sha256=? WHERE generation=1',
                             (canonical(body), digest(body)))
                conn.execute(s.definitions()[trigger])
                s.check_control(conn)
                conn.commit()
        else:
            a.migrate_runtime_profile_contract(self.f.config, expected_generation=1,
                operator='fixture', reason='schema only', now=f.at(120))
        with a.connect(self.f.control) as conn:
            self.binding = json.loads(conn.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
        self.options = dict(expected_generation=self.binding['generation'], installation_id=self.binding['installation_id'],
            target_id=self.binding['target_id'], owner_id=self.binding['owner_id'],
            source_binding_sha256=digest(self.binding), operator='trusted-local-operator',
            reason='prepare independent observation', now=f.at(180))

    def issue(self, **changes):
        return c.issue_challenge(self.f.config, **dict(self.options, **changes))

    def snapshot(self):
        with a.connect(self.f.control) as conn:
            return '\n'.join(conn.iterdump())

    def protected_snapshot(self):
        with a.connect(self.f.control) as conn:
            return {table: [tuple(row) for row in conn.execute(f'SELECT * FROM {table} ORDER BY rowid')]
                    for table in self.PROTECTED}

    def test_success_exact_fields_digest_expiry_nonce_and_no_authority(self):
        from src.review.recognition import admin_auth, approvals
        before = self.protected_snapshot()
        for table, rows in before.items():
            self.assertTrue(rows, table+' must be populated')
        with a.connect(self.f.control) as conn, a.connect(self.f.path) as target_conn:
            primary = admin_auth._primary(conn, target_conn, self.binding, self.f.primary, f.at(180))
            session, _ = admin_auth._session(conn, target_conn, self.binding, self.session, f.at(180))
            admin_auth._step(conn, target_conn, self.binding, session, self.step, 'approve', self.f.oid, f.at(180))
            self.assertFalse(primary['revoked'])
            self.assertFalse(session['revoked'])
            confirmation = conn.execute('SELECT * FROM recognition_admin_confirmations WHERE token_hash=?',
                                        (a.token_hash(self.confirmation),)).fetchone()
            self.assertFalse(confirmation['used'])
            self.assertEqual(self.binding['generation'], confirmation['generation'])
            self.assertGreater(confirmation['expires'], a.timestamp(f.at(180)))
            self.assertEqual('APPROVED', approvals._read(conn, self.approved['approval']['approval_id'])['state'])
        target = self.f.path.read_bytes()
        original_connect = a.connect
        denied = []
        @contextmanager
        def guarded_connect(path, **kwargs):
            with original_connect(path, **kwargs) as conn:
                if path == self.f.control:
                    def authorize(action, table, column, database, source):
                        if table in self.PROTECTED and action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
                            denied.append((action, table))
                            return sqlite3.SQLITE_DENY
                        return sqlite3.SQLITE_OK
                    conn.set_authorizer(authorize)
                    # Prove the guard rejects even no-op UPDATE/DELETE requests.
                    for table in self.PROTECTED:
                        column = conn.execute(f'PRAGMA table_info({table})').fetchone()['name']
                        for sql in (f'UPDATE {table} SET {column}={column} WHERE 0', f'DELETE FROM {table} WHERE 0'):
                            with self.assertRaises(sqlite3.DatabaseError):
                                conn.execute(sql)
                    denied.clear()
                yield conn
        with patch.object(a, 'connect', side_effect=guarded_connect), \
             patch('src.review.recognition.admin_auth._cipher', side_effect=AssertionError('key read')):
            result = self.issue()
        self.assertEqual([], denied)
        row = result['challenge']
        self.assertEqual(set(row), {'challenge_id','format','installation_id','source_generation',
            'source_binding_sha256','target_id','owner_id','role','nonce_sha256','issued_at',
            'expires_at','operator','reason','audit_sequence','challenge_sha256'})
        self.assertEqual(digest({k:v for k,v in row.items() if k != 'challenge_sha256'}), row['challenge_sha256'])
        self.assertEqual(hashlib.sha256(result['nonce'].encode()).hexdigest(), row['nonce_sha256'])
        self.assertEqual(600, row['expires_at'] - row['issued_at'])
        self.assertEqual(self.binding['generation'], row['source_generation'])
        self.assertEqual('runtime', row['role'])
        for key in ('installation_id','target_id','owner_id','source_binding_sha256','operator','reason'):
            self.assertEqual(self.options[key], row[key])
        self.assertNotIn(result['nonce'], self.snapshot())
        self.assertNotIn(result['nonce'].encode(), self.f.control.read_bytes())
        with a.connect(self.f.control) as conn:
            self.assertEqual(dict(conn.execute(f'SELECT * FROM {r.CHALLENGES}').fetchone()), row)
            self.assertEqual(self.binding['generation'], conn.execute('SELECT MAX(generation) FROM recognition_admin_bindings').fetchone()[0])
            for table in (r.PROFILES,r.AUTH):
                self.assertEqual(0,conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0])
            head = a._audit_head(conn)
            self.assertEqual(row['audit_sequence'],head['sequence'])
            self.assertEqual('runtime_enrollment_challenge_issued',json.loads(head['body_json'])['action'])
            s.check_control(conn)
        self.assertEqual(before, self.protected_snapshot())
        self.assertEqual(target,self.f.path.read_bytes())
        with self.assertRaisesRegex(a.AdminError,'runtime_profile_contract_not_enabled'):
            a.get_installation_control(self.f.config)

    def test_scope_and_input_mismatches_do_not_mutate(self):
        for changes in (dict(expected_generation=1),dict(expected_generation=True),
                dict(installation_id='bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee'),
                dict(target_id='bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee'),dict(owner_id=2),
                dict(source_binding_sha256='a'*64),dict(operator=''),dict(reason=''),
                dict(operator='x\x00y'),dict(source_binding_sha256='a'*64+'\x00')):
            with self.subTest(changes=changes):
                before = self.snapshot()
                with self.assertRaises(ValueError):
                    self.issue(**changes)
                self.assertEqual(before,self.snapshot())

    def test_each_deployment_identity_mismatch_is_denied(self):
        original = a.target_identity
        for field,value in (('hostname','other-host'),('device',999),('inode',999),('database','/wrong/path')):
            with self.subTest(field=field):
                def altered(subject):
                    return replace(original(subject), **{field:value})
                with patch.object(a,'target_identity',side_effect=altered), self.assertRaisesRegex(a.AdminError,'control_identity_mismatch'):
                    self.issue()
        with patch.object(a,'observe_target',return_value={}), self.assertRaisesRegex(a.AdminError,'target_identity_or_schema_mismatch'):
            self.issue()

    def test_wrong_actual_owner_and_metadata_denied(self):
        # Changes to data do not change sqlite_master fingerprint.
        with a.connect(self.f.path,write=True) as target:
            target.execute("UPDATE community_reviewers SET role='reviewer' WHERE id=1")
            target.commit()
        with self.assertRaisesRegex(a.AdminError,'verified_project_owner_required'):
            self.issue()

    def test_target_metadata_mismatches_fail_closed(self):
        for column,value in (('installation_id','bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee'),
                             ('target_id','bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee'),('owner_id',2)):
            with self.subTest(column=column):
                with a.connect(self.f.path,write=True) as target:
                    target.execute(f'UPDATE {s.TARGET_TABLE} SET {column}=?',(value,))
                    target.commit()
                with self.assertRaisesRegex(a.AdminError,'installation_target_mismatch'):
                    self.issue()
                with a.connect(self.f.path,write=True) as target:
                    target.execute(f'UPDATE {s.TARGET_TABLE} SET {column}=?',(self.binding[column],))
                    target.commit()

    def test_generation_advance_rejects_stale_issuance_preserves_old_challenge(self):
        issued = self.issue()['challenge']
        with a.connect(self.f.control,write=True) as conn:
            new = dict(self.binding,generation=3,previous_sha256=digest(self.binding))
            conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(3,canonical(new),digest(new)))
            conn.commit()
        with self.assertRaisesRegex(a.AdminError,'generation_conflict'):
            self.issue()
        with a.connect(self.f.control) as conn:
            self.assertEqual(issued,dict(conn.execute(f'SELECT * FROM {r.CHALLENGES}').fetchone()))
            s.check_control(conn)

    def test_cli_requires_explicit_confirmation_and_outputs_nonce_once(self):
        from scripts.active.manage_recognition_administration import main
        args = ['issue-runtime-challenge','--target',str(self.f.path),'--control',str(self.f.control),
                '--key-file',str(self.f.key_file),'--operator','fixture','--reason','test']
        with patch('sys.stderr',new_callable=io.StringIO),self.assertRaises(SystemExit):
            main(args)
        args += ['--expected-generation','2','--installation-id',self.binding['installation_id'],
                 '--target-id',self.binding['target_id'],'--owner-id','1',
                 '--source-binding-sha256',digest(self.binding),'--confirm-issue-runtime-challenge']
        with patch('sys.stdout',new_callable=io.StringIO) as output,patch.object(c,'issue_challenge',return_value={'nonce':'one-time'}) as issue:
            main(args)
        self.assertEqual({'nonce':'one-time'},json.loads(output.getvalue()))
        self.assertEqual('fixture',issue.call_args.kwargs['operator'])

    def test_non_not_activated_denied(self):
        with patch.object(c,'_deployment_binding',return_value=dict(self.binding,production_state='ACTIVATED')):
            with self.assertRaises(ValueError):
                self.issue(source_binding_sha256=digest(dict(self.binding,production_state='ACTIVATED')))

    def test_readiness_active_denied(self):
        # Existing readiness state is independently checked, not enabled here.
        from src.review.recognition import local_readiness
        original = a.connect
        from contextlib import contextmanager
        with patch.object(local_readiness,'_state',return_value={'state':'ACTIVATED'}):
            # Force the optional branch via a connection proxy.
            class Proxy:
                def __init__(self,conn): self.conn=conn
                def __getattr__(self,name): return getattr(self.conn,name)
                def execute(self,sql,*args):
                    if sql == "SELECT 1 FROM sqlite_master WHERE name='recognition_local_activation'":
                        return self.conn.execute('SELECT 1')
                    return self.conn.execute(sql,*args)
            @contextmanager
            def proxied(path,**kwargs):
                with original(path,**kwargs) as conn:
                    yield Proxy(conn) if path == self.f.control else conn
            with patch.object(a,'connect',side_effect=proxied),self.assertRaisesRegex(a.AdminError,'requires_not_activated'):
                self.issue()

    def test_malformed_binding_and_stale_history_denied(self):
        for body in (dict(self.binding,previous_sha256='0'*64),dict(self.binding,generation=3)):
            with a.connect(self.f.control,write=True) as conn:
                conn.execute('BEGIN')
                # Only corrupt test storage after explicitly removing protection.
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='recognition_admin_bindings'").fetchall():
                    conn.execute('DROP TRIGGER '+row[0])
                conn.execute('UPDATE recognition_admin_bindings SET body_json=?,body_sha256=? WHERE generation=2', (canonical(body),digest(body)))
                with self.assertRaises(ValueError):
                    c._deployment_binding(conn)
                conn.rollback()

    def test_missing_genesis_previous_digest_rejected_at_issuance_boundary(self):
        with a.connect(self.f.control, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            trigger = 'recognition_admin_bindings_immutable_update'
            conn.execute('DROP TRIGGER '+trigger)
            previous = None
            rows = conn.execute('SELECT generation,body_json FROM recognition_admin_bindings ORDER BY generation').fetchall()
            for record in rows:
                body = json.loads(record['body_json'])
                if record['generation'] == 1:
                    del body['previous_sha256']
                else:
                    body['previous_sha256'] = previous
                previous = digest(body)
                conn.execute('UPDATE recognition_admin_bindings SET body_json=?,body_sha256=? WHERE generation=?',
                             (canonical(body), previous, record['generation']))
            conn.execute(s.definitions()[trigger])
            # Keep hashes, links, schema and current scope otherwise consistent;
            # rejection must come from explicit genesis history validation.
            s.check_control(conn)
            conn.commit()
        before = self.snapshot()
        with self.assertRaisesRegex(a.AdminError, 'installation_history_integrity_failure'):
            self.issue(source_binding_sha256=previous)
        self.assertEqual(before, self.snapshot())

    def test_concurrent_issuance_serializes_without_advancing_generation(self):
        barrier = threading.Barrier(2)
        def issue(_):
            barrier.wait()
            return self.issue()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(issue,range(2)))
        self.assertNotEqual(results[0]['nonce'],results[1]['nonce'])
        self.assertNotEqual(results[0]['challenge']['challenge_id'],results[1]['challenge']['challenge_id'])
        self.assertEqual(1,abs(results[0]['challenge']['audit_sequence']-results[1]['challenge']['audit_sequence']))
        with a.connect(self.f.control) as conn:
            s.check_control(conn)
            a._audit_head(conn)
            self.assertEqual(2,conn.execute('SELECT MAX(generation) FROM recognition_admin_bindings').fetchone()[0])

    def test_issued_challenge_immutable(self):
        self.issue()
        with a.connect(self.f.control,write=True) as conn:
            for statement in (f"UPDATE {r.CHALLENGES} SET reason='changed'",f'DELETE FROM {r.CHALLENGES}',
                              f'INSERT OR REPLACE INTO {r.CHALLENGES} SELECT * FROM {r.CHALLENGES}'):
                with self.assertRaisesRegex(sqlite3.IntegrityError,'immutable'):
                    conn.execute(statement)

    def test_rollback_after_challenge_audit_and_final_validation(self):
        for stage in ('audit_before','audit_after','validation','precommit','commit'):
            with self.subTest(stage=stage):
                before=self.snapshot()
                original=a._audit
                def fail_audit(*args,**kwargs):
                    if stage != 'audit_before': original(*args,**kwargs)
                    raise RuntimeError('injected')
                if stage.startswith('audit'):
                    context=patch.object(a,'_audit',side_effect=fail_audit)
                elif stage == 'validation':
                    original_check=s.check_control
                    calls=[]
                    def fail_check(conn):
                        original_check(conn)
                        calls.append(1)
                        if len(calls)==2: raise RuntimeError('injected')
                    context=patch.object(s,'check_control',side_effect=fail_check)
                elif stage == 'precommit':
                    context=patch.object(a,'_verify',side_effect=[None,RuntimeError('injected')])
                else:
                    from contextlib import contextmanager
                    original_connect=a.connect
                    class Proxy:
                        def __init__(self,conn): self.conn=conn
                        def __getattr__(self,name): return getattr(self.conn,name)
                        def commit(self): raise RuntimeError('injected')
                    @contextmanager
                    def connected(path,**kwargs):
                        with original_connect(path,**kwargs) as conn:
                            yield Proxy(conn) if path == self.f.control else conn
                    original_identity=a.target_identity
                    @contextmanager
                    def fail_commit():
                        with patch.object(a,'connect',side_effect=connected), patch.object(a,'target_identity',
                                side_effect=lambda subject: original_identity(subject.conn if isinstance(subject,Proxy) else subject)):
                            yield
                    context=fail_commit()
                with context,self.assertRaisesRegex(RuntimeError,'injected'):
                    self.issue()
                self.assertEqual(before,self.snapshot())


if __name__ == '__main__':
    unittest.main()
