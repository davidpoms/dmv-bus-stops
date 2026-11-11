"""Disposable DATA graphs only; never an attempt producer or runtime authority."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, closing
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, administration_schema as base, authorization
from src.review.recognition import runtime_execution_attempt_schema as s, runtime_activation_authority_schema as authority
from src.review.recognition import runtime_execution_claim_schema as claims, runtime_validation as runtime, writer_boundary
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import utc
from tests import test_recognition_runtime_activation_authority_schema as fixtures


class ExecutionAttemptSchemaTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ActivationAuthoritySchemaTests(); self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.migrate(); self.config = self.f.config

    def migrate(self, **changes):
        options = dict(expected_generation=3,operator='storage-test',reason='inert attempt storage')
        options.update(changes)
        with patch.object(a,'target_identity',side_effect=authorization.target_identity):
            return s.migrate(self.config,**options)

    def prepare(self):
        self.migrate()
        body = self.f.body(self.f.f.activate_fixture())
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE'); self.f.graph(conn,body); conn.commit()
        self.authority = body
        return dict(format=s.FORMAT,attempt_id=str(uuid4()),authority_id=body['authority_id'],authority_sha256=digest(body),
                    created_at_utc=body['issued_at_utc'],expires_at_utc=body['expires_at_utc'])

    def event(self, body):
        return dict(format=s.EVENT_FORMAT,attempt_id=body['attempt_id'],attempt_sha256=digest(body),sequence=1,
            state='ATTEMPT_CREATED',at_utc=body['created_at_utc'],previous_sha256=None,
            actor_id=self.authority['runtime_target']['owner_id'],reason=self.authority['producer_ceremony']['reason'])

    def rows(self, conn, body, *, bad_digest=False):
        sequence = conn.execute('SELECT max(sequence)+1 FROM recognition_admin_audit').fetchone()[0]
        row = dict(attempt_id=body['attempt_id'],authority_id=body['authority_id'],authority_sha256=body['authority_sha256'],
            created_at=a.timestamp(body['created_at_utc']),expires_at=a.timestamp(body['expires_at_utc']),
            body_json=canonical(body),body_sha256='0'*64 if bad_digest else digest(body),audit_sequence=sequence)
        event = self.event(body); event['attempt_sha256'] = row['body_sha256']
        h = dict(attempt_id=body['attempt_id'],sequence=1,state='ATTEMPT_CREATED',at=row['created_at'],previous_sha256=None,
                 body_json=canonical(event),body_sha256=digest(event),audit_sequence=sequence)
        return row,h,event

    def graph(self, conn, body, *, bad_digest=False):
        row,h,event = self.rows(conn,body,bad_digest=bad_digest)
        self.f.insert(conn,s.ATTEMPTS,row); self.f.insert(conn,s.HISTORY,h)
        a._audit(conn,s.CREATE_ACTION,event['actor_id'],event['at_utc'],dict(attempt_id=body['attempt_id'],
            attempt_sha256=row['body_sha256'],event_sequence=1,event_sha256=h['body_sha256']))
        return row,h

    def test_migration_idempotence_manifest_and_protected_state(self):
        with a.connect(self.config.control) as conn:
            before = runtime._denial_baseline(conn); previous = claims.manifest(conn)
            old_audits = [tuple(r) for r in conn.execute('SELECT * FROM recognition_admin_audit')]
        target = self.f.dump(self.config.target)
        with patch.object(Path,'read_text',side_effect=AssertionError('key read')),patch.object(Path,'read_bytes',side_effect=AssertionError('key read')):
            self.assertTrue(self.migrate()['installed'])
        self.assertEqual(target,self.f.dump(self.config.target))
        installed = self.f.dump(self.config.control)
        self.assertFalse(self.migrate()['installed']); self.assertEqual(installed,self.f.dump(self.config.control))
        with a.connect(self.config.control) as conn:
            base.check_control(conn)
            self.assertEqual(before,runtime._denial_baseline(conn))
            self.assertEqual(previous,s.authority_manifest(conn))
            self.assertEqual(old_audits,[tuple(r) for r in conn.execute('SELECT * FROM recognition_admin_audit WHERE sequence<=?',(len(old_audits),))])
            self.assertEqual((0,0),(conn.execute(f'SELECT count(*) FROM {s.ATTEMPTS}').fetchone()[0],conn.execute(f'SELECT count(*) FROM {s.HISTORY}').fetchone()[0]))
            self.assertEqual([],conn.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual(['ok'],[r[0] for r in conn.execute('PRAGMA integrity_check')])

    def test_canonical_roundtrip_and_durable_binding(self):
        body = self.prepare()
        with a.connect(self.config.control) as conn:
            self.assertEqual(body,s.parse_attempt(canonical(body),attempt_sha256=s.attempt_digest(body)))
            self.assertEqual(self.authority,s.validate_binding(conn,body))
            e = self.event(body)
            self.assertEqual(e,s.parse_created(conn,canonical(e),event_sha256=digest(e),attempt=body))
        for text in (canonical(body)+' ',canonical(body)[:-1]+',"format":"'+s.FORMAT+'"}',canonical(body).replace('"attempt_id":','"other":')):
            with self.subTest(text=text[-30:]),self.assertRaises(ValueError):s.parse_attempt(text,attempt_sha256=digest(body))
        with self.assertRaises(ValueError):s.parse_attempt(canonical(body),attempt_sha256='f'*64)

    def test_unknown_missing_uuid_sha_nul_and_timestamps(self):
        body = self.prepare()
        for key in body:
            b = dict(body); del b[key]
            with self.subTest(missing=key),self.assertRaises(ValueError):s.validate_attempt(b)
        cases = [('extra','bad'),('format','other'),('authority_id','AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE'),('attempt_id','bad'),
            ('authority_id',body['authority_id']+'\0'),('attempt_id',body['attempt_id'][:3]+'\0'+body['attempt_id'][4:]),
            ('authority_sha256','A'*64),('authority_sha256',body['authority_sha256']+'\0'),('authority_sha256','0\0'+'a'*62),
            ('created_at_utc',True),('created_at_utc',1.0),('created_at_utc','2099-01-01T00:00:00+00:00'),
            ('created_at_utc','2099-1-1T00:00:00Z'),('expires_at_utc',body['created_at_utc'])]
        for key,value in cases:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):s.validate_attempt(dict(body,**{key:value}))

    def test_authority_id_digest_and_lifetime_mismatch(self):
        body = self.prepare()
        cases = [dict(body,authority_id=str(uuid4())),dict(body,authority_sha256='a'*64),
                 dict(body,expires_at_utc=(utc(body['expires_at_utc'])+timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')),
                 dict(body,created_at_utc=(utc(body['created_at_utc'])-timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ'))]
        with a.connect(self.config.control) as conn:
            for b in cases:
                with self.subTest(body=b),self.assertRaises(ValueError):s.validate_binding(conn,b)
        s.validate_expiry(body,now=body['created_at_utc'])
        for now in (body['expires_at_utc'],True,'bad',(utc(body['created_at_utc'])-timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')):
            with self.subTest(now=now),self.assertRaises(ValueError):s.validate_expiry(body,now=now)

    def test_every_transitive_scope_field_mismatch(self):
        body = self.prepare(); expected = {k:deepcopy(self.authority[k]) for k in s.SCOPE_FIELDS}
        paths = [('runtime_target',k) for k in ('installation_id','target_id','generation','owner_id','auth_epoch','mfa_epoch','runtime_profile_sha256','binding_sha256')]
        paths += [('activation','sequence'),('activation','event_sha256'),('approval','approval_id'),('approval','approval_sha256'),
                  ('operation_reference','operation_id'),('operation_reference','operation_sha256'),
                  ('operation_reference','proposal_reference'),('physical_snapshot','target'),('authentication','primary_sha256')]
        with a.connect(self.config.control) as conn:
            s.validate_binding(conn,body,expected_scope=expected)
            for group,key in paths:
                bad = deepcopy(expected); v = bad[group][key]
                bad[group][key] = v+1 if type(v) is int else {} if type(v) is dict else 'different'
                with self.subTest(group=group,key=key),self.assertRaises(ValueError):s.validate_binding(conn,body,expected_scope=bad)

    def test_genesis_only_and_strict_integer_null_reason(self):
        body = self.prepare(); event = self.event(body)
        cases = [('state',x) for x in ('WRITER_ADMITTED','TARGET_MUTATION_STARTED','COMPLETED','UNCERTAIN')]
        cases += [('sequence',True),('sequence',2),('actor_id',True),('previous_sha256','a'*64),('reason','bad\0reason'),('attempt_sha256','a'*64)]
        with a.connect(self.config.control) as conn:
            for key,value in cases:
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):s.validate_created(conn,dict(event,**{key:value}),attempt=body)
            bad = dict(event); del bad['previous_sha256']
            with self.assertRaises(ValueError):s.validate_created(conn,bad,attempt=body)

    def test_immutable_records_replace_and_single_authority_winner(self):
        body = self.prepare()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE'); row,h = self.graph(conn,body); base.check_control(conn); conn.commit()
            conn.execute('PRAGMA recursive_triggers=OFF')
            for table,record in ((s.ATTEMPTS,row),(s.HISTORY,h)):
                for statement in (f'UPDATE {table} SET body_json=body_json',f'DELETE FROM {table}'):
                    with self.subTest(statement=statement),self.assertRaises(sqlite3.IntegrityError):conn.execute(statement)
                with self.assertRaises(sqlite3.IntegrityError):self.f.insert(conn,table,record,replace=True)
            other = dict(body,attempt_id=str(uuid4())); r,_,_ = self.rows(conn,other)
            with self.assertRaises(sqlite3.IntegrityError):self.f.insert(conn,s.ATTEMPTS,r)
            conn.rollback(); base.check_control(conn)

    def test_deferred_graph_foreign_key_and_audit_guards(self):
        body = self.prepare()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE'); row,h,event = self.rows(conn,body)
            bad = dict(row,authority_id=str(uuid4()))
            with self.assertRaises(sqlite3.IntegrityError):self.f.insert(conn,s.ATTEMPTS,bad)
            for key,value in (('attempt_id',body['attempt_id']+'\0'),('authority_sha256',body['authority_sha256']+'\0'),
                              ('created_at',-1),('created_at',2**63-1)):
                with self.subTest(key=key),self.assertRaises(sqlite3.IntegrityError):
                    self.f.insert(conn,s.ATTEMPTS,dict(row,**{key:value}))
            self.f.insert(conn,s.ATTEMPTS,row)
            with self.assertRaises(sqlite3.IntegrityError):conn.commit()
            conn.rollback(); conn.execute('BEGIN IMMEDIATE')
            self.f.insert(conn,s.ATTEMPTS,row); self.f.insert(conn,s.HISTORY,h)
            with self.assertRaises(sqlite3.IntegrityError):a._audit(conn,'wrong',event['actor_id'],event['at_utc'],{})
            conn.rollback()

    def test_readonly_inspection_immutable_data_no_key_or_authority(self):
        body = self.prepare()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE'); self.graph(conn,body); conn.commit()
        before = self.f.dump(self.config.control); original = a.connect; observed = []
        @contextmanager
        def read(path, *, write=False):
            self.assertEqual(self.config.control,path); self.assertFalse(write)
            with original(path,write=write) as conn:
                self.assertEqual(1,conn.execute('PRAGMA query_only').fetchone()[0])
                with self.assertRaises(sqlite3.OperationalError):conn.execute('UPDATE recognition_admin_confirmations SET used=used')
                if conn.in_transaction:conn.rollback()  # Failed DML may begin an implicit read transaction.
                conn.set_trace_callback(observed.append)
                yield conn
        with patch.object(a,'connect',side_effect=read),patch.object(Path,'read_text',side_effect=AssertionError('key read')),patch.object(Path,'read_bytes',side_effect=AssertionError('key read')):
            result = s.inspect_attempt(self.config.control,attempt_id=body['attempt_id'])
        self.assertEqual('VALID',result['status']); self.assertFalse(result['execution_authority'])
        with self.assertRaises(TypeError):result['attempt']['authority_id']='bad'
        with self.assertRaises(ValueError):writer_boundary.acquire(result,self.config.target,{})
        self.assertTrue(all(q.lstrip().split()[0].upper() in ('SELECT','PRAGMA','BEGIN','ROLLBACK') for q in observed))
        self.assertEqual(before,self.f.dump(self.config.control))
        self.assertEqual('MISSING',s.inspect_attempt(self.config.control,attempt_id=str(uuid4()))['status'])
        self.assertEqual('CONFLICTING',s.inspect_attempt(self.config.control,attempt_id=body['attempt_id'],authority_id=str(uuid4()))['status'])

    def test_malformed_digest_graph_inspection_fails_closed(self):
        body = self.prepare()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE'); self.graph(conn,body,bad_digest=True); conn.commit()
        with a.connect(self.config.control) as conn:
            with self.assertRaises(ValueError):base.check_control(conn)
        self.assertEqual('MALFORMED',s.inspect_attempt(self.config.control,attempt_id=body['attempt_id'])['status'])

    def test_partial_incompatible_manifest_and_stale_generation(self):
        before = self.f.dump(self.config.control)
        with self.assertRaises(ValueError):self.migrate(expected_generation=2)
        self.assertEqual(before,self.f.dump(self.config.control))
        with a.connect(self.config.control,write=True) as conn:
            conn.execute(s.definitions()[s.ATTEMPTS]); conn.commit()
        with self.assertRaises(ValueError):self.migrate()

    def test_installed_trigger_tampering_rejected(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            name=s.ATTEMPTS+'_immutable_update'; conn.execute('DROP TRIGGER '+name)
            conn.execute(f'CREATE TRIGGER {name} BEFORE UPDATE ON {s.ATTEMPTS} BEGIN SELECT 1; END'); conn.commit()
        with self.assertRaises(ValueError):self.migrate()

    def test_rollback_ddl_audit_final_and_commit_faults(self):
        before = self.f.dump(self.config.control); original_audit=a._audit; original_verify=a._verify; connect=a.sqlite3.connect
        for stage in ('audit','final','commit','silent','after'):
            def audit(conn,action,*args):
                if action==s.ACTION and stage=='audit':raise OSError('audit')
                return original_audit(conn,action,*args)
            def verify(config,control,target,binding):
                original_verify(config,control,target,binding)
                if stage=='final' and s.present(control):raise OSError('final')
            class Fault(sqlite3.Connection):
                def commit(conn):
                    if conn.execute('PRAGMA database_list').fetchone()[2]==str(self.config.control):
                        if stage=='commit':raise OSError('before')
                        if stage=='silent':return None
                        super(Fault,conn).commit()
                        if stage=='after':raise OSError('uncertain')
                    else:super(Fault,conn).commit()
            def connected(*args,**kwargs):return connect(*args,**dict(kwargs,factory=Fault))
            with self.subTest(stage=stage),patch.object(a,'_audit',side_effect=audit),patch.object(a,'_verify',side_effect=verify),patch.object(a.sqlite3,'connect',side_effect=connected):
                with self.assertRaises((ValueError,OSError)):self.migrate()
            if stage!='after':self.assertEqual(before,self.f.dump(self.config.control))
        with a.connect(self.config.control) as conn:
            base.check_control(conn); self.assertEqual(0,conn.execute(f'SELECT count(*) FROM {s.ATTEMPTS}').fetchone()[0])

    def _reservation(self, mode):
        with closing(sqlite3.connect(self.config.target)) as conn:conn.execute('PRAGMA journal_mode='+mode)
        before = self.f.dump(self.config.target); connect=a.sqlite3.connect; checked=[]
        class Probe(sqlite3.Connection):
            def execute(conn,sql,*args,**kw):
                is_target=bool(conn.execute_path == str(self.config.target)) if hasattr(conn,'execute_path') else False
                if is_target:self.assertNotIn(sql.split()[0].upper(),('INSERT','UPDATE','DELETE','REPLACE','CREATE','DROP','ALTER'))
                return super(Probe,conn).execute(sql,*args,**kw)
            def commit(conn):
                path=conn.execute('PRAGMA database_list').fetchone()[2]
                self.assertNotEqual(str(self.config.target),path)
                with closing(connect(self.config.target,timeout=0)) as other:
                    with self.assertRaises(sqlite3.OperationalError):other.execute('BEGIN IMMEDIATE')
                checked.append(True); return super(Probe,conn).commit()
        def connected(*args,**kwargs):
            conn=connect(*args,**dict(kwargs,factory=Probe)); conn.execute_path=conn.execute('PRAGMA database_list').fetchone()[2]; return conn
        with patch.object(a.sqlite3,'connect',side_effect=connected):self.migrate()
        self.assertTrue(checked); self.assertEqual(before,self.f.dump(self.config.target))
        with closing(connect(self.config.target,timeout=0)) as conn:conn.execute('BEGIN IMMEDIATE');conn.rollback()

    def test_target_reservation_delete(self):self._reservation('DELETE')
    def test_target_reservation_wal(self):self._reservation('WAL')

    def test_concurrent_migration_single_install_no_attempts(self):
        def call(_):
            try:return s.migrate(self.config,expected_generation=3,operator='storage-test',reason='inert attempt storage')['installed']
            except sqlite3.OperationalError as error:
                self.assertIn(error.sqlite_errorcode,(sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED));return None
        with patch.object(a,'target_identity',side_effect=authorization.target_identity),ThreadPoolExecutor(max_workers=2) as pool:
            values=list(pool.map(call,range(2)))
        self.assertEqual(1,sum(x is True for x in values))
        with a.connect(self.config.control) as conn:
            base.check_control(conn); self.assertEqual(1,len(authority._rows(conn,s.ACTION)))
            self.assertEqual(0,conn.execute(f'SELECT count(*) FROM {s.ATTEMPTS}').fetchone()[0])

    def _data_race(self, same):
        # Direct synthetic constraint records only, not an attempt-creation API.
        import threading
        body=self.prepare(); before=self.f.dump(self.config.target); barrier=threading.Barrier(2)
        def contender(index):
            value=body if same or index==0 else dict(body,attempt_id=str(uuid4()))
            try:
                with a.connect(self.config.control,write=True) as conn:
                    barrier.wait(timeout=10);conn.execute('BEGIN IMMEDIATE')
                    self.graph(conn,value);conn.commit()
                return 'INSERTED'
            except sqlite3.IntegrityError:return 'REJECTED'
            except sqlite3.OperationalError as error:
                self.assertIn(error.sqlite_errorcode,(sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED));return 'REJECTED'
        with ThreadPoolExecutor(max_workers=2) as pool:values=list(pool.map(contender,range(2)))
        self.assertEqual(['INSERTED','REJECTED'],sorted(values))
        with a.connect(self.config.control) as conn:
            base.check_control(conn)
            self.assertEqual(1,conn.execute(f'SELECT count(*) FROM {s.ATTEMPTS}').fetchone()[0])
            self.assertEqual(1,conn.execute(f'SELECT count(*) FROM {s.HISTORY}').fetchone()[0])
            self.assertEqual(1,len(authority._rows(conn,s.CREATE_ACTION)))
        self.assertEqual(before,self.f.dump(self.config.target))

    def test_same_authority_same_synthetic_identity_race(self):self._data_race(True)
    def test_same_authority_different_synthetic_identity_race(self):self._data_race(False)

    def test_populated_historical_authority_survives_extension_without_authority_gain(self):
        from src.review.recognition import local_readiness, runtime_challenges
        body=self.f.body(self.f.f.activate_fixture())
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE');self.f.graph(conn,body)
            binding=runtime_challenges._deployment_binding(conn)
            local_readiness._append(conn,binding,'DEACTIVATED',1,'synthetic nonactive migration fixture',runtime._utc_now())
            conn.commit()
            original=[tuple(r) for r in conn.execute(f'SELECT * FROM {authority.AUTHORITIES}')]
            genesis=[tuple(r) for r in conn.execute(f'SELECT * FROM {authority.LIFECYCLE}')]
        target=self.f.dump(self.config.target)
        self.assertTrue(self.migrate()['installed'])
        self.assertEqual(target,self.f.dump(self.config.target))
        with a.connect(self.config.control) as conn:
            base.check_control(conn)
            self.assertEqual(original,[tuple(r) for r in conn.execute(f'SELECT * FROM {authority.AUTHORITIES}')])
            self.assertEqual(genesis,[tuple(r) for r in conn.execute(f'SELECT * FROM {authority.LIFECYCLE}')])
            self.assertEqual(0,conn.execute(f'SELECT count(*) FROM {s.ATTEMPTS}').fetchone()[0])
