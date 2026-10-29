"""Slice 1 only: synthetic rows below exist solely to exercise storage guards."""

from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, administration_schema as s
from src.review.recognition import runtime_profile_schema as r
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_administration as fixture


INSTALL = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'
TARGET = 'bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee'
CHALLENGE = 'cccccccc-bbbb-4ccc-8ddd-eeeeeeeeeeee'


class RuntimeProfileSchemaTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.conn = sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.execute('BEGIN')
        s.install_control(self.conn)
        self.old = dict(format='recognition-local-control-v2', generation=1, installation_id=INSTALL,
            target_id=TARGET, owner_id=1, production_state='NOT_ACTIVATED', previous_sha256=None,
            at_utc=fixture.NOW, control_identity=dict(hostname='deployment', database=str(self.root/'control.db'), device=1, inode=43),
            target=dict(observation=dict(hostname='deployment', database=str(self.root/'target.db'), device=1, inode=42), schema_sha256='a'*64))
        self.binding(self.old)
        self.conn.commit()
        self.conn.execute('BEGIN')
        s.install_runtime_extension(self.conn)
        self.conn.commit()

    def binding(self, body):
        self.conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)', (body['generation'], canonical(body), digest(body)))

    def insert(self, table, row):
        self.conn.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", tuple(row.values()))

    def audit(self, row, key):
        moment = row.get('issued_at',row.get('created_at'))
        # Invalid timestamp tests must reach the table constraint, not this fixture formatter.
        valid = type(moment) is int and 0 <= moment <= r.MAX_TIME
        at = datetime.fromtimestamp(moment if valid else 1000, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        body = dict(subject={key:row[key]}, actor=row['operator'], action='schema-constraint-fixture', at_utc=at, previous_sha256=None)
        self.conn.execute('INSERT INTO recognition_admin_audit VALUES(?,?,?)', (row['audit_sequence'], canonical(body), digest(body)))

    def challenge(self, **changes):
        row = dict(challenge_id=CHALLENGE, format='recognition-runtime-enrollment-challenge-v1', installation_id=INSTALL,
            source_generation=1, source_binding_sha256=digest(self.old), target_id=TARGET, owner_id=1, role='runtime',
            nonce_sha256='b'*64, issued_at=1000, expires_at=1600, operator='fixture', reason='schema constraint test', audit_sequence=1)
        row.update(changes)
        row.setdefault('challenge_sha256', digest(row))
        self.audit(row, 'challenge_sha256')
        self.insert(r.CHALLENGES, row)
        return row

    def profile(self, complete=True, challenge_changes=None, **changes):
        self.challenge(**(challenge_changes or {}))
        row = dict(format='recognition-runtime-profile-v1', installation_id=INSTALL, generation=2, role='runtime', hostname='worker',
            target_path=str(self.root/'target.db'), target_device='18446744073709551615', target_inode=str(self.old['target']['observation']['inode']),
            control_path=str(self.root/'control.db'), control_device='18446744073709551615', control_inode=str(self.old['control_identity']['inode']),
            target_schema_sha256='a'*64, target_id=TARGET, owner_id=1, challenge_id=CHALLENGE, observation_sha256='c'*64,
            evidence_channel='operator-reviewed-private-wsgi-log-v1', observed_at=1001, created_at=1002,
            operator='fixture', reason='schema constraint test', audit_sequence=2)
        row.update(changes)
        row.setdefault('profile_sha256', digest(row))
        self.audit(row, 'profile_sha256')
        self.insert(r.PROFILES, row)
        if complete:
            self.binding(dict(self.old, format=r.V3, generation=2, previous_sha256=digest(self.old), runtime_profile_sha256=row['profile_sha256']))
        return row

    @contextmanager
    def rejected(self):
        self.conn.execute('SAVEPOINT rejected')
        try:
            with self.assertRaises((sqlite3.IntegrityError, ValueError)):
                yield
        finally:
            self.conn.execute('ROLLBACK TO rejected')
            self.conn.execute('RELEASE rejected')

    def test_exact_schema_and_idempotent_explicit_installer(self):
        s.check_control(self.conn)
        self.conn.execute('BEGIN')
        before = self.conn.execute('SELECT name,sql FROM sqlite_master').fetchall()
        s.install_runtime_extension(self.conn)
        self.assertEqual(before, self.conn.execute('SELECT name,sql FROM sqlite_master').fetchall())
        self.conn.rollback()
        self.assertEqual(0, self.conn.execute(f'SELECT count(*) FROM {r.PROFILES}').fetchone()[0])

    def test_installer_requires_transaction_and_foreign_keys(self):
        with self.assertRaisesRegex(ValueError,'transaction_required'):
            s.install_runtime_extension(self.conn)
        self.conn.execute('PRAGMA foreign_keys=OFF')
        self.conn.execute('BEGIN')
        with self.assertRaisesRegex(ValueError,'transaction_required'):
            s.install_runtime_extension(self.conn)
        self.conn.rollback()

    def test_partial_and_malformed_extension_rejected_not_repaired(self):
        for statement in (f'DROP TABLE {r.AUTH}', f'DROP TRIGGER {r.PROFILES}_immutable_update'):
            self.conn.execute('SAVEPOINT malformed')
            self.conn.execute(statement)
            with self.assertRaises(ValueError):
                s.check_control(self.conn)
            with self.assertRaises(ValueError):
                s.install_runtime_extension(self.conn)
            self.conn.execute('ROLLBACK TO malformed')
            self.conn.execute('RELEASE malformed')

    def test_v3_binding_without_extension_cannot_be_interpreted_as_v2(self):
        self.binding(dict(self.old,format=r.V3,generation=2,runtime_profile_sha256=None))
        for name, sql in r.definitions().items():
            if sql.startswith('CREATE TRIGGER'):
                self.conn.execute(f'DROP TRIGGER {name}')
        for name in (r.AUTH,r.PROFILES,r.CHALLENGES):
            self.conn.execute(f'DROP TABLE {name}')
        with self.assertRaisesRegex(ValueError,'schema_mismatch'):
            s.check_control(self.conn)

    def test_low_level_migration_savepoint_rolls_back_when_caught(self):
        with sqlite3.connect(':memory:') as conn:
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('BEGIN')
            s.install_control(conn)
            conn.commit()
            conn.execute('BEGIN')
            original = s.check_control
            calls = 0
            def checked(c):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise ValueError('injected after DDL')
                original(c)
            with patch.object(s, 'check_control', side_effect=checked), self.assertRaises(ValueError):
                s.install_runtime_extension(conn)
            conn.commit()
            s.check_control(conn)
            self.assertFalse(conn.execute("SELECT 1 FROM sqlite_master WHERE name LIKE 'recognition_runtime_%'").fetchone())

    def test_malformed_uuid_sha_timestamp_and_role_challenge(self):
        cases = [('installation_id', v) for v in ('no', INSTALL.upper(), 'a'*36)]
        cases += [('nonce_sha256', v) for v in ('a'*63, 'A'*64, 'z'*64)]
        cases += [('issued_at', v) for v in (-1, 1000.5, 'invalid', r.MAX_TIME+1)]
        cases += [('expires_at',1601), ('role','deployment'), ('owner_id',0), ('source_generation',2), ('source_binding_sha256','d'*64), ('target_id',INSTALL)]
        for key, value in cases:
            with self.subTest(key=key, value=value), self.rejected():
                self.challenge(**{key:value})

    def test_profile_field_constraints(self):
        cases = [('role','deployment'), ('installation_id',TARGET), ('target_id',INSTALL), ('owner_id',2), ('generation',1), ('generation',3),
            ('hostname',''), ('target_schema_sha256','d'*64), ('profile_sha256','A'*64), ('challenge_id',INSTALL),
            ('evidence_channel','browser'), ('observed_at',999), ('created_at',1600), ('created_at',1601), ('created_at',1000), ('created_at',1.5)]
        for key in ('target_device','control_device','target_inode','control_inode'):
            cases += [(key,v) for v in ('-1','01','1.0','1e3','+2','', ' 2')]
        cases += [('target_inode','0'), ('control_inode','0')]
        for key in ('target_path','control_path'):
            cases += [(key,v) for v in ('relative.db', '/tmp/../target.db', '/tmp//target.db', str(self.root/'other.db'))]
        for key, value in cases:
            with self.subTest(key=key,value=value), self.rejected():
                self.profile(**{key:value})

    def test_sql_constraints_reject_embedded_and_trailing_nuls(self):
        for suffix in ('\0', '\0suffix'):
            with self.subTest(kind='sha',suffix=suffix),self.rejected():
                self.challenge(nonce_sha256='b'*64+suffix)
            with self.subTest(kind='uuid',suffix=suffix),self.rejected():
                self.challenge(challenge_id=CHALLENGE+suffix)
            for field in ('target_device','control_device'):
                with self.subTest(kind=field,suffix=suffix),self.rejected():
                    self.profile(**{field:'60'+suffix})
        for value in ('\0'+'b'*64, 'b'*32+'\0'+'b'*32):
            with self.subTest(kind='sha',value=value),self.rejected():
                self.challenge(nonce_sha256=value)
        for value in ('\0'+CHALLENGE,CHALLENGE[:18]+'\0'+CHALLENGE[18:]):
            with self.subTest(kind='uuid',value=value),self.rejected():
                self.challenge(challenge_id=value)
        for value in ('\0'+'60','6\0'+'0'):
            with self.subTest(kind='decimal',value=value),self.rejected():
                self.profile(target_device=value)

    def test_row_validation_rejects_complete_nul_graph_despite_bypassed_checks(self):
        # Model records accepted by the old CHECK expressions. Only the private
        # in-memory fixture disables checks; restore them before check_control.
        cases = [dict(challenge_changes=dict(nonce_sha256='b'*64+'\0suffix'),target_device='60\0suffix'),
                 dict(challenge_changes=dict(nonce_sha256='b'*64+'\0')),
                 dict(target_device='60\0'),dict(control_device='6\0'+'0'),
                 dict(observation_sha256='c'*32+'\0'+'c'*32)]
        for changes in cases:
            with self.subTest(changes=changes):
                self.conn.execute('SAVEPOINT malformed_graph')
                try:
                    self.conn.execute('PRAGMA ignore_check_constraints=ON')
                    self.profile(**changes)
                    self.conn.execute('PRAGMA ignore_check_constraints=OFF')
                    with self.assertRaisesRegex(ValueError,'runtime_profile_(sha|decimal)_format_mismatch'):
                        s.check_control(self.conn)
                finally:
                    self.conn.execute('PRAGMA ignore_check_constraints=OFF')
                    self.conn.execute('ROLLBACK TO malformed_graph')
                    self.conn.execute('RELEASE malformed_graph')

    def test_nonnull_profile_does_not_admit_execution_or_writer(self):
        from src.review.recognition import production_operations, local_execution, writer_boundary
        self.profile()
        self.conn.commit()
        context = object.__new__(production_operations.ProductionOperationContext)
        config = a.LocalAdministration(self.root/'target.db',self.root/'control.db',self.root/'key')
        production_operations._contexts[context] = dict(config=config,operation_id='synthetic',consumed=False)
        self.addCleanup(production_operations._contexts.pop,context,None)
        @contextmanager
        def memory_connection(*_args, **_kwargs):
            yield self.conn
        with patch.object(a,'connect',side_effect=memory_connection), \
             patch.object(local_execution.approvals.schema,'check'), \
             patch.object(a,'_audit_head'), \
             patch.object(local_execution.permanent,'finalize',side_effect=AssertionError('writer invoked')):
            result = local_execution.execute_approved_operation(context,'no-session','no-approval',now=fixture.NOW)
            self.assertEqual('runtime_profile_contract_not_enabled',result.reason)
        # Enter the real final writer boundary with synthetic admission metadata;
        # the nonnull profile must still stop it at the same binding loader.
        self.conn.rollback()
        self.conn.execute('BEGIN IMMEDIATE')
        manifest = dict(synthetic='schema-only')
        claim = dict(execution_scope='trusted-local-production')
        data = production_operations._contexts[context]
        data.update(writer_admission=(self.conn,digest(manifest),digest(claim)),writer_control=self.conn)
        with self.assertRaisesRegex(a.AdminError,'runtime_profile_contract_not_enabled'):
            with writer_boundary._local_lease(context,self.conn,manifest,claim):
                self.fail('writer capability issued')
        self.assertEqual(0,len(writer_boundary._local_leases))

    def test_unsigned_values_above_sqlite_signed_range_remain_exact_text(self):
        # This tests JSON extraction too, without conversion through REAL or CAST.
        self.conn.execute('DROP TRIGGER recognition_admin_bindings_immutable_update')
        self.old['target']['observation']['inode'] = 18446744073709551615
        self.conn.execute('UPDATE recognition_admin_bindings SET body_json=?,body_sha256=?', (canonical(self.old), digest(self.old)))
        self.conn.execute(s.definitions()['recognition_admin_bindings_immutable_update'])
        p = self.profile()
        self.conn.commit()
        s.check_control(self.conn)
        actual = self.conn.execute(f'SELECT target_device,target_inode,typeof(target_inode) FROM {r.PROFILES}').fetchone()
        self.assertEqual(tuple(actual), ('18446744073709551615','18446744073709551615','text'))
        self.assertEqual(p['profile_sha256'], digest({k:v for k,v in p.items() if k != 'profile_sha256'}))

    def test_control_inode_above_sqlite_signed_range_remains_exact_text(self):
        self.conn.execute('DROP TRIGGER recognition_admin_bindings_immutable_update')
        self.old['control_identity']['inode'] = 18446744073709551615
        self.conn.execute('UPDATE recognition_admin_bindings SET body_json=?,body_sha256=?', (canonical(self.old),digest(self.old)))
        self.conn.execute(s.definitions()['recognition_admin_bindings_immutable_update'])
        self.profile()
        self.conn.commit()
        s.check_control(self.conn)
        row = self.conn.execute(f'SELECT control_inode,typeof(control_inode) FROM {r.PROFILES}').fetchone()
        self.assertEqual(tuple(row),('18446744073709551615','text'))

    def test_deferred_profile_binding_and_audit_foreign_keys(self):
        self.profile(complete=False)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.commit()
        self.conn.rollback()
        q = self.challenge()
        self.conn.execute('DROP TRIGGER recognition_admin_audit_immutable_delete')
        self.conn.execute('DELETE FROM recognition_admin_audit')
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.commit()
        self.conn.rollback()
        self.assertEqual(q['source_generation'], 1)

    def test_profile_binding_consistency_and_downgrade(self):
        p = self.profile(complete=False)
        for changes in (dict(installation_id=TARGET),dict(target_id=INSTALL),dict(owner_id=2),dict(runtime_profile_sha256='d'*64),dict(production_state='ACTIVATED')):
            with self.subTest(changes=changes), self.rejected():
                self.binding(dict(dict(self.old, format=r.V3, generation=2, runtime_profile_sha256=p['profile_sha256']), **changes))
        self.binding(dict(self.old, format=r.V3, generation=2, runtime_profile_sha256=p['profile_sha256']))
        with self.rejected():
            self.binding(dict(self.old,generation=3))

    def auth_rows(self, p):
        self.conn.execute('INSERT INTO recognition_admin_primary VALUES(?,?,?,?,?,?,?,0)', ('d'*64,1,'key',1,2,1003,2000))
        self.insert(r.AUTH, dict(token_kind='primary',token_hash='d'*64,profile_sha256=p['profile_sha256'],created_at=1003))
        self.conn.execute('INSERT INTO recognition_admin_sessions VALUES(?,?,?,?,?,?,?,?,0)', ('e'*64,'d'*64,1,2,1,1,1004,2000))

    def test_auth_guard_scope_parent_and_generation(self):
        p = self.profile()
        for changes in (dict(token_hash='d'*64), dict(token_kind='invalid')):
            with self.rejected():
                self.insert(r.AUTH, dict(dict(token_kind='primary',token_hash='f'*64,profile_sha256=p['profile_sha256'],created_at=1003), **changes))
        self.auth_rows(p)
        row = dict(token_kind='session',token_hash='e'*64,profile_sha256=p['profile_sha256'],created_at=1004)
        with self.rejected():
            self.insert(r.AUTH, dict(row, created_at=1005))
        self.insert(r.AUTH, row)
        self.conn.execute('UPDATE recognition_admin_sessions SET generation=1')
        self.conn.execute(f'DROP TRIGGER {r.AUTH}_immutable_delete')
        self.conn.execute(f"DELETE FROM {r.AUTH} WHERE token_kind='session'")
        with self.rejected():
            self.insert(r.AUTH,row)

    def test_immutable_all_rows_and_all_replace_collisions(self):
        p = self.profile()
        self.auth_rows(p)
        for table in (r.CHALLENGES,r.PROFILES,r.AUTH):
            for sql in (f'UPDATE {table} SET created_at=0' if table != r.CHALLENGES else f'UPDATE {table} SET issued_at=0',
                        f'DELETE FROM {table}', f'INSERT OR REPLACE INTO {table} SELECT * FROM {table}'):
                with self.subTest(table=table,sql=sql), self.rejected():
                    self.conn.execute(sql)
        # OR REPLACE collisions on alternate unique keys cannot delete old rows.
        for key in ('profile_sha256','challenge_id','audit_sequence'):
            row = dict(p, profile_sha256='f'*64)
            if key != 'profile_sha256':
                row[key] = p[key]
            with self.subTest(key=key), self.rejected():
                self.conn.execute(f"INSERT OR REPLACE INTO {r.PROFILES} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",tuple(row.values()))

    def test_replace_guard_independently_protects_each_unique_key(self):
        p = self.profile()
        # Isolate immutable protection from the other insert-time guards.
        self.conn.execute('DROP TRIGGER recognition_runtime_profile_challenge_guard')
        self.conn.execute('DROP TRIGGER recognition_runtime_challenge_binding_guard')
        q = dict(self.conn.execute(f'SELECT * FROM {r.CHALLENGES}').fetchone())
        examples = ((r.PROFILES,p,dict(profile_sha256='f'*64,installation_id=TARGET,generation=99,challenge_id=INSTALL,audit_sequence=99),
                     [('profile_sha256',),('generation','role'),('installation_id','generation','role'),('challenge_id',),('audit_sequence',)]),
                    (r.CHALLENGES,q,dict(challenge_id=INSTALL,nonce_sha256='f'*64,audit_sequence=99,challenge_sha256='f'*64),
                     [('challenge_id',),('nonce_sha256',),('audit_sequence',),('challenge_sha256',)]))
        for table, original, changes, keys in examples:
            for key in keys:
                candidate = dict(original, **changes)
                candidate.update({k:original[k] for k in key})
                with self.subTest(table=table,key=key), self.assertRaisesRegex(sqlite3.IntegrityError,'immutable_runtime_profile_record'):
                    self.conn.execute(f"INSERT OR REPLACE INTO {table} ({','.join(candidate)}) VALUES ({','.join('?' for _ in candidate)})",tuple(candidate.values()))

    def test_read_validation_rejects_bad_digest_or_audit_metadata(self):
        self.profile(profile_sha256='f'*64)
        self.conn.commit()
        with self.assertRaisesRegex(ValueError,'digest_mismatch'):
            s.check_control(self.conn)

    def test_audit_metadata_must_match_immutable_profile_metadata(self):
        self.profile()
        self.conn.execute('DROP TRIGGER recognition_admin_audit_immutable_update')
        encoded = self.conn.execute('SELECT body_json FROM recognition_admin_audit WHERE sequence=2').fetchone()[0]
        body = dict(json.loads(encoded), actor='another-operator')
        self.conn.execute('UPDATE recognition_admin_audit SET body_json=?,body_sha256=? WHERE sequence=2', (canonical(body),digest(body)))
        self.conn.execute(s.definitions()['recognition_admin_audit_immutable_update'])
        self.conn.commit()
        with self.assertRaisesRegex(ValueError,'audit_mismatch'):
            s.check_control(self.conn)

    def test_historical_scope_survives_revocation_but_cannot_create_stale_scope(self):
        p = self.profile()
        self.auth_rows(p)
        self.conn.execute('UPDATE recognition_admin_primary SET revoked=1')
        self.conn.execute('UPDATE recognition_admin_sessions SET revoked=1')
        current = json.loads(self.conn.execute('SELECT body_json FROM recognition_admin_bindings WHERE generation=2').fetchone()[0])
        self.binding(dict(current,generation=3,previous_sha256=digest(current),runtime_profile_sha256=None))
        self.conn.commit()
        s.check_control(self.conn)
        with self.rejected():
            self.insert(r.AUTH,dict(token_kind='session',token_hash='e'*64,profile_sha256=p['profile_sha256'],created_at=1004))

    def test_v3_null_profile_still_requires_canonical_binding_metadata(self):
        for changes in (dict(installation_id='malformed'),dict(target_id=TARGET.upper()),dict(generation=2.0),dict(owner_id=1.5)):
            with self.subTest(changes=changes),self.rejected():
                self.binding(dict(dict(self.old,format=r.V3,generation=2,runtime_profile_sha256=None),**changes))

    def test_challenge_source_and_profile_role_path_schema_are_not_authority_claims(self):
        for changes in (dict(installation_id=TARGET),dict(owner_id=2),dict(source_binding_sha256='f'*64)):
            with self.subTest(changes=changes),self.rejected():
                self.challenge(**changes)


class RuntimeProfileMigrationTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.AdministrationTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def migrate(self, **changes):
        options = dict(expected_generation=1,operator='fixture',reason='storage migration',now=fixture.at(60))
        options.update(changes)
        return a.migrate_runtime_profile_contract(self.f.config, **options)

    def test_success_preserves_deployment_identity_revokes_auth_and_blocks_v3(self):
        self.f.confirmation()
        old = a.get_installation_control(self.f.config)
        target_before = self.f.path.read_bytes()
        self.assertEqual(2,self.migrate())
        with a.connect(self.f.control) as conn:
            s.check_control(conn)
            body = json.loads(conn.execute('SELECT body_json FROM recognition_admin_bindings WHERE generation=2').fetchone()[0])
            for key in ('target','control_identity','installation_id','target_id','owner_id'):
                self.assertEqual(old[key],body[key])
            self.assertIsNone(body['runtime_profile_sha256'])
            self.assertEqual('NOT_ACTIVATED',body['production_state'])
            for table in (r.CHALLENGES,r.PROFILES,r.AUTH):
                self.assertEqual(0,conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0])
            for table in ('recognition_admin_primary','recognition_admin_sessions'):
                self.assertEqual(0,conn.execute(f'SELECT count(*) FROM {table} WHERE revoked=0').fetchone()[0])
            self.assertEqual(0,conn.execute('SELECT count(*) FROM recognition_admin_stepups').fetchone()[0])
            self.assertEqual(0,conn.execute('SELECT count(*) FROM recognition_admin_confirmations WHERE used=0').fetchone()[0])
            a._audit_head(conn)
        self.assertEqual(target_before,self.f.path.read_bytes())
        with self.assertRaisesRegex(a.AdminError,'runtime_profile_contract_not_enabled'):
            a.get_installation_control(self.f.config)
        with self.assertRaises(a.AdminError):
            self.migrate()

    def test_ceremony_and_generation_required(self):
        for changes in (dict(expected_generation=2),dict(expected_generation=True),dict(operator=''),dict(reason='')):
            with self.subTest(changes=changes),self.assertRaises(a.AdminError):
                self.migrate(**changes)
        self.assertEqual(1,a.get_installation_control(self.f.config)['generation'])

    def test_full_migration_failure_rolls_back_ddl_binding_audit_and_auth(self):
        from src.review.recognition import approvals, admin_auth
        approvals.install(self.f.config,operator='fixture',reason='test',now=fixture.NOW)
        session, step, token = self.f.confirmation()
        approved = approvals.create_approval(self.f.config,session,step,token,operation_id=self.f.oid,
                                             reason='fixture approval',now=fixture.at(60))
        fresh_step = admin_auth.create_step_up(self.f.config,session,fixture.independent_code(fixture.at(90)),
            action='approve',operation_id=self.f.oid,now=fixture.at(90))
        admin_auth.begin_operation_confirmation(self.f.config,session,fresh_step,operation_id=self.f.oid,now=fixture.at(90))
        before = self.f.control.read_bytes()
        target_before = self.f.path.read_bytes()
        with patch.object(a,'_audit',side_effect=ValueError('injected')),self.assertRaises(ValueError):
            self.migrate(now=fixture.at(120))
        self.assertEqual(before,self.f.control.read_bytes())
        self.assertEqual(target_before,self.f.path.read_bytes())
        self.assertEqual(1,a.get_installation_control(self.f.config)['generation'])
        with a.connect(self.f.control) as conn:
            self.assertEqual('APPROVED',approvals._read(conn,approved['approval']['approval_id'])['state'])
            for table in ('recognition_admin_primary','recognition_admin_sessions'):
                self.assertGreater(conn.execute(f'SELECT count(*) FROM {table} WHERE revoked=0').fetchone()[0],0)
            self.assertGreater(conn.execute('SELECT count(*) FROM recognition_admin_stepups').fetchone()[0],0)
            self.assertGreater(conn.execute('SELECT count(*) FROM recognition_admin_confirmations WHERE used=0').fetchone()[0],0)

    def test_concurrent_migrations_advance_generation_exactly_once(self):
        barrier = threading.Barrier(2)
        def migrate():
            barrier.wait(timeout=10)
            try:
                return self.migrate()
            except a.AdminError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _:migrate(),range(2)))
        self.assertCountEqual(results,[2,'runtime_profile_contract_not_enabled'])
        with a.connect(self.f.control) as conn:
            self.assertEqual(2,conn.execute('SELECT MAX(generation) FROM recognition_admin_bindings').fetchone()[0])
            self.assertEqual(1,conn.execute("SELECT count(*) FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')='runtime_profile_contract_migrated'").fetchone()[0])
            s.check_control(conn)

    def test_migration_invalidates_approvals_without_reading_key_or_invoking_writer(self):
        from src.review.recognition import approvals, admin_auth, permanent
        approvals.install(self.f.config,operator='fixture',reason='test',now=fixture.NOW)
        session, step, token = self.f.confirmation()
        approved = approvals.create_approval(self.f.config,session,step,token,operation_id=self.f.oid,
                                             reason='fixture approval',now=fixture.at(60))
        with patch.object(admin_auth,'_cipher',side_effect=AssertionError('key read')), \
             patch.object(permanent,'finalize',side_effect=AssertionError('writer invoked')):
            self.migrate(now=fixture.at(90))
        with a.connect(self.f.control) as conn:
            value = approvals._read(conn,approved['approval']['approval_id'])
            self.assertEqual('INVALIDATED',value['state'])
            s.check_control(conn)

    def test_cli_requires_explicit_ceremony_and_exposes_no_enrollment_action(self):
        from scripts.active import manage_recognition_administration as cli
        common = ['migrate-runtime-profile-contract','--target',str(self.f.path),'--control',str(self.f.control),'--key-file',str(self.f.key_file)]
        for extra in ([],['--operator','fixture','--reason','test']):
            with self.subTest(extra=extra),self.assertRaises(SystemExit):
                cli.main(common+extra)
        with patch.object(a,'migrate_runtime_profile_contract',return_value=2) as migrate, patch('builtins.print'):
            cli.main(common+['--operator','fixture','--reason','test','--expected-generation','1'])
            migrate.assert_called_once()

    def test_migration_rejects_active_state_before_any_ddl(self):
        from src.review.recognition import approvals, local_readiness
        approvals.install(self.f.config,operator='fixture',reason='test',now=fixture.NOW)
        local_readiness.install(self.f.config,operator='fixture',reason='test',now=fixture.NOW)
        before = self.f.control.read_bytes()
        with patch.object(local_readiness,'_state',return_value=dict(state='ACTIVATED')), \
             self.assertRaisesRegex(a.AdminError,'requires_not_activated'):
            self.migrate()
        self.assertEqual(before,self.f.control.read_bytes())


if __name__ == '__main__':
    unittest.main()
