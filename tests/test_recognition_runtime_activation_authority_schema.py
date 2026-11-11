"""Synthetic DATA/storage graphs only. No authority producer or runtime writer."""

from contextlib import contextmanager, closing
from copy import deepcopy
from datetime import timedelta
import json
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, administration_schema as base, authorization
from src.review.recognition import runtime_activation_authority_schema as s, runtime_execution_claim_schema as claims
from src.review.recognition import runtime_validation as runtime, writer_boundary, production_operations, local_readiness
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import utc
from tests import test_recognition_runtime_activated_owner as fixtures


class ActivationAuthoritySchemaTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.RuntimeActivatedOwnerTests()
        # Preserve its real enrollment/auth/ACK/v2 approval/schema fixtures, but
        # defer its explicit synthetic ledger activation until AFTER migration.
        with patch.object(fixtures.RuntimeActivatedOwnerTests, 'activate_fixture', return_value=None):
            self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config = self.f.config
        self.observed = json.loads(self.f.f.snapshot.canonical_json)

    def migrate(self, **changes):
        options = dict(expected_generation=3, operator='storage-test', reason='disposable storage only')
        options.update(changes)
        with patch.object(a, 'target_identity', side_effect=authorization.target_identity):
            return s.migrate(self.config, **options)

    def dump(self, path):
        with a.connect(path) as conn:
            return '\n'.join(conn.iterdump())

    def body(self, activation=None):
        observed = self.observed; op = observed['proposal']
        now = runtime._utc_now()
        later = lambda seconds: (utc(now)+timedelta(seconds=seconds)).strftime('%Y-%m-%dT%H:%M:%SZ')
        reference = {k:op[k] for k in ('operation_id','event_id','event_sha256','preparation_id','preparation_sha256',
                                      'writer_manifest_sha256','population_sha256')}
        reference.update(operation_sha256=digest(op), writer_family=op['family'], proposal_reference=observed['reference'])
        return dict(format=s.FORMAT, authority_id=str(uuid4()), operation_reference=reference,
            runtime_target=deepcopy(observed['runtime_scope']), physical_snapshot=deepcopy(observed['target_snapshot']),
            activation=dict(sequence=activation['sequence'] if activation else 1,
                            event_sha256=digest(activation) if activation else 'a'*64),
            approval=dict(approval_id=observed['approval']['approval_id'],approval_sha256=observed['approval_sha256'],
                          effective_history_sha256=observed['approval_history_sha256']),
            authentication=deepcopy(observed['authentication']),
            producer_ceremony=dict(step_artifact_sha256='b'*64,confirmation_artifact_sha256='c'*64,
                confirmation_token_sha256='d'*64,decision='authorize_runtime_execution',reason='SYNTHETIC storage graph only'),
            dependencies=dict(snapshot=deepcopy(observed['dependency_snapshot']),snapshot_sha256=digest(observed['dependency_snapshot'])),
            emergency_stop=dict(snapshot=deepcopy(observed['emergency_stop_snapshot']),snapshot_sha256=digest(observed['emergency_stop_snapshot'])),
            readiness=dict(assessment_sha256='e'*64,assessed_at_utc=now,policy=s.READINESS),
            issued_at_utc=now,expires_at_utc=later(120),lifetime_policy=s.LIFETIME)

    def insert(self, conn, table, row, replace=False):
        conn.execute(('INSERT OR REPLACE' if replace else 'INSERT')+f" INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", tuple(row.values()))

    def row(self, body, sequence):
        scope, ref = body['runtime_target'], body['operation_reference']
        return dict(authority_id=body['authority_id'],operation_id=ref['operation_id'],operation_sha256=ref['operation_sha256'],
            writer_manifest_sha256=ref['writer_manifest_sha256'],installation_id=scope['installation_id'],target_id=scope['target_id'],
            generation=scope['generation'],profile_sha256=scope['runtime_profile_sha256'],owner_id=scope['owner_id'],
            auth_epoch=scope['auth_epoch'],mfa_epoch=scope['mfa_epoch'],activation_sequence=body['activation']['sequence'],
            activation_sha256=body['activation']['event_sha256'],approval_id=body['approval']['approval_id'],
            approval_sha256=body['approval']['approval_sha256'],confirmation_sha256=body['producer_ceremony']['confirmation_token_sha256'],
            issued_at=a.timestamp(body['issued_at_utc']),expires_at=a.timestamp(body['expires_at_utc']),
            body_json=canonical(body),body_sha256=digest(body),audit_sequence=sequence)

    def genesis(self, body):
        ref = body['operation_reference']
        return dict(format=s.EVENT_FORMAT,authority_id=body['authority_id'],authority_sha256=digest(body),
            operation_id=ref['operation_id'],operation_sha256=ref['operation_sha256'],sequence=1,state='AUTHORIZED',kind='AUTHORIZE',
            at_utc=body['issued_at_utc'],previous_sha256=None,entry_sha256=None,seal_sha256=None,receipt_sha256=None,
            actor_id=body['runtime_target']['owner_id'],reason=body['producer_ceremony']['reason'],
            evidence=dict(format=s.EVIDENCE_FORMAT,authority_id=body['authority_id'],authority_sha256=digest(body)))

    def prepare_graph(self):
        self.migrate()
        activation = self.f.activate_fixture()  # Explicit test-only ledger DATA, not an activation API.
        return self.body(activation)

    def graph(self, conn, body, *, row_changes=None, event_changes=None, issue=True, include_genesis=True,
              subject_owner=None, step_audit_actor=None):
        now = body['issued_at_utc']; scope = body['runtime_target']; ceremony = body['producer_ceremony']
        ready = dict(code_ready=True,rehearsal_evidence_present=True,activation_state='ACTIVATED',
                     target=body['runtime_target'],synthetic_storage_fixture=True)
        body['readiness']['assessment_sha256'] = digest(ready)
        subject = {k:deepcopy(body[k]) for k in s.SUBJECT_FIELDS if k not in ('readiness','reason')}
        subject.update(readiness=ready, reason=ceremony['reason'])
        if subject_owner is not None:subject['runtime_target']['owner_id']=subject_owner
        step = dict(format=s.STEP,token_sha256=digest(dict(synthetic='step')),subject=subject,subject_sha256=digest(subject),
            actor_id=scope['owner_id'],**{k:body['authentication'][k] for k in ('primary_sha256','session_sha256')},
            issued_at_utc=now,expires_at_utc=(utc(now)+timedelta(seconds=600)).strftime('%Y-%m-%dT%H:%M:%SZ'))
        confirm = dict(step,format=s.CONFIRMATION,token_sha256=ceremony['confirmation_token_sha256'],
                       step_artifact_sha256=digest(step),decision='authorize_runtime_execution')
        ceremony['step_artifact_sha256'],ceremony['confirmation_artifact_sha256'] = digest(step),digest(confirm)
        a._audit(conn,s.STEP_ACTION,scope['owner_id'] if step_audit_actor is None else step_audit_actor,now,step)
        a._audit(conn,s.CONFIRM_ACTION,scope['owner_id'],now,confirm)
        conn.execute('INSERT INTO recognition_admin_confirmations VALUES(?,?,?,?,?,?,?,?,1)',
            (ceremony['confirmation_token_sha256'],body['authentication']['session_sha256'],scope['owner_id'],
             'runtime-authority:'+body['operation_reference']['operation_id'],body['operation_reference']['operation_sha256'],
             digest(subject),scope['generation'],a.timestamp(confirm['expires_at_utc'])))
        a._audit(conn,s.CONSUME_ACTION,scope['owner_id'],now,dict(format='recognition-runtime-authority-confirmation-consumption-v1',
            token_sha256=ceremony['confirmation_token_sha256'],artifact_sha256=digest(confirm),subject_sha256=digest(subject)))
        sequence = conn.execute('SELECT MAX(sequence)+1 FROM recognition_admin_audit').fetchone()[0]
        row = self.row(body,sequence)
        row.update(row_changes or {})
        self.insert(conn,s.AUTHORITIES,row)
        event = self.genesis(body)
        event.update(event_changes or {})
        erow = dict(authority_id=body['authority_id'],sequence=1,state='AUTHORIZED',kind='AUTHORIZE',at=row['issued_at'],
            previous_sha256=None,entry_sha256=None,seal_sha256=None,receipt_sha256=None,
            body_json=canonical(event),body_sha256=digest(event),audit_sequence=sequence)
        if include_genesis:self.insert(conn,s.LIFECYCLE,erow)
        if issue:
            a._audit(conn,s.ISSUE_ACTION,scope['owner_id'],now,dict(authority_id=body['authority_id'],authority_sha256=digest(body),
                                                              event_sequence=1,event_sha256=digest(event)))
            base.check_control(conn)
        return row,erow

    def test_codec_deterministic_canonical_roundtrip_and_exact_evidence(self):
        body = self.body(); encoded = canonical(body); sha = s.authority_digest(body)
        self.assertEqual(body,s.parse_authority(encoded,authority_sha256=sha))
        self.assertEqual(sha,s.authority_digest(json.loads(encoded)))
        event = self.genesis(body)
        self.assertEqual(event,s.parse_genesis(canonical(event),event_sha256=digest(event),authority=body))
        self.assertEqual({'format','authority_id','authority_sha256'},set(event['evidence']))
        for serialized in (encoded+' ',encoded[:-1]+',"format":"'+s.FORMAT+'"}',encoded.replace('"generation":3','"generation":3.0')):
            with self.subTest(serialized=serialized[-30:]),self.assertRaises(ValueError):
                s.parse_authority(serialized,authority_sha256=sha)
        with self.assertRaises(ValueError):s.parse_authority(encoded,authority_sha256='0'*64)

    def test_every_required_and_unknown_field_and_wrong_type(self):
        body=self.body()
        for key in body:
            changed=deepcopy(body);del changed[key]
            with self.subTest(key=key),self.assertRaises(ValueError):s.validate_authority(changed)
        for key in ('activation','runtime_target','operation_reference','approval','authentication','physical_snapshot',
                    'producer_ceremony','dependencies','emergency_stop','readiness'):
            changed=deepcopy(body);changed[key]['extra']='not allowed'
            with self.subTest(key=key),self.assertRaises(ValueError):s.validate_authority(changed)
        for value in (None,True,1,[],{},body['authority_id']+'\0','AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE'):
            changed=deepcopy(body);changed['authority_id']=value
            with self.subTest(value=value),self.assertRaises(ValueError):s.validate_authority(changed)

    def test_digests_nul_numbers_time_and_lifetime(self):
        body=self.body()
        cases=[('activation','event_sha256','a'*64+'\0'),('activation','event_sha256','A'*64),
               ('activation','sequence',True),('runtime_target','generation',3.0),
               ('runtime_target','owner_id',True),('authentication','actor_id',2),
               ('producer_ceremony','reason','bad\0reason'),('readiness','assessed_at_utc','yesterday')]
        for group,key,value in cases:
            changed=deepcopy(body);changed[group][key]=value
            with self.subTest(group=group,key=key),self.assertRaises(ValueError):s.validate_authority(changed)
        for seconds in (0,-1,121):
            changed=deepcopy(body);changed['expires_at_utc']=(utc(body['issued_at_utc'])+timedelta(seconds=seconds)).strftime('%Y-%m-%dT%H:%M:%SZ')
            with self.subTest(seconds=seconds),self.assertRaises(ValueError):s.validate_authority(changed)
        for value in ('2099-01-01T00:00:00+00:00','2099-01-01T00:00:00.0Z','bad',True):
            changed=deepcopy(body);changed['issued_at_utc']=value
            with self.subTest(time=value),self.assertRaises(ValueError):s.validate_authority(changed)

    def test_scope_digests_and_physical_lossless_values(self):
        body=self.body()
        for group in ('dependencies','emergency_stop'):
            changed=deepcopy(body);changed[group]['snapshot_sha256']='0'*64
            with self.subTest(group=group),self.assertRaises(ValueError):s.validate_authority(changed)
        changed=deepcopy(body);changed['operation_reference']['proposal_reference']['operation_id']=str(uuid4())
        with self.assertRaises(ValueError):s.validate_authority(changed)
        for physical in ('target','control'):
            changed=deepcopy(body)
            observed=changed['physical_snapshot']['target']['observation'] if physical=='target' else changed['physical_snapshot']['control_identity']
            observed['device']=2**80;observed['inode']=2**90
            self.assertEqual(changed,s.parse_authority(canonical(changed),authority_sha256=digest(changed)))
            for bad in (True,1.0,-1,'58\0'):
                observed['device']=bad
                with self.subTest(physical=physical,bad=bad),self.assertRaises(ValueError):s.validate_authority(changed)

    def test_genesis_rejects_every_later_state_and_evidence_extension(self):
        body=self.body();event=self.genesis(body)
        for state in ('EXECUTING','COMMITTED','COMPLETED','FAILED','FAILED_BEFORE_COMMIT','RECOVERY_REQUIRED','UNCERTAIN'):
            changed=deepcopy(event);changed['state']=state
            with self.subTest(state=state),self.assertRaises(ValueError):s.validate_genesis(changed,authority=body)
        for key,value in (('extra','bad'),('issued_at_utc',body['issued_at_utc']),('format','later-v1'),
                          ('authority_id',str(uuid4())),('authority_sha256','0'*64)):
            changed=deepcopy(event);changed['evidence'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):s.validate_genesis(changed,authority=body)
        for key in event['evidence']:
            changed=deepcopy(event);del changed['evidence'][key]
            with self.subTest(missing=key),self.assertRaises(ValueError):s.validate_genesis(changed,authority=body)
        for key,value in (('sequence',True),('actor_id',True),('entry_sha256','a'*64),('reason','different'),('operation_id',str(uuid4()))):
            changed=deepcopy(event);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):s.validate_genesis(changed,authority=body)

    def _clean(self,mode):
        for path in (self.config.target,self.config.control):
            with closing(sqlite3.connect(path)) as conn:conn.execute('PRAGMA journal_mode='+mode)
        before=self.dump(self.config.target)
        with a.connect(self.config.control) as conn:
            protected={name:[tuple(r) for r in conn.execute('SELECT * FROM '+name)] for name in
                ('recognition_runtime_execution_claims','recognition_runtime_execution_claim_history',
                 'recognition_admin_bindings','recognition_admin_primary','recognition_admin_sessions','recognition_admin_mfa',
                 'recognition_admin_confirmations','recognition_admin_stepups','recognition_approvals','recognition_approval_history')}
            old_audits=[tuple(r) for r in conn.execute('SELECT * FROM recognition_admin_audit')]
        leases=dict(writer_boundary._leases),dict(writer_boundary._local_leases),dict(production_operations._contexts)
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('no key contents')):
            self.assertTrue(self.migrate()['installed'])
        with a.connect(self.config.control) as conn:
            base.check_control(conn)
            for name,sql in s.definitions().items():
                self.assertEqual(' '.join(sql.split()),' '.join(conn.execute('SELECT sql FROM sqlite_master WHERE name=?',(name,)).fetchone()[0].split()))
            self.assertEqual((0,0),tuple(conn.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in (s.AUTHORITIES,s.LIFECYCLE)))
            self.assertEqual(protected,{name:[tuple(r) for r in conn.execute('SELECT * FROM '+name)] for name in protected})
            self.assertEqual(old_audits,[tuple(r) for r in conn.execute('SELECT * FROM recognition_admin_audit WHERE sequence<=?',(len(old_audits),))])
            self.assertEqual('ok',conn.execute('PRAGMA integrity_check').fetchone()[0])
            self.assertFalse(conn.execute('PRAGMA foreign_key_check').fetchone())
        self.assertEqual(before,self.dump(self.config.target))
        self.assertEqual(leases,(dict(writer_boundary._leases),dict(writer_boundary._local_leases),dict(production_operations._contexts)))
        after=self.dump(self.config.control)
        self.assertFalse(self.migrate()['installed'])
        self.assertEqual(after,self.dump(self.config.control))
        # Old 4d-1 migration still recognizes its original immutable manifest.
        with patch.object(a,'target_identity',side_effect=authorization.target_identity):
            self.assertFalse(claims.migrate(self.config,expected_generation=3,operator='fixture',reason='inspect only')['installed'])

    def test_clean_delete_idempotent_empty_and_legacy_isolation(self):self._clean('DELETE')
    def test_clean_wal_idempotent_empty_and_legacy_isolation(self):self._clean('WAL')

    def test_populated_old_claim_history_is_untouched(self):
        receipt=self.f.f.acquire()
        from src.review.recognition import runtime_claim_consumption as consume
        with consume.consume(self.config,receipt,self.f.f.snapshot,self.f.session,primary_token=self.f.primary):pass
        before=self.dump(self.config.target)
        with a.connect(self.config.control) as conn:
            old={name:[tuple(r) for r in conn.execute('SELECT * FROM '+name)] for name in (claims.CLAIMS,claims.HISTORY)}
        self.migrate()
        with a.connect(self.config.control) as conn:
            self.assertEqual(old,{name:[tuple(r) for r in conn.execute('SELECT * FROM '+name)] for name in old})
            base.check_control(conn)
        self.assertEqual(before,self.dump(self.config.target))

    def test_partial_incompatible_and_missing_install_audit_fail_closed(self):
        with a.connect(self.config.control,write=True) as conn:
            conn.execute(f'CREATE TABLE {s.AUTHORITIES}(wrong TEXT)');conn.commit()
        before=self.dump(self.config.control)
        with self.assertRaises(ValueError):self.migrate()
        self.assertEqual(before,self.dump(self.config.control))

    def test_wrong_generation_identity_and_active_state_reject(self):
        before=self.dump(self.config.control)
        with self.assertRaises(ValueError):self.migrate(expected_generation=2)
        with self.assertRaisesRegex(ValueError,'control_identity_mismatch'):
            s.migrate(self.config,expected_generation=3,operator='fixture',reason='runtime is not deployment')
        self.assertEqual(before,self.dump(self.config.control))
        self.f.activate_fixture()
        before=self.dump(self.config.control)
        with self.assertRaisesRegex(ValueError,'requires_not_activated'):self.migrate()
        self.assertEqual(before,self.dump(self.config.control))

    def test_ddl_and_audit_rollback_completely(self):
        before=self.dump(self.config.control),self.dump(self.config.target)
        definitions=s.definitions
        for stage in ('ddl','audit','final'):
            if stage=='ddl':
                altered=dict(list(definitions().items())[:2]);altered['broken']='CREATE TABLE invalid syntax'
                patcher=patch.object(s,'definitions',return_value=altered)
            elif stage=='audit':patcher=patch.object(a,'_audit',side_effect=OSError('synthetic audit failure'))
            else:patcher=patch.object(s,'check_rows',side_effect=ValueError('synthetic final validation'))
            with self.subTest(stage=stage),patcher,self.assertRaises(Exception):self.migrate()
            self.assertEqual(before,(self.dump(self.config.control),self.dump(self.config.target)))

    def test_valid_synthetic_graph_and_immutable_every_collision(self):
        body=self.prepare_graph()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN');row,event=self.graph(conn,body)
            for table,original in ((s.AUTHORITIES,row),(s.LIFECYCLE,event)):
                for sql in (f'UPDATE {table} SET body_json=body_json',f'DELETE FROM {table}'):
                    with self.subTest(sql=sql),self.assertRaises(sqlite3.IntegrityError):conn.execute(sql)
                keys=('authority_id','operation_id','writer_manifest_sha256','confirmation_sha256','body_sha256','audit_sequence') if table==s.AUTHORITIES else ('authority_id','body_sha256','audit_sequence')
                # Isolate each immutable collision guard from the scope guard,
                # so a bad scope cannot provide false confidence. SQLite does
                # not promise ordering among different BEFORE triggers.
                guard=table+('_scope_guard' if table==s.AUTHORITIES else '_sequence_guard')
                sql=conn.execute('SELECT sql FROM sqlite_master WHERE name=?',(guard,)).fetchone()[0]
                conn.execute('DROP TRIGGER '+guard)
                for key in keys:
                    candidate=deepcopy(original)
                    for column in keys:
                        if column!=key:
                            candidate[column]=(original[column]+100 if column=='audit_sequence' else
                                               str(uuid4()) if column.endswith('_id') else digest(dict(column=column,key=key)))
                    with self.subTest(table=table,key=key),self.assertRaisesRegex(sqlite3.IntegrityError,'immutable_runtime_activation_authority'):
                        self.insert(conn,table,candidate,True)
                conn.execute(sql)
            base.check_control(conn)
            self.assertFalse(writer_boundary.verify_local(body,self.config.target,{}))
            with self.assertRaisesRegex(ValueError,'runtime_profile_contract_not_enabled'):a._binding(conn)

    def test_scope_guards_and_foreign_keys(self):
        body=self.prepare_graph()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN')
            for key,value in (('authority_id','bad\0'),('generation',2),('owner_id',2),('auth_epoch',2),('mfa_epoch',2),
                ('installation_id',str(uuid4())),('target_id',str(uuid4())),('profile_sha256','0'*64),
                ('activation_sequence',999),('activation_sha256','0'*64),('approval_id',str(uuid4())),
                ('approval_sha256','0'*64),('expires_at',a.timestamp(body['issued_at_utc'])+121),('confirmation_sha256','0'*64),
                ('audit_sequence',1)):
                conn.execute('SAVEPOINT bad_scope')
                with self.subTest(key=key),self.assertRaises(sqlite3.IntegrityError):
                    self.graph(conn,deepcopy(body),row_changes={key:value})
                conn.execute('ROLLBACK TO bad_scope');conn.execute('RELEASE bad_scope')
            self.graph(conn,deepcopy(body))  # Same graph, no corrupted column, really succeeds.

    def test_genesis_fk_later_state_extra_evidence_and_missing_audit(self):
        body=self.prepare_graph()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN');row,event=self.graph(conn,body)
            conn.rollback()
            with self.assertRaises(sqlite3.IntegrityError):self.insert(conn,s.LIFECYCLE,event)
            conn.rollback();conn.execute('BEGIN')
            for state in ('EXECUTING','COMMITTED','COMPLETED','FAILED_BEFORE_COMMIT','RECOVERY_REQUIRED'):
                conn.execute('SAVEPOINT bad_event')
                with self.subTest(state=state),self.assertRaises(sqlite3.IntegrityError):
                    self.graph(conn,deepcopy(body),event_changes={'state':state})
                conn.execute('ROLLBACK TO bad_event');conn.execute('RELEASE bad_event')
            extra=dict(self.genesis(body)['evidence'],extra='not permitted')
            conn.execute('SAVEPOINT extra_evidence')
            with self.assertRaises(sqlite3.IntegrityError):self.graph(conn,deepcopy(body),event_changes={'evidence':extra})
            conn.execute('ROLLBACK TO extra_evidence');conn.execute('RELEASE extra_evidence')
            self.graph(conn,deepcopy(body),issue=False)
            with self.assertRaisesRegex(ValueError,'audit_missing'):s.check_rows(conn)
            with self.assertRaises(sqlite3.IntegrityError):conn.commit()  # Deferred audit FK is real.

    def test_genesis_is_required_by_deferred_audit_protocol_not_just_reader(self):
        body=self.prepare_graph()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN');row,event=self.graph(conn,body,issue=False,include_genesis=False)
            with self.assertRaisesRegex(ValueError,'genesis_missing'):s.check_rows(conn)
            with self.assertRaisesRegex(sqlite3.IntegrityError,'audit_mismatch'):
                a._audit(conn,s.ISSUE_ACTION,body['runtime_target']['owner_id'],body['issued_at_utc'],
                    dict(authority_id=body['authority_id'],authority_sha256=digest(body),event_sequence=1,event_sha256=event['body_sha256']))
            with self.assertRaises(sqlite3.IntegrityError):conn.commit()

    def test_populated_legacy_target_storage_unchanged(self):
        oid=self.observed['proposal']['operation_id'];marker=canonical(dict(synthetic_storage_only=True))
        with a.connect(self.config.target,write=True) as conn:
            conn.execute('INSERT INTO recognition_execution_claims VALUES(?,?,?)',(oid,marker,digest(marker)))
            conn.execute('INSERT INTO recognition_execution_seals VALUES(?,?,?,?)',(oid,'1'*64,marker,digest(marker)))
            conn.execute('INSERT INTO recognition_execution_audit VALUES(?,?,?,?,?,?)',(oid,1,'EXECUTING','EXECUTION',marker,digest(marker)))
            conn.execute('INSERT INTO recognition_operation_receipts VALUES(?,?,?)',(oid,marker,digest(marker)))
            conn.commit()
        before=self.dump(self.config.target)
        self.migrate()
        self.assertEqual(before,self.dump(self.config.target))

    def test_old_manifest_cannot_be_rewritten_to_match_new_schema(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN')
            trigger='recognition_admin_audit_immutable_update'
            sql=conn.execute('SELECT sql FROM sqlite_master WHERE name=?',(trigger,)).fetchone()[0]
            conn.execute('DROP TRIGGER '+trigger)
            previous=None
            for row in conn.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence').fetchall():
                body=json.loads(row['body_json']);body['previous_sha256']=previous
                if body['action']==claims.ACTION:body['subject']['installed_schema_sha256']=claims.manifest(conn)
                previous=digest(body)
                conn.execute('UPDATE recognition_admin_audit SET body_json=?,body_sha256=? WHERE sequence=?',
                             (canonical(body),previous,row['sequence']))
            conn.execute(sql)  # Restore EXACT DDL; failure must be historical manifest, not absent trigger.
            with self.assertRaisesRegex(ValueError,'migration_predecessor'):base.check_control(conn)

    def test_missing_extension_objects_cannot_hide_installation_audit(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            for name,sql in s.definitions().items():
                if sql.startswith('CREATE TRIGGER'):conn.execute('DROP TRIGGER '+name)
            conn.execute('DROP TABLE '+s.LIFECYCLE);conn.execute('DROP TABLE '+s.AUTHORITIES);conn.commit()
        with self.assertRaisesRegex(ValueError,'schema_mismatch'):self.migrate()

    def test_manifest_rejects_extra_or_missing_objects_and_no_audit_repair(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('CREATE TABLE unexpected(value TEXT)');conn.commit()
        before=self.dump(self.config.control)
        with self.assertRaises(ValueError):self.migrate()
        self.assertEqual(before,self.dump(self.config.control))

    def test_coherent_foreign_scope_and_physical_observations_reject(self):
        body=self.prepare_graph()
        cases=[]
        for group,key,value in (('runtime_target','generation',2),('runtime_target','runtime_profile_sha256','0'*64),
            ('runtime_target','installation_id',str(uuid4())),('runtime_target','target_id',str(uuid4())),
            ('activation','event_sha256','0'*64),('activation','sequence',1)):
            changed=deepcopy(body);changed[group][key]=value;cases.append((group+'.'+key,changed))
        for prefix in ('target','control'):
            for key in ('hostname','database','device','inode'):
                changed=deepcopy(body)
                physical=changed['physical_snapshot']['target']['observation'] if prefix=='target' else changed['physical_snapshot']['control_identity']
                physical[key]=(physical[key]+1 if key in ('device','inode') else str(self.config.target.parent/'other.sqlite') if key=='database' else 'other-worker')
                cases.append((prefix+'.'+key,changed))
        changed=deepcopy(body);changed['physical_snapshot']['target']['schema_sha256']='0'*64;cases.append(('schema',changed))
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN')
            for label,changed in cases:
                conn.execute('SAVEPOINT foreign_scope')
                with self.subTest(field=label),self.assertRaises(sqlite3.IntegrityError):self.graph(conn,changed)
                conn.execute('ROLLBACK TO foreign_scope');conn.execute('RELEASE foreign_scope')
            self.graph(conn,deepcopy(body))

    def test_history_survives_revocation_and_generation_change_without_granting_authority(self):
        body=self.prepare_graph()
        from src.review.recognition import local_execution
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN');self.graph(conn,body)
            conn.execute('UPDATE recognition_admin_primary SET revoked=1')
            conn.execute('UPDATE recognition_admin_sessions SET revoked=1')
            conn.execute('UPDATE recognition_admin_mfa SET epoch=epoch+1')
            old=json.loads(conn.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
            new=dict(old,generation=old['generation']+1,previous_sha256=digest(old),runtime_profile_sha256=None)
            conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(new['generation'],canonical(new),digest(new)))
            base.check_control(conn)  # Historical integrity is not current permission.
            conn.commit()
        with a.connect(self.config.control) as conn:
            base.check_control(conn)
        for value in (body,self.genesis(body),self.genesis(body)['evidence']):
            self.assertFalse(writer_boundary.verify_local(value,self.config.target,{}))
            result=local_execution.execute_approved_operation(value,self.f.session,body['approval']['approval_id'],now=runtime._utc_now())
            self.assertEqual('BLOCKED',result.admission)
        self.assertFalse(local_readiness.assess(self.config,now=runtime._utc_now())['activation_ready'])

    def test_minimum_original_ceremony_and_auth_deadline_is_not_caller_selected(self):
        body=self.prepare_graph()
        body['expires_at_utc']=(utc(body['issued_at_utc'])+timedelta(seconds=119)).strftime('%Y-%m-%dT%H:%M:%SZ')
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN')
            with self.assertRaisesRegex(ValueError,'lifetime_extension'):self.graph(conn,body)

    def test_consent_integer_boolean_alias_is_not_equal_canonical_scope(self):
        body=self.prepare_graph()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN')
            with self.assertRaisesRegex(ValueError,'confirmation_scope'):self.graph(conn,body,subject_owner=True)

    def test_consent_audit_actor_boolean_is_not_an_owner_integer(self):
        body=self.prepare_graph()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN')
            with self.assertRaisesRegex(ValueError,'integer'):self.graph(conn,body,step_audit_actor=True)

    def test_python_row_validation_rejects_boolean_event_sequence_even_after_hash_repair(self):
        body=self.prepare_graph()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN');row,event=self.graph(conn,body)
            trigger='recognition_admin_audit_immutable_update'
            sql=conn.execute('SELECT sql FROM sqlite_master WHERE name=?',(trigger,)).fetchone()[0]
            audit=json.loads(conn.execute('SELECT body_json FROM recognition_admin_audit WHERE sequence=?',(row['audit_sequence'],)).fetchone()[0])
            audit['subject']['event_sequence']=True
            conn.execute('DROP TRIGGER '+trigger)
            conn.execute('UPDATE recognition_admin_audit SET body_json=?,body_sha256=? WHERE sequence=?',
                         (canonical(audit),digest(audit),row['audit_sequence']))
            conn.execute(sql)
            with self.assertRaisesRegex(ValueError,'audit_scope'):base.check_control(conn)

    def test_uncertain_or_silent_commit_never_claims_a_new_success(self):
        connect=a.sqlite3.connect
        for stage in ('before','silent','after'):
            if stage=='after':
                # Earlier cases must have rolled back ALL storage and audit.
                with a.connect(self.config.control) as conn:
                    self.assertFalse(conn.execute('SELECT 1 FROM sqlite_master WHERE name=?',(s.AUTHORITIES,)).fetchone())
            class Lost(sqlite3.Connection):
                def commit(conn):
                    if stage=='after':super().commit()
                    if stage!='silent':raise OSError('synthetic commit acknowledgement loss')
            def factory(*args,**kwargs):
                if str(args[0]).startswith(self.config.control.resolve().as_uri()):kwargs['factory']=Lost
                return connect(*args,**kwargs)
            with self.subTest(stage=stage),patch.object(a.sqlite3,'connect',side_effect=factory),self.assertRaises((OSError,ValueError)):
                self.migrate()
            with a.connect(self.config.control) as conn:
                present=bool(conn.execute('SELECT 1 FROM sqlite_master WHERE name=?',(s.AUTHORITIES,)).fetchone())
                self.assertEqual(stage=='after',present)
                if present:
                    base.check_control(conn)
                    self.assertEqual(0,conn.execute('SELECT count(*) FROM '+s.AUTHORITIES).fetchone()[0])

    def test_postcommit_verification_failure_leaves_atomic_inspectable_storage(self):
        original=a.connect;connect=a.sqlite3.connect;committed=False
        class Committed(sqlite3.Connection):
            def commit(conn):
                nonlocal committed
                super().commit();committed=True
        def factory(*args,**kwargs):
            if str(args[0]).startswith(self.config.control.resolve().as_uri()) and 'mode=rw' in str(args[0]):
                kwargs['factory']=Committed
            return connect(*args,**kwargs)
        @contextmanager
        def connected(path,**kwargs):
            if committed and path==self.config.control and not kwargs.get('write'):
                raise OSError('synthetic postcommit verification failure')
            with original(path,**kwargs) as conn:yield conn
        with patch.object(a.sqlite3,'connect',side_effect=factory),patch.object(a,'connect',side_effect=connected),self.assertRaises(OSError):
            self.migrate()
        with a.connect(self.config.control) as conn:
            base.check_control(conn)
            self.assertEqual(0,conn.execute('SELECT count(*) FROM '+s.AUTHORITIES).fetchone()[0])
            self.assertEqual(1,len(s._rows(conn,s.ACTION)))
        self.assertFalse(self.migrate()['installed'])

    def _interrupted_migration(self,mode):
        for index,stage in enumerate(('before_commit','committed')):
            if index:self.doCleanups();self.setUp()
            for path in (self.config.target,self.config.control):
                with closing(sqlite3.connect(path)) as conn:conn.execute('PRAGMA journal_mode='+mode)
            target_before=self.dump(self.config.target)
            options=dict(paths=[str(self.config.target),str(self.config.control),str(self.config.key_file)],
                         now=runtime._utc_now(),stage=stage)
            child=subprocess.Popen([sys.executable,'-B','-u','-c',_MIGRATION_CHILD],stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                child.stdin.write(json.dumps(options)+'\n');child.stdin.flush()
                line=child.stdout.readline().strip()
                if line!='BOUNDARY':
                    _,error=child.communicate(timeout=30);self.fail('migration child failed: '+line+' '+error)
                child.kill();child.wait(timeout=30);child.communicate(timeout=30)
            finally:
                if child.poll() is None:child.kill();child.wait(timeout=30);child.communicate(timeout=30)
            # Ordinary SQLite rollback/recovery only. No checkpoint, sidecar
            # deletion, repair, retry or production lifecycle intervention.
            with a.connect(self.config.control,write=True) as conn:
                conn.execute('BEGIN IMMEDIATE');base.check_control(conn)
                self.assertEqual(stage=='committed',bool(conn.execute('SELECT 1 FROM sqlite_master WHERE name=?',(s.AUTHORITIES,)).fetchone()))
                if stage=='committed':self.assertEqual(0,conn.execute('SELECT count(*) FROM '+s.AUTHORITIES).fetchone()[0])
            self.assertEqual(target_before,self.dump(self.config.target))

    def test_process_interruption_delete(self):self._interrupted_migration('DELETE')
    def test_process_interruption_wal(self):self._interrupted_migration('WAL')

    def test_target_readonly_and_commit_order(self):
        original=a.connect;connect=a.sqlite3.connect;denied=[];target_events=[]
        class Probe(sqlite3.Connection):
            def commit(conn):
                if conn.execute('PRAGMA database_list').fetchone()[2]==str(self.config.control):
                    with closing(connect(self.config.target,timeout=0)) as competitor:
                        with self.assertRaises(sqlite3.OperationalError):competitor.execute('BEGIN IMMEDIATE')
                else:target_events.append('commit')
                return super().commit()
        def factory(*args,**kwargs):kwargs['factory']=Probe;return connect(*args,**kwargs)
        @contextmanager
        def guarded(path,**kwargs):
            with original(path,**kwargs) as conn:
                if path==self.config.target:
                    def authorizer(action,*args):
                        if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
                            denied.append(action);return sqlite3.SQLITE_DENY
                        return sqlite3.SQLITE_OK
                    conn.set_authorizer(authorizer)
                else:
                    protected=set(base.TABLES)-{'recognition_admin_audit'}
                    protected.update((claims.CLAIMS,claims.HISTORY,'recognition_approvals','recognition_approval_history',
                                      'recognition_runtime_auth_bindings','recognition_runtime_profiles','recognition_runtime_enrollment_challenges'))
                    def protect(action,table,*args):
                        if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) and table in protected:
                            denied.append((action,table));return sqlite3.SQLITE_DENY
                        return sqlite3.SQLITE_OK
                    conn.set_authorizer(protect)
                yield conn
        with patch.object(a.sqlite3,'connect',side_effect=factory),patch.object(a,'connect',side_effect=guarded):
            self.migrate()
        self.assertEqual([],denied);self.assertEqual([],target_events)

    def test_concurrent_idempotent_migration(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        barrier=threading.Barrier(2)
        def migrate():
            barrier.wait(timeout=10)
            return s.migrate(self.config,expected_generation=3,operator='fixture',reason='concurrent inert storage')['installed']
        with patch.object(a,'target_identity',side_effect=authorization.target_identity),ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual([False,True],sorted(pool.map(lambda _:migrate(),range(2))))
        with a.connect(self.config.control) as conn:
            self.assertEqual(1,len(s._rows(conn,s.ACTION)));base.check_control(conn)


_MIGRATION_CHILD = r'''
import json,sys,os,tempfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname
options=json.loads(sys.stdin.readline())
roots=(Path(tempfile.gettempdir()).resolve(),Path.cwd()/'.tmp',Path.cwd()/'tests')
assert all(any(Path(p).resolve().is_relative_to(r) for r in roots) for p in options['paths'])
databases={Path(p).resolve() for p in options['paths'][:2]}
def guard(event,args):
    if event=='sqlite3.connect':
        raw=os.fsdecode(os.fspath(args[0]))
        if raw.startswith('file:'):
            uri=urlsplit(raw)
            if uri.netloc not in ('','localhost'):raise PermissionError('nonlocal_database_denied')
            raw=url2pathname(uri.path)
        if Path(raw).resolve() not in databases:raise PermissionError('nonfixture_database_denied')
    elif event in ('socket.connect','socket.getaddrinfo'):raise PermissionError('network_denied')
sys.addaudithook(guard)
from src.review.recognition import administration as a,runtime_validation as v,runtime_activation_authority_schema as s
v._utc_now=lambda:options['now']
def no_key(*args,**kwargs):raise AssertionError('key_read_denied')
Path.read_bytes=no_key
original=a._audit
def audit(*args,**kwargs):
    original(*args,**kwargs)
    if args[1]==s.ACTION and options['stage']=='before_commit':
        print('BOUNDARY',flush=True);sys.stdin.readline()
a._audit=audit
s.migrate(a.LocalAdministration(*(Path(p) for p in options['paths'])),expected_generation=3,
          operator='disposable-child',reason='inert migration interruption')
print('BOUNDARY',flush=True);sys.stdin.readline()
'''
