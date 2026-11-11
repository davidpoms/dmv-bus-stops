"""R11-E disposable migration/storage graphs, never production authority."""

from contextlib import closing, contextmanager, ExitStack
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as admin, administration_schema as base, authorization
from src.review.recognition import runtime_activation_authority_schema as authority
from src.review.recognition import runtime_authority_lifetime_policy as policy
from src.review.recognition import runtime_schema_package_lineage as lineage
from src.review.recognition import runtime_execution_attempt_schema as attempts
from src.review.recognition import runtime_enrollment_transition_schema as transition
from src.review.recognition import runtime_execution_claim_schema as claims
from src.review.recognition import runtime_validation as runtime, writer_boundary, production_operations
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import utc, TrustError
from tests import test_recognition_runtime_activation_authority_schema as fixtures
from tests import test_recognition_runtime_execution_attempt_schema as attempt_fixtures
from tests.recognition_authorization_fixture import workspace_for


class LifetimePolicyMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Test-scoped allocation only: the already established writable creation
        # mode, never chmod, shared-fixture edits or a global tempfile setting.
        root = Path(__file__).resolve().parents[1]
        original = tempfile.mkdtemp
        def allocate(suffix=None, prefix=None, dir=None):
            if prefix != 'recognition-disposable-' or dir is not None:
                return original(suffix=suffix, prefix=prefix, dir=dir)
            path = root / ('recognition-r11e-'+uuid4().hex+(suffix or ''))
            os.mkdir(path, 0o777)
            return str(path)
        cls.f = fixtures.ActivationAuthoritySchemaTests()
        cls.addClassCleanup(cls.f.doCleanups)
        with patch.object(tempfile, 'mkdtemp', allocate):
            cls.f.setUp()
        cls.config = cls.f.config
        cls.workspace = Path(workspace_for(cls.config.target).name).resolve()
        assert cls.workspace.parent == root and cls.workspace.name.startswith('recognition-r11e-')
        assert all(p.resolve().is_relative_to(cls.workspace) for p in
                   (cls.config.target, cls.config.control, cls.config.key_file))
        cls.f.migrate()
        cls.core = cls.backup()
        cls.addClassCleanup(cls.core.close)
        with patch.object(admin, 'target_identity', side_effect=authorization.target_identity):
            attempts.migrate(cls.config, expected_generation=3, operator='fixture', reason='isolated attempt package')
            cls.at_template = cls.backup()
            cls.addClassCleanup(cls.at_template.close)
            transition.migrate(cls.config, expected_generation=3, operator='fixture', reason='isolated transition package')
        cls.template = cls.backup()
        cls.addClassCleanup(cls.template.close)

    @classmethod
    def backup(cls):
        result = sqlite3.connect(':memory:')
        with admin.connect(cls.config.control) as source:
            source.backup(result)
        return result

    def restore(self, source=None):
        # Explicit same disposable file: do not change inode/path to bypass scope.
        self.assertTrue(self.config.control.resolve().is_relative_to(self.workspace))
        with closing(sqlite3.connect(self.config.control)) as target:
            (self.template if source is None else source).backup(target)

    def setUp(self):
        self.restore()
        self.target_before = self.f.dump(self.config.target)
        self.leases = (dict(writer_boundary._leases), dict(writer_boundary._local_leases),
                       dict(production_operations._contexts))

    def tearDown(self):
        self.assertEqual(self.target_before, self.f.dump(self.config.target))
        self.assertEqual(self.leases, (dict(writer_boundary._leases), dict(writer_boundary._local_leases),
                                      dict(production_operations._contexts)))
        self.assertFalse(self.config.control.parent.joinpath(policy.STAGING).exists())

    def migrate(self, generation=3, **options):
        args = dict(expected_generation=generation, operator='isolated-r11e', reason='disposable compatibility test')
        args.update(options)
        def identity(database):
            return authorization.target_identity(getattr(database, 'conn', database))
        with patch.object(admin, 'target_identity', side_effect=identity), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('no key reads')):
            return policy.migrate(self.config, **args)

    def idle_generation(self, conn):
        old = json.loads(conn.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
        new = dict(old, generation=old['generation']+1, previous_sha256=digest(old), runtime_profile_sha256=None)
        conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',
                     (new['generation'], canonical(new), digest(new)))
        return new['generation']

    def seed(self, *, version=None, clipped=False, with_attempt=True, idle=True):
        if idle:
            # The existing E guard forbids clearing an enrolled profile outside
            # its transition protocol. Seed the historical binding before E is
            # installed, then install E normally on that already-idle generation.
            self.restore(self.at_template)
        activation = self.f.f.activate_fixture()  # Existing explicit synthetic ledger DATA only.
        body = self.f.body(activation)
        if version:
            body['lifetime_policy'] = version
        lifetime = 30 if clipped else policy.seconds(body['lifetime_policy'])
        body['expires_at_utc'] = (utc(body['issued_at_utc'])+timedelta(seconds=lifetime)).strftime('%Y-%m-%dT%H:%M:%SZ')
        with admin.connect(self.config.control, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            if clipped:
                deadline = admin.timestamp(body['expires_at_utc'])
                conn.execute('UPDATE recognition_admin_primary SET expires=? WHERE token_hash=?',
                             (deadline, body['authentication']['primary_sha256']))
                conn.execute('UPDATE recognition_admin_sessions SET expires=? WHERE token_hash=?',
                             (deadline, body['authentication']['session_sha256']))
            real_delta = timedelta
            def artifact_delta(*args, **kwargs):
                if clipped and not args and kwargs == dict(seconds=600):
                    return real_delta(seconds=30)
                return real_delta(*args, **kwargs)
            with patch.object(fixtures, 'timedelta', artifact_delta):
                self.f.graph(conn, body)
            if with_attempt:
                helper = attempt_fixtures.ExecutionAttemptSchemaTests()
                helper.f = self.f; helper.authority = body
                value = dict(format=attempts.FORMAT, attempt_id=str(uuid4()), authority_id=body['authority_id'],
                    authority_sha256=digest(body), created_at_utc=body['issued_at_utc'], expires_at_utc=body['expires_at_utc'])
                helper.graph(conn, value)
            generation = self.idle_generation(conn) if idle else 3
            base.check_control(conn)
            conn.commit()
        if idle:
            with patch.object(admin, 'target_identity', side_effect=authorization.target_identity):
                transition.migrate(self.config, expected_generation=generation,
                    operator='fixture', reason='install after disposable historical binding')
        return body, generation

    def test_preserves_normal_near_expiry_and_credential_clipped_v1(self):
        for kind in ('normal', 'near_expiry', 'credential_clipped'):
            with self.subTest(kind=kind):
                self.restore()
                body, generation = self.seed(clipped=kind == 'credential_clipped')
                with admin.connect(self.config.control) as conn:
                    before = policy._snapshot(conn)
                    old_manifests = (attempts.authority_manifest(conn), transition.historical_manifest(conn),
                                     authority.historical_claim_manifest(conn))
                    head_time = json.loads(admin._audit_head(conn)['body_json'])['at_utc']
                now = head_time if kind != 'near_expiry' else (
                    utc(body['expires_at_utc'])-timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
                with patch.object(runtime, '_utc_now', return_value=now):
                    self.assertTrue(self.migrate(generation)['installed'])
                    self.assertFalse(self.migrate(generation)['installed'])
                with admin.connect(self.config.control) as conn:
                    base.check_control(conn)
                    after = policy._snapshot(conn)
                    for table, rows in before.items():
                        self.assertEqual(rows, after[table][:-1] if table == 'recognition_admin_audit' else after[table])
                    stored = conn.execute('SELECT * FROM '+authority.AUTHORITIES).fetchone()
                    self.assertEqual(canonical(body), stored['body_json'])
                    self.assertEqual(body, authority.parse_authority(stored['body_json'], authority_sha256=stored['body_sha256']))
                    self.assertEqual(30 if kind == 'credential_clipped' else 120, stored['expires_at']-stored['issued_at'])
                    self.assertEqual(old_manifests, (attempts.authority_manifest(conn), transition.historical_manifest(conn),
                                                    authority.historical_claim_manifest(conn)))
                    self.assertEqual(['main'], [r['name'] for r in conn.execute('PRAGMA database_list')])
                    self.assertFalse(conn.execute('SELECT 1 FROM sqlite_master WHERE name=?', (policy.STAGING,)).fetchone())
                    self.assertEqual(1, len(authority._rows(conn, policy.ACTION)))
                    self.assertFalse(conn.execute('PRAGMA foreign_key_check').fetchone())

    def test_v2_representation_clipping_immutable_and_invalid_policies(self):
        for clipped in (False, True):
            with self.subTest(clipped=clipped):
                self.restore()
                self.migrate()
                body, _ = self.seed(version=lineage.V2, clipped=clipped, idle=False)
                self.assertEqual(300, policy.seconds(lineage.V2))
                self.assertEqual(120, policy.seconds(authority.LIFETIME))
                with admin.connect(self.config.control, write=True) as conn:
                    conn.execute('BEGIN IMMEDIATE')
                    base.check_control(conn)
                    row = conn.execute('SELECT * FROM '+authority.AUTHORITIES).fetchone()
                    self.assertEqual(30 if clipped else 300, row['expires_at']-row['issued_at'])
                    for verb in ('UPDATE '+authority.AUTHORITIES+' SET body_json=body_json',
                                 'DELETE FROM '+authority.AUTHORITIES):
                        with self.assertRaises(sqlite3.IntegrityError): conn.execute(verb)
                    # Isolate the table's policy CHECK from other live admission
                    # checks in this rolled-back DATA probe, restoring on rollback.
                    conn.execute('DROP TRIGGER '+authority.AUTHORITIES+'_scope_guard')
                    columns = list(row.keys())
                    for version, interval in (('unknown-v3', 120), (None, 120), (True, 120),
                                              (authority.LIFETIME, 121), (lineage.V2, 301)):
                        candidate = deepcopy(body); candidate['lifetime_policy'] = version
                        candidate['expires_at_utc'] = (utc(body['issued_at_utc'])+timedelta(seconds=interval)).strftime('%Y-%m-%dT%H:%M:%SZ')
                        with self.assertRaises(TrustError): authority.validate_authority(candidate)
                        raw = dict(row)
                        raw.update(authority_id=str(uuid4()), operation_id=str(uuid4()),
                            writer_manifest_sha256='1'*64, confirmation_sha256='2'*64,
                            body_sha256='3'*64, audit_sequence=row['audit_sequence']+100,
                            body_json=canonical(candidate), expires_at=row['issued_at']+interval)
                        with self.assertRaises(sqlite3.IntegrityError):
                            conn.execute('INSERT INTO '+authority.AUTHORITIES+' ('+','.join(columns)+') VALUES ('+
                                         ','.join('?' for _ in columns)+')', tuple(raw[c] for c in columns))
                    conn.rollback()

    def test_actual_packages_installed_after_cutover_keep_raw_hashes(self):
        self.restore(self.core)
        self.migrate()
        with admin.connect(self.config.control) as conn:
            before_t = claims.manifest(conn)
        with patch.object(admin, 'target_identity', side_effect=authorization.target_identity):
            attempts.migrate(self.config, expected_generation=3, operator='fixture', reason='post-cutover attempt')
            transition.migrate(self.config, expected_generation=3, operator='fixture', reason='post-cutover transition')
        with admin.connect(self.config.control) as conn:
            base.check_control(conn)
            edges = lineage.verify(conn)
            self.assertEqual(['A', 'L', 'T', 'E'], list(edges))
            self.assertEqual(before_t, edges['T']['audit']['subject']['previous_schema_sha256'])

    def test_rollback_at_rebuild_audit_and_final_validation(self):
        body, generation = self.seed()
        template = self.backup(); self.addCleanup(template.close)
        before = self.f.dump(self.config.control)
        original = admin.connect
        class Connection:
            def __init__(self, conn, fault): self.conn = conn; self.fault = fault
            def __getattr__(self, name): return getattr(self.conn, name)
            def execute(self, sql, *args):
                result = self.conn.execute(sql, *args)
                if self.fault in sql: raise OSError('injected reserved migration failure')
                return result
        for stage in ('CREATE TABLE main.'+policy.STAGING, 'DROP TABLE '+authority.AUTHORITIES,
                      'CREATE TRIGGER '+authority.AUTHORITIES+'_scope_guard',
                      'DROP TABLE main.'+policy.STAGING, 'audit', 'validation'):
            with self.subTest(stage=stage):
                self.restore(template)
                @contextmanager
                def connected(path, **kwargs):
                    with original(path, **kwargs) as conn:
                        yield Connection(conn, stage) if path == self.config.control and kwargs.get('write') else conn
                check = base.check_control
                def checked(conn):
                    if stage == 'validation' and lineage.present(conn): raise OSError('injected final validation')
                    return check(conn)
                audit = admin._audit
                def audited(conn, action, *args):
                    if stage == 'audit' and action == policy.ACTION: raise OSError('injected audit')
                    return audit(conn, action, *args)
                with patch.object(admin, 'connect', connected), patch.object(base, 'check_control', checked), \
                     patch.object(admin, '_audit', audited), self.assertRaises(OSError):
                    self.migrate(generation)
                self.assertEqual(before, self.f.dump(self.config.control))
                with admin.connect(self.config.control) as conn:
                    base.check_control(conn)
                    self.assertFalse(lineage.present(conn))

    def test_wrong_generation_active_and_staging_or_temp_reject(self):
        with self.assertRaisesRegex(TrustError, 'generation_conflict'): self.migrate(99)
        self.f.f.activate_fixture()
        with self.assertRaisesRegex(TrustError, 'requires_not_activated'): self.migrate()
        self.restore()
        with admin.connect(self.config.control, write=True) as conn:
            conn.execute('CREATE TABLE '+policy.STAGING+' (id INTEGER)'); conn.commit()
        with self.assertRaisesRegex(TrustError, 'administration_schema_mismatch'): self.migrate()
        self.restore()
        with admin.connect(self.config.control, write=True) as conn:
            conn.execute('CREATE TEMP TABLE staging_probe (id INTEGER)')
            conn.execute('DROP TABLE staging_probe')
            with self.assertRaisesRegex(TrustError, 'isolated_admin_control_required'): base.check_control(conn)

    def test_commit_uncertainty_publishes_no_success_and_is_inspectable(self):
        _, generation = self.seed()
        template = self.backup(); self.addCleanup(template.close)
        before = self.f.dump(self.config.control)
        original = admin.connect
        for committed in (False, True):
            with self.subTest(committed=committed):
                self.restore(template)
                class Connection:
                    def __init__(self, conn): self.conn = conn
                    def __getattr__(self, name): return getattr(self.conn, name)
                    def commit(self):
                        if committed:
                            self.conn.commit()
                            raise OSError('synthetic lost commit acknowledgement')
                        # A silent no-op is not a confirmed commit.
                @contextmanager
                def connected(path, **kwargs):
                    with original(path, **kwargs) as conn:
                        yield Connection(conn) if path == self.config.control and kwargs.get('write') else conn
                with patch.object(admin, 'connect', connected), self.assertRaises((TrustError, OSError)):
                    self.migrate(generation)
                with admin.connect(self.config.control) as conn:
                    base.check_control(conn)
                    self.assertEqual(committed, lineage.present(conn))
                if not committed:
                    self.assertEqual(before, self.f.dump(self.config.control))

    def test_target_read_only_reservation_through_commit(self):
        _, generation = self.seed()
        original = admin.connect
        target_state = []
        statements = []
        committed = []
        class Connection:
            def __init__(self, conn, is_target): self.conn = conn; self.is_target = is_target
            def __getattr__(self, name): return getattr(self.conn, name)
            def commit(inner):
                self.assertFalse(inner.is_target, 'target commit forbidden')
                self.assertTrue(target_state[-1].in_transaction)
                self.assertEqual(1, target_state[-1].execute('PRAGMA query_only').fetchone()[0])
                self.assertIsNone(inner.conn.execute('SELECT 1 FROM sqlite_master WHERE name=?', (policy.STAGING,)).fetchone())
                self.assertEqual(['main'], [r['name'] for r in inner.conn.execute('PRAGMA database_list')])
                inner.conn.commit(); committed.append(True)
        @contextmanager
        def connected(path, **kwargs):
            with original(path, **kwargs) as conn:
                if kwargs.get('write'):
                    if path == self.config.target:
                        target_state.append(conn); conn.set_trace_callback(statements.append)
                    yield Connection(conn, path == self.config.target)
                else:
                    yield conn
        with patch.object(admin, 'connect', connected):
            self.assertTrue(self.migrate(generation)['installed'])
        self.assertEqual([True], committed)
        forbidden = ('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'REPLACE', 'COMMIT')
        self.assertFalse(any(s.lstrip().upper().startswith(forbidden) for s in statements))

    def test_concurrent_upgrade_has_one_install_and_one_audit(self):
        _, generation = self.seed()
        with patch.object(admin, 'target_identity', side_effect=authorization.target_identity):
            def run(_):
                return policy.migrate(self.config, expected_generation=generation,
                    operator='isolated-concurrency', reason='same disposable store')['installed']
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual([False, True], sorted(pool.map(run, range(2))))
        with admin.connect(self.config.control) as conn:
            base.check_control(conn)
            self.assertEqual(1, len(authority._rows(conn, policy.ACTION)))

    def test_clean_wal_migration_close_and_fresh_reopen(self):
        body, generation = self.seed()
        with closing(sqlite3.connect(self.config.control)) as conn:
            self.assertEqual('wal', conn.execute('PRAGMA journal_mode=WAL').fetchone()[0])
        with admin.connect(self.config.control) as conn:
            before = policy._snapshot(conn)
            historical = (attempts.authority_manifest(conn), transition.historical_manifest(conn),
                          authority.historical_claim_manifest(conn))
        # No live connection to this file is retained around the normal manager
        # call; success includes its actual control commit and clean context exit.
        self.assertTrue(self.migrate(generation)['installed'])
        with admin.connect(self.config.control, write=True) as conn:
            self.assertEqual(2, conn.execute('PRAGMA synchronous').fetchone()[0])
            self.assertEqual('wal', conn.execute('PRAGMA journal_mode').fetchone()[0])
            conn.execute('BEGIN IMMEDIATE')
            base.check_control(conn)
            self.assertEqual(['A', 'T', 'E', 'L'], list(lineage.verify(conn)))
            after = policy._snapshot(conn)
            for table, rows in before.items():
                self.assertEqual(rows, after[table][:-1] if table == 'recognition_admin_audit' else after[table])
            self.assertEqual(len(before['recognition_admin_audit'])+1, len(after['recognition_admin_audit']))
            self.assertEqual(historical, (attempts.authority_manifest(conn), transition.historical_manifest(conn),
                                          authority.historical_claim_manifest(conn)))
            row = conn.execute('SELECT * FROM '+authority.AUTHORITIES).fetchone()
            self.assertEqual(canonical(body), row['body_json'])
            self.assertEqual(120, row['expires_at']-row['issued_at'])
            self.assertFalse(conn.execute('PRAGMA foreign_key_check').fetchone())
            self.assertFalse(conn.execute('SELECT 1 FROM sqlite_master WHERE name=?', (policy.STAGING,)).fetchone())
            self.assertEqual(['main'], [r['name'] for r in conn.execute('PRAGMA database_list')])

    def test_process_interruption_delete_and_wal(self):
        _, generation = self.seed()
        template = self.backup(); self.addCleanup(template.close)
        for mode in ('DELETE', 'WAL'):
            for committed in (False, True):
                with self.subTest(mode=mode, committed=committed), ExitStack() as connections:
                    self.restore(template)
                    with closing(sqlite3.connect(self.config.control)) as conn:
                        self.assertEqual(mode.lower(), conn.execute('PRAGMA journal_mode='+mode).fetchone()[0])
                    marker = self.workspace / ('r11e-boundary-'+uuid4().hex)
                    with admin.connect(self.config.control) as conn:
                        now = json.loads(admin._audit_head(conn)['body_json'])['at_utc']
                        before = policy._snapshot(conn)
                    if mode == 'WAL':
                        # R11-G writer-termination case. Keep a connection, not a
                        # read transaction, through recovery. Last-client crash
                        # diagnosis remains separate in recognition_runtime_wal_diagnosis.
                        anchor = connections.enter_context(admin.connect(self.config.control))
                        anchor.execute('SELECT count(*) FROM '+authority.AUTHORITIES).fetchone()
                        self.assertFalse(anchor.in_transaction)
                        self.assertEqual('wal', anchor.execute('PRAGMA journal_mode').fetchone()[0])
                        self.assertEqual(2, anchor.execute('PRAGMA synchronous').fetchone()[0])
                    args = dict(target=str(self.config.target), control=str(self.config.control),
                        key=str(self.config.key_file), root=str(self.workspace), marker=str(marker),
                        generation=generation, now=now, committed=committed)
                    child = subprocess.Popen([sys.executable, '-B', '-c', _CHILD, json.dumps(args)],
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    try:
                        deadline = time.monotonic()+30
                        while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                            time.sleep(0.025)
                        self.assertTrue(marker.exists(), 'child did not reach reserved boundary; exit='+str(child.poll()))
                    finally:
                        if child.poll() is None: child.kill()
                        child.wait(timeout=5)
                        marker.unlink(missing_ok=True)
                    # Normal SQLite recovery only; no checkpoint, sidecar removal,
                    # retries, schema repair or authority adoption.
                    with admin.connect(self.config.control, write=True) as conn:
                        conn.execute('BEGIN IMMEDIATE')
                        base.check_control(conn)
                        self.assertEqual(committed, lineage.present(conn))
                        self.assertEqual(1, conn.execute('SELECT count(*) FROM '+authority.AUTHORITIES).fetchone()[0])
                        after = policy._snapshot(conn)
                        for table, rows in before.items():
                            expected = after[table][:-1] if committed and table == 'recognition_admin_audit' else after[table]
                            self.assertEqual(rows, expected)
                        self.assertEqual(len(before['recognition_admin_audit'])+int(committed), len(after['recognition_admin_audit']))
                    # Close every parent handle cleanly, then require a genuinely
                    # fresh reopen; do not retain the anchor indefinitely.
                    connections.close()
                    with admin.connect(self.config.control, write=True) as fresh:
                        self.assertEqual(2, fresh.execute('PRAGMA synchronous').fetchone()[0])
                        self.assertEqual(mode.lower(), fresh.execute('PRAGMA journal_mode').fetchone()[0])
                        fresh.execute('BEGIN IMMEDIATE')
                        base.check_control(fresh)
                        self.assertEqual(committed, lineage.present(fresh))
                        self.assertEqual(after, policy._snapshot(fresh))
                        self.assertFalse(fresh.execute('PRAGMA foreign_key_check').fetchone())


_CHILD = r'''
import json, sqlite3, sys, time
from pathlib import Path
from unittest.mock import patch
from src.review.recognition import administration as a, runtime_authority_lifetime_policy as p
from src.review.recognition import runtime_validation as runtime
x=json.loads(sys.argv[1])
root=Path(x['root']).resolve()
assert root.name.startswith('recognition-r11e-')
assert all(Path(x[k]).resolve().is_relative_to(root) for k in ('target','control','key','marker'))
def boundary():
    Path(x['marker']).write_text('reserved boundary',encoding='utf-8')
    time.sleep(90)
rebuild=p._rebuild
def staged(conn):
    rebuild(conn)
    if not x['committed']: boundary()
class Connection(sqlite3.Connection):
    def commit(self):
        super().commit()
        if x['committed']: boundary()
factory=sqlite3.connect
def connect(*args,**kwargs):
    kwargs['factory']=Connection
    return factory(*args,**kwargs)
config=a.LocalAdministration(Path(x['target']),Path(x['control']),Path(x['key']))
with patch.object(p,'_rebuild',staged),patch.object(a.sqlite3,'connect',connect),patch.object(runtime,'_utc_now',return_value=x['now']):
    p.migrate(config,expected_generation=x['generation'],operator='isolated-child',reason='termination test only')
'''


if __name__ == '__main__':
    unittest.main()
