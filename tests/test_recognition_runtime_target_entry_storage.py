"""Inert package tests: new temporary SQLite files only, no deployment ceremony."""

from copy import deepcopy
from pathlib import Path
import sqlite3
import tempfile
import unittest
from uuid import uuid4

from src.review.recognition import runtime_target_entry_storage as s
from src.review.recognition import event_schema, operation_schema, enrollment
from src.review.recognition import runtime_operation_contract as operation
from src.review.recognition import runtime_execution_attempt_schema as attempts
from src.review.recognition import runtime_activation_authority_schema as authority
from src.review.recognition.rules import canonical, digest


def graph():
    """Detached synthetic source DATA, never durable authority or authentication."""
    uid = lambda: str(uuid4())
    now, end = '2099-01-01T00:00:00Z', '2099-01-01T00:02:00Z'
    op = uid()
    reference = dict(operation_id=op, operation_sha256='a'*64, event_id=uid(), event_sha256='b'*64,
        preparation_id=uid(), preparation_sha256='c'*64, writer_family='first_look',
        writer_manifest_sha256='d'*64, population_sha256='e'*64,
        proposal_reference=dict(format='recognition-runtime-proposal-reference-v1', operation_id=op,
            operation_sha256='a'*64, acknowledgement_sequence=1, acknowledgement_sha256='f'*64))
    from src.review.recognition import runtime_proposal_records as records, dependencies
    reference['proposal_reference']['format'] = records.REFERENCE_FORMAT
    target = dict(format=operation.TARGET_FORMAT, installation_id=uid(), target_id=uid(), generation=3,
        owner_id=1, binding_sha256='a'*64, runtime_profile_sha256='b'*64, auth_epoch=1, mfa_epoch=1)
    physical = dict(hostname='synthetic-runtime', database='/disposable/target.db', device=2**80, inode=2**81)
    dep = dict(format=dependencies.FORMAT, family='first_look', manifest_sha256='d'*64,
        boundary=dependencies.BOUNDARY, observations={k:None for k in ('assignment_inventory','review_evidence',
            'completions','qualification_rules','existence','identity','current_active','policy','permanent_records','scope_snapshot')})
    dep['sha256'] = digest(dep)
    stop = dict(sequence=1, active=False, reason='synthetic stop data', actor='test', recorded_at_utc=now, previous_sha256=None)
    source = dict(format=authority.FORMAT, authority_id=uid(), operation_reference=reference,
        runtime_target=target, physical_snapshot=dict(target=dict(observation=physical, schema_sha256='c'*64),
            control_identity=dict(physical, database='/disposable/control.db')),
        activation=dict(sequence=1,event_sha256='d'*64),
        approval=dict(approval_id=uid(),approval_sha256='e'*64,effective_history_sha256='f'*64),
        authentication=dict(actor_id=1,primary_sha256='a'*64,session_sha256='b'*64),
        producer_ceremony=dict(step_artifact_sha256='c'*64,confirmation_artifact_sha256='d'*64,
            confirmation_token_sha256='e'*64,decision='authorize_runtime_execution',reason='synthetic DATA'),
        dependencies=dict(snapshot=dep,snapshot_sha256=digest(dep)),
        emergency_stop=dict(snapshot=stop,snapshot_sha256=digest(stop)),
        readiness=dict(assessment_sha256='f'*64,assessed_at_utc=now,policy=authority.READINESS),
        issued_at_utc=now,expires_at_utc=end,lifetime_policy=authority.LIFETIME)
    attempt = dict(format=attempts.FORMAT,attempt_id=uid(),authority_id=source['authority_id'],
        authority_sha256=digest(source),created_at_utc=now,expires_at_utc=end)
    event = dict(format=attempts.EVENT_FORMAT,attempt_id=attempt['attempt_id'],attempt_sha256=digest(attempt),
        sequence=1,state='ATTEMPT_CREATED',at_utc=now,previous_sha256=None,actor_id=1,reason='synthetic DATA')
    entry = dict(format=s.FORMAT,state='TARGET_ENTRY_CREATED',attempt_id=attempt['attempt_id'],
        attempt_sha256=digest(attempt),creation_event_sha256=digest(event),authority_id=source['authority_id'],
        authority_sha256=digest(source),entered_at_utc=now,expires_at_utc=end,
        **{k:deepcopy(source[k]) for k in s.SCOPE_FIELDS})
    return entry, dict(authority_body=source,attempt=attempt,creation_event=event)


class TargetEntryStorageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.path = Path(temp.name)/'target.db'
        self.conn = sqlite3.connect(self.path); self.addCleanup(self.conn.close)
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.execute('PRAGMA recursive_triggers=OFF')
        for module in (event_schema, operation_schema):
            for sql in module.definitions().values(): self.conn.execute(sql)
        self.before = enrollment._schema(self.conn)
        for sql in s.definitions().values(): self.conn.execute(sql)
        self.body, self.sources = graph()
        ref = self.body['operation_reference']
        self.conn.execute('INSERT INTO recognition_preparations VALUES (?,?,?,?)', (ref['preparation_id'],None,'{}','a'*64))
        self.conn.execute('INSERT INTO recognition_frozen_events VALUES (?,?,?,?)', (ref['event_id'],ref['preparation_id'],'{}','b'*64))
        self.conn.execute('INSERT INTO recognition_operation_contracts VALUES (?,?,?,?)', (ref['operation_id'],ref['event_id'],'{}','c'*64))
        self.conn.commit()

    def row(self, body=None):
        body = body or self.body
        return (body['attempt_id'],body['operation_reference']['operation_id'],body['authority_sha256'],
            body['operation_reference']['writer_manifest_sha256'],authority._time(body['entered_at_utc']),canonical(body),digest(body))

    def insert(self, row=None, replace=False):
        self.conn.execute(('INSERT OR REPLACE' if replace else 'INSERT')+f' INTO {s.TABLE} VALUES (?,?,?,?,?,?,?)',row or self.row())

    def test_clean_exact_schema_and_deterministic_package(self):
        self.assertEqual(s.package_manifest(),s.check_schema(self.conn))
        self.assertEqual(s.definitions(),s.definitions())
        self.assertEqual(digest(s.definitions()),s.package_manifest()['added_definitions_sha256'])
        self.assertNotEqual(self.before,enrollment._schema(self.conn))
        self.assertEqual(enrollment._schema(self.conn),enrollment._schema(self.conn))
        self.assertEqual(7,len(self.conn.execute(f'PRAGMA table_info({s.TABLE})').fetchall()))
        self.assertEqual(5,len(self.conn.execute(f'PRAGMA index_list({s.TABLE})').fetchall()))
        self.assertEqual('recognition_operation_contracts',self.conn.execute(f'PRAGMA foreign_key_list({s.TABLE})').fetchone()[2])
        self.insert(); self.assertEqual([],self.conn.execute('PRAGMA foreign_key_check').fetchall())

    def test_codec_roundtrip_is_detached_data_and_lossless(self):
        encoded = s.encode_entry(self.body,**self.sources)
        self.assertEqual(self.body,s.parse_entry(encoded,entry_sha256=digest(self.body),**self.sources))
        self.assertEqual(2**81,s.parse_entry(encoded,entry_sha256=digest(self.body),**self.sources)['physical_snapshot']['target']['observation']['inode'])
        self.assertEqual(encoded,s.encode_entry(deepcopy(self.body),**self.sources))

    def test_missing_extra_duplicate_noncanonical_and_tampered_codec(self):
        for key in self.body:
            bad = deepcopy(self.body); del bad[key]
            with self.subTest(missing=key),self.assertRaises(ValueError):s.encode_entry(bad,**self.sources)
        for text in (canonical(self.body)+' ',canonical(self.body)[:-1]+',"state":"TARGET_ENTRY_CREATED"}',
                     canonical(dict(self.body,extra=True))):
            with self.subTest(text=text[-40:]),self.assertRaises(ValueError):
                s.parse_entry(text,entry_sha256=digest(self.body),**self.sources)
        with self.assertRaises(ValueError):s.parse_entry(canonical(self.body),entry_sha256='0'*64,**self.sources)

    def test_invalid_scalars_lifetime_and_complete_scope(self):
        cases = [('attempt_id','bad'),('authority_id',self.body['authority_id']+'\0'),
            ('attempt_sha256','A'*64),('creation_event_sha256','a'*64+'\0'),('authority_sha256','0'*64),
            ('entered_at_utc',True),('entered_at_utc',1.0),('entered_at_utc','2099-01-01T00:00:00+00:00'),
            ('entered_at_utc',self.body['expires_at_utc']),('expires_at_utc','2099-01-01T00:02:01Z')]
        for key,value in cases:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):s.encode_entry(dict(self.body,**{key:value}),**self.sources)
        for group in s.SCOPE_FIELDS:
            for key in self.body[group]:
                bad = deepcopy(self.body); bad[group][key] = None
                with self.subTest(group=group,key=key),self.assertRaises(ValueError):s.encode_entry(bad,**self.sources)
        for key,value in [('generation',True),('owner_id',1.0),('auth_epoch',0),('mfa_epoch',False)]:
            bad = deepcopy(self.body); bad['runtime_target'][key] = value
            with self.subTest(key=key),self.assertRaises(ValueError):s.encode_entry(bad,**self.sources)

    def test_mismatched_attempt_creation_and_sources(self):
        for source,key,value in [('attempt','authority_sha256','0'*64),('attempt','attempt_id',str(uuid4())),
            ('creation_event','actor_id',True),('creation_event','previous_sha256','a'*64),
            ('authority_body','expires_at_utc','2099-01-01T00:01:59Z')]:
            sources = deepcopy(self.sources); sources[source][key] = value
            with self.subTest(source=source,key=key),self.assertRaises(ValueError):s.encode_entry(self.body,**sources)

    def test_immutable_update_delete_replace_every_unique_key(self):
        self.insert(); self.conn.commit()
        before = list(self.conn.execute(f'SELECT * FROM {s.TABLE}'))
        for sql in (f'UPDATE {s.TABLE} SET entered_at=entered_at+1',f'DELETE FROM {s.TABLE}'):
            with self.assertRaises(sqlite3.IntegrityError):self.conn.execute(sql)
        for collision in (0,1,2,3,6):
            row = list(self.row()); row[0]=str(uuid4()); row[1]=str(uuid4()); row[2]='1'*64;row[3]='2'*64;row[6]='3'*64
            row[collision] = self.row()[collision]
            with self.subTest(collision=collision),self.assertRaises(sqlite3.IntegrityError):self.insert(tuple(row),replace=True)
        self.assertEqual(before,list(self.conn.execute(f'SELECT * FROM {s.TABLE}')))

    def test_sql_constraints_and_foreign_key(self):
        for index,value in [(0,'bad'),(0,self.body['attempt_id']+'\0'),(2,'A'*64),(3,'a'*64+'\0'),(4,-1),(4,1.5),(5,'{}')]:
            row=list(self.row());row[index]=value
            with self.subTest(index=index,value=value),self.assertRaises(sqlite3.IntegrityError):self.insert(tuple(row))
        bad=deepcopy(self.body);bad['operation_reference']['operation_id']=str(uuid4())
        with self.assertRaises(sqlite3.IntegrityError):self.insert(self.row(bad))
        bad=deepcopy(self.body);bad['expires_at_utc']=bad['entered_at_utc']
        with self.assertRaises(sqlite3.IntegrityError):self.insert(self.row(bad))

    def test_missing_altered_unexpected_schema_rejected(self):
        name=s.TABLE+'_immutable_delete'; sql=s.definitions()[name]
        self.conn.execute(f'DROP TRIGGER {name}')
        with self.assertRaises(ValueError):s.check_schema(self.conn)
        self.conn.execute(sql.replace('immutable_runtime_target_entry','different'))
        with self.assertRaises(ValueError):s.check_schema(self.conn)
        self.conn.execute(f'DROP TRIGGER {name}');self.conn.execute(sql)
        self.conn.execute(f'CREATE INDEX unexpected_entry_index ON {s.TABLE}(entered_at)')
        with self.assertRaises(ValueError):s.check_schema(self.conn)

    def test_inspection_read_only_and_no_authority_or_installer(self):
        self.conn.commit();before=self.path.read_bytes()
        with sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True) as conn:
            conn.execute('PRAGMA query_only=ON')
            denied={sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_CREATE_TRIGGER}
            conn.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK)
            s.check_schema(conn)
            self.assertEqual(0,conn.total_changes)
        self.assertEqual(before,self.path.read_bytes())
        for name in ('migrate','install','execute','acquire','activate','recover'):
            self.assertFalse(hasattr(s,name))


if __name__ == '__main__':unittest.main()
