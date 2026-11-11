"""Migration/constraint fixtures only; no runtime claim acquisition or execution."""

from copy import deepcopy
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, administration_schema as schema, authorization
from src.review.recognition import runtime_execution_claim_schema as claims
from src.review.recognition import runtime_validation as runtime
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_runtime_execution_admission as fixture


class RuntimeExecutionClaimSchemaTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.RuntimeExecutionAdmissionTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config = self.f.config
        # Export is ordinary JSON data, used solely as a schema constraint fixture.
        import json
        observed = json.loads(self.f.assess().canonical_json)
        self.now = observed['checked_at_utc']
        from datetime import timedelta
        from src.review.recognition.trust import utc
        self.body = dict(format=claims.FORMAT,claim_id=str(uuid4()),operation_id=observed['proposal']['operation_id'],
            operation_sha256=digest(observed['proposal']),proposal_sha256=digest(observed['proposal']),
            proposal_reference=observed['reference'],acknowledgement_sha256=observed['reference']['acknowledgement_sha256'],
            approval_id=observed['approval']['approval_id'],approval_sha256=observed['approval_sha256'],
            approval_history_sha256=observed['approval_history_sha256'],runtime_scope=observed['runtime_scope'],
            authentication=observed['authentication'],dependency_snapshot_sha256=digest(observed['dependency_snapshot']),
            target_snapshot=observed['target_snapshot'],target_snapshot_sha256=digest(observed['target_snapshot']),
            admission_sha256=digest(observed),emergency_stop_snapshot_sha256=digest(observed['emergency_stop_snapshot']),
            issued_at_utc=self.now,expires_at_utc=(utc(self.now)+timedelta(seconds=300)).strftime('%Y-%m-%dT%H:%M:%SZ'),state='ISSUED')

    def migrate(self, **changes):
        args = dict(expected_generation=3,operator='migration-test',reason='disposable storage migration')
        args.update(changes)
        with patch.object(a,'target_identity',side_effect=authorization.target_identity):
            return claims.migrate(self.config,**args)

    def dump(self,path):
        with a.connect(path) as conn:
            return '\n'.join(conn.iterdump())

    def insert(self,conn,table,row,replace=False):
        verb = 'INSERT OR REPLACE' if replace else 'INSERT'
        conn.execute(f"{verb} INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",tuple(row.values()))

    def row(self,conn,body=None,**changes):
        body = deepcopy(self.body if body is None else body)
        row = dict(claim_id=body['claim_id'],operation_id=body['operation_id'],body_json=canonical(body),body_sha256=digest(body),
            generation=body['runtime_scope']['generation'],profile_sha256=body['runtime_scope']['runtime_profile_sha256'],
            issued_at=a.timestamp(body['issued_at_utc']),expires_at=a.timestamp(body['expires_at_utc']),
            audit_sequence=conn.execute('SELECT MAX(sequence)+1 FROM recognition_admin_audit').fetchone()[0])
        row.update(changes)
        return row

    def graph(self,conn):
        row = self.row(conn)
        self.insert(conn,claims.CLAIMS,row)
        body = dict(format=claims.EVENT_FORMAT,claim_id=row['claim_id'],claim_sha256=row['body_sha256'],sequence=1,
                    previous_sha256=None,state='ISSUED',reason='synthetic schema constraint fixture',at_utc=self.now)
        event = dict(claim_id=row['claim_id'],sequence=1,state='ISSUED',at=row['issued_at'],body_json=canonical(body),
                     body_sha256=digest(body),audit_sequence=row['audit_sequence'])
        self.insert(conn,claims.HISTORY,event)
        a._audit(conn,'runtime_execution_claim_issued',1,self.now,dict(claim_id=row['claim_id'],claim_sha256=row['body_sha256'],
                 event_sequence=1,event_sha256=event['body_sha256']))
        schema.check_control(conn)
        return row,event

    def inspect_mode(self,mode):
        for mode in (mode,):
            with self.subTest(mode=mode):
                with a.connect(self.config.control,write=True) as conn:
                    conn.execute('PRAGMA journal_mode='+mode)
                before_target = self.dump(self.config.target)
                result = self.migrate()
                self.assertEqual(claims.MIGRATION,result['migration_id'])
                with a.connect(self.config.control) as conn:
                    schema.check_control(conn)
                    actual = dict(conn.execute("SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
                    for name,sql in claims.definitions().items():
                        self.assertEqual(' '.join(sql.split()),' '.join(actual[name].split()))
                    self.assertEqual(9,len(conn.execute('PRAGMA table_info('+claims.CLAIMS+')').fetchall()))
                    self.assertEqual(7,len(conn.execute('PRAGMA table_info('+claims.HISTORY+')').fetchall()))
                    self.assertEqual(3,len(conn.execute('PRAGMA foreign_key_list('+claims.CLAIMS+')').fetchall()))
                    self.assertEqual(2,len(conn.execute('PRAGMA foreign_key_list('+claims.HISTORY+')').fetchall()))
                    self.assertTrue(any(row['name']==claims.CLAIMS+'_scope_idx' for row in conn.execute('PRAGMA index_list('+claims.CLAIMS+')')))
                    self.assertEqual(0,conn.execute('SELECT COUNT(*) FROM '+claims.CLAIMS).fetchone()[0])
                    self.assertEqual(0,conn.execute('SELECT COUNT(*) FROM '+claims.HISTORY).fetchone()[0])
                    self.assertEqual('ok',conn.execute('PRAGMA integrity_check').fetchone()[0])
                self.assertEqual(before_target,self.dump(self.config.target))

    def test_delete_fresh_schema_inspection_and_empty_storage(self):
        self.inspect_mode('DELETE')

    def test_wal_fresh_schema_inspection_and_empty_storage(self):
        self.inspect_mode('WAL')

    def test_idempotent_preserves_objects_records_and_target(self):
        self.migrate()
        before = self.dump(self.config.control),self.dump(self.config.target)
        self.assertFalse(self.migrate()['installed'])
        self.assertEqual(before,(self.dump(self.config.control),self.dump(self.config.target)))

    def test_protected_records_and_strict_v3_gate_preserved(self):
        with a.connect(self.config.control) as conn:
            protected = {name:[tuple(r) for r in conn.execute('SELECT * FROM '+name)] for name in
                ('recognition_admin_bindings','recognition_runtime_profiles','recognition_admin_primary','recognition_admin_sessions',
                 'recognition_admin_stepups','recognition_admin_confirmations','recognition_approvals','recognition_approval_history')}
        self.migrate()
        with a.connect(self.config.control) as conn:
            for name,rows in protected.items():
                self.assertEqual(rows,[tuple(r) for r in conn.execute('SELECT * FROM '+name)])
            with self.assertRaisesRegex(a.AdminError,'runtime_profile_contract_not_enabled'):
                a._binding(conn)

    def test_valid_synthetic_graph_idempotent_and_immutable(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row,event = self.graph(conn)
            for table,values in ((claims.CLAIMS,row),(claims.HISTORY,event)):
                for sql in ('UPDATE '+table+' SET body_json=body_json','DELETE FROM '+table):
                    with self.subTest(sql=sql),self.assertRaises(sqlite3.IntegrityError):
                        conn.execute(sql)
                with self.assertRaises(sqlite3.IntegrityError):
                    self.insert(conn,table,values,replace=True)
            conn.commit()
        before = self.dump(self.config.control)
        self.assertFalse(self.migrate()['installed'])
        self.assertEqual(before,self.dump(self.config.control))

    def test_duplicate_operation_and_all_unique_replace_collisions(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN')
            row,event = self.graph(conn)
            changed = deepcopy(self.body)
            changed['claim_id'] = str(uuid4())
            with self.assertRaisesRegex(sqlite3.IntegrityError,'immutable_runtime_execution_claim'):
                self.insert(conn,claims.CLAIMS,self.row(conn,changed))
            for changes in (dict(claim_id=str(uuid4())),dict(operation_id=str(uuid4())),dict(body_sha256='e'*64),dict(audit_sequence=row['audit_sequence']+1)):
                with self.subTest(changes=changes),self.assertRaises(sqlite3.IntegrityError):
                    self.insert(conn,claims.CLAIMS,dict(row,**changes),replace=True)

    def test_malformed_scalars_lifetime_and_nul(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN')
            row = self.row(conn)
            cases = [dict(claim_id='bad'),dict(claim_id=row['claim_id']+'\0'),dict(operation_id='x'),dict(body_sha256='A'*64),
                dict(body_sha256='a'*64+'\0'),dict(profile_sha256='q'*64),dict(issued_at=-1),dict(expires_at=row['issued_at']),
                dict(expires_at=row['issued_at']+299),dict(expires_at=row['issued_at']+301),dict(generation=0)]
            for changes in cases:
                with self.subTest(changes=changes),self.assertRaises(sqlite3.IntegrityError):
                    self.insert(conn,claims.CLAIMS,dict(row,**changes))
            for key,value in (('operation_sha256','g'*64),('proposal_sha256','a'*64+'\0'),('approval_id','BAD')):
                body = deepcopy(self.body);body[key]=value
                with self.subTest(key=key),self.assertRaises(sqlite3.IntegrityError):
                    self.insert(conn,claims.CLAIMS,self.row(conn,body))

    def test_history_state_missing_genesis_and_deferred_audit_fk(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN')
            row = self.row(conn);self.insert(conn,claims.CLAIMS,row)
            event = dict(claim_id=row['claim_id'],sequence=1,state='BAD',at=row['issued_at'],body_json='{}',body_sha256='e'*64,audit_sequence=row['audit_sequence'])
            with self.assertRaises(sqlite3.IntegrityError):
                self.insert(conn,claims.HISTORY,event)
            with self.assertRaisesRegex(Exception,'genesis_missing'):
                claims.check_rows(conn)
            with self.assertRaises(sqlite3.IntegrityError):
                conn.commit()

    def test_incompatible_and_partial_objects_fail_closed(self):
        before = self.dump(self.config.target)
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('CREATE TABLE '+claims.CLAIMS+'(wrong TEXT)')
            conn.commit()
        snapshot = self.dump(self.config.control)
        with self.assertRaisesRegex(Exception,'administration_schema_mismatch'):
            self.migrate()
        self.assertEqual(snapshot,self.dump(self.config.control))
        self.assertEqual(before,self.dump(self.config.target))

    def test_audit_failure_rolls_back_all_ddl_and_records(self):
        before = self.dump(self.config.control),self.dump(self.config.target)
        with patch.object(a,'_audit',side_effect=OSError('synthetic migration failure')):
            with self.assertRaises(OSError):
                self.migrate()
        self.assertEqual(before,(self.dump(self.config.control),self.dump(self.config.target)))

    def test_wrong_generation_and_identity_never_install(self):
        before = self.dump(self.config.control),self.dump(self.config.target)
        with self.assertRaisesRegex(Exception,'generation_conflict'):
            self.migrate(expected_generation=2)
        with self.assertRaisesRegex(Exception,'control_identity_mismatch'):
            claims.migrate(self.config,expected_generation=3,operator='fixture',reason='wrong runtime host')
        self.assertEqual(before,(self.dump(self.config.control),self.dump(self.config.target)))

    def test_existing_legacy_table_and_synthetic_row_preserved(self):
        # Schema-only legacy storage fixture: not a valid execution authority.
        with a.connect(self.config.target,write=True) as conn:
            legacy = dict(format='recognition-local-execution-claim-v1',operation_id=self.body['operation_id'],schema_fixture=True)
            conn.execute('INSERT INTO recognition_execution_claims VALUES(?,?,?)',
                         (self.body['operation_id'],canonical(legacy),digest(legacy)))
            conn.commit()
        before = self.dump(self.config.target)
        self.migrate()
        self.assertEqual(before,self.dump(self.config.target))
        with a.connect(self.config.control) as conn:
            self.assertEqual(0,conn.execute('SELECT COUNT(*) FROM '+claims.CLAIMS).fetchone()[0])

    def test_late_validation_failure_rolls_back_ddl_and_audit(self):
        before = self.dump(self.config.control),self.dump(self.config.target)
        verify = a._verify
        calls = []
        def checked(*args):
            calls.append(True)
            if len(calls)==2:
                raise OSError('synthetic final validation failure')
            return verify(*args)
        with patch.object(a,'_verify',side_effect=checked),self.assertRaises(OSError):
            self.migrate()
        self.assertEqual(2,len(calls))
        self.assertEqual(before,(self.dump(self.config.control),self.dump(self.config.target)))

    def test_target_write_denial_and_no_key_reads(self):
        from contextlib import contextmanager
        from src.review.recognition import admin_auth
        original = a.connect
        denied = []
        @contextmanager
        def guarded(path,**kwargs):
            with original(path,**kwargs) as conn:
                if path == self.config.target:
                    def authorizer(action,*args):
                        if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
                            denied.append(action)
                            return sqlite3.SQLITE_DENY
                        return sqlite3.SQLITE_OK
                    conn.set_authorizer(authorizer)
                yield conn
        with patch.object(a,'connect',side_effect=guarded),patch.object(admin_auth,'_cipher',side_effect=AssertionError('key access')):
            self.assertTrue(self.migrate()['installed'])
        self.assertEqual([],denied)

    def test_mid_ddl_failure_rolls_back_partial_extension(self):
        before = self.dump(self.config.control),self.dump(self.config.target)
        original = claims.definitions()
        broken = dict(list(original.items())[:2])
        broken['synthetic_failure'] = 'CREATE TABLE invalid syntax'
        with patch.object(claims,'definitions',return_value=broken),self.assertRaises(sqlite3.OperationalError):
            self.migrate()
        self.assertEqual(before,(self.dump(self.config.control),self.dump(self.config.target)))

    def test_scope_types_and_physical_identity_fail_closed(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN')
            for field,value in (('auth_epoch',True),('mfa_epoch',1.5),('owner_id',True),('generation',2)):
                body = deepcopy(self.body);body['runtime_scope'][field]=value
                with self.subTest(field=field),self.assertRaises(sqlite3.IntegrityError):
                    self.insert(conn,claims.CLAIMS,self.row(conn,body))
            for field,value in (('hostname','other-worker'),('device',True),('inode',2),('database','/wrong/path')):
                body = deepcopy(self.body);body['target_snapshot']['target']['observation'][field]=value
                with self.subTest(field=field),self.assertRaises(sqlite3.IntegrityError):
                    self.insert(conn,claims.CLAIMS,self.row(conn,body))

    def test_missing_all_extension_objects_cannot_hide_install_audit(self):
        self.migrate()
        # Deliberately corrupt this disposable fixture, never a migration step.
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('DROP TRIGGER '+claims.CLAIMS+'_audit_guard')
            conn.execute('DROP TABLE '+claims.HISTORY)
            conn.execute('DROP TABLE '+claims.CLAIMS)
            conn.commit()
        with self.assertRaisesRegex(Exception,'administration_schema_mismatch'):
            self.migrate()
