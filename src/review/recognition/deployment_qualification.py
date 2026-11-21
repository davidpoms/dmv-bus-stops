"""Focused trusted-host qualification, not authority or a rehearsal substitute.

Observations are operator-reviewed evidence hashes, not cryptographic proof of
host behavior. Existing reserved administration owners bind them to the exact
installation and physical context. Backup contents are independently checked.
"""

from dataclasses import asdict
from pathlib import Path
import hashlib
import os
import stat
import sqlite3
import subprocess
import sys
import tempfile

from . import administration as a
from .rules import canonical, digest
from .trust import load

ACTION = 'local_deployment_qualification_recorded'
CHECKS = frozenset(('control_persistence', 'filesystem_permissions',
                    'secret_protection', 'no_startup_activation'))
LOCKING = dict(sqlite_locking=True, concurrent_workers=True, writer_lock=True)


def permissions(config):
    """Current private-file access remains mandatory, independently of evidence."""
    for path in (config.target, config.control, config.key_file):
        info = path.lstat()
        a.need(not path.is_symlink() and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
               'deployment_unsafe_permissions', 503)
        if os.name != 'nt':
            a.need(info.st_uid == os.geteuid() and not info.st_mode & 0o077
                   and not path.parent.stat().st_mode & 0o022,
                   'deployment_unsafe_permissions', 503)


def _file(path, config):
    a.need(isinstance(path, Path) and path.is_absolute(), 'deployment_backup_required', 503)
    info = path.lstat()
    a.need(not any(Path(str(path)+suffix).exists() for suffix in ('-journal','-wal','-shm')),
           'deployment_backup_active', 503)
    a.need(not path.is_symlink() and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
           'deployment_backup_required', 503)
    for protected in (config.target, config.control, config.key_file):
        live = protected.stat()
        a.need((info.st_dev, info.st_ino) != (live.st_dev, live.st_ino),
               'deployment_separate_backup_required', 503)
    if os.name != 'nt':
        a.need(info.st_uid == os.geteuid() and not info.st_mode & 0o077
               and not path.parent.stat().st_mode & 0o022, 'deployment_unsafe_backup', 503)
    with path.open('rb') as source:
        opened = os.fstat(source.fileno())
        a.need((opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino), 'deployment_backup_changed', 503)
        hasher = hashlib.sha256()
        for block in iter(lambda: source.read(1024*1024), b''):
            hasher.update(block)
        sha = hasher.hexdigest()
        stamp = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        a.need(stamp(os.fstat(source.fileno())) == stamp(opened) and stamp(path.lstat()) == stamp(info),
               'deployment_backup_changed', 503)
    return dict(path=str(path), sha256=sha)


def _contents(conn):
    """Typed content hash, including all application tables; no contents returned."""
    result = []
    for name, in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name NOT LIKE 'sqlite_%' OR name='sqlite_sequence') ORDER BY name"):
        quoted = '"'+name.replace('"', '""')+'"'
        result.append((name, sorted(repr(tuple(row)) for row in conn.execute('SELECT * FROM '+quoted))))
    return digest(result)


def _scope(config, binding):
    from . import production_operations
    implementation = digest({name: hashlib.sha256(Path(__file__).with_name(name+'.py').read_bytes()).hexdigest()
                             for name in ('deployment_qualification', 'writer_boundary', 'local_execution',
                                          'runtime_validation', 'runtime_execution_coordinator')})
    return dict(target=production_operations.local_target(binding), binding_sha256=digest(binding),
                sqlite_version=sqlite3.sqlite_version, implementation_sha256=implementation,
                physical={key: asdict(a.target_identity(path)) for key, path in
                          (('target', config.target), ('control', config.control))})


def qualify_locking(config):
    """Two-process exclusion and committed visibility on disposable sibling files.

    Never opens a live store. Both processes use the supported SQLite loader.
    Failure, unexpected success or timeout is a failed qualification.
    """
    program = '''
import sys,os
if os.environ.get('RECOGNITION_SQLITE_LIBRARY'):
    from src.api.sqlite_runtime import load_production_sqlite
    load_production_sqlite()
import sqlite3
if sqlite3.sqlite_version != sys.argv[2]:
    print('FAILED');sys.exit(1)
try:
    db=sqlite3.connect(sys.argv[1],timeout=0)
    db.execute('BEGIN IMMEDIATE')
    db.execute('INSERT INTO probe VALUES(2)')
    db.commit()
    print('COMMITTED')
except sqlite3.OperationalError as error:
    print('BUSY' if getattr(error,'sqlite_errorcode',None) in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED) else 'FAILED')
'''
    try:
        for directory in sorted({config.target.parent, config.control.parent}):
            with tempfile.TemporaryDirectory(prefix='recognition-lock-qualification-', dir=directory) as work:
                path = Path(work)/'probe.db'
                db = sqlite3.connect(path)
                try:
                    db.execute('PRAGMA journal_mode=DELETE')
                    db.execute('PRAGMA synchronous=FULL')
                    db.execute('CREATE TABLE probe(value INTEGER)'); db.commit()
                    def child():
                        executable = Path(sys.prefix)/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
                        result = subprocess.run([str(executable),'-B','-c',program,str(path),sqlite3.sqlite_version],
                            cwd=Path(__file__).resolve().parents[3],capture_output=True,text=True,timeout=15)
                        return result.stdout.strip() if result.returncode == 0 else 'FAILED'
                    db.execute('BEGIN IMMEDIATE'); db.execute('INSERT INTO probe VALUES(1)')
                    a.need(child() == 'BUSY', 'deployment_unsafe_locking', 503)
                    db.rollback()
                    a.need(child() == 'COMMITTED' and db.execute('SELECT value FROM probe').fetchall() == [(2,)],
                           'deployment_unsafe_locking', 503)
                finally:
                    db.close()
    except (OSError, sqlite3.Error, subprocess.SubprocessError):
        raise a.AdminError('deployment_unsafe_locking', 503) from None


def _integrity(conn):
    a.need([row[0] for row in conn.execute('PRAGMA integrity_check')] == ['ok']
           and conn.execute('PRAGMA foreign_key_check').fetchone() is None,
           'deployment_backup_integrity_failed', 503)


def _backups(config, control, target, binding, paths):
    a.need(type(paths) is dict and set(paths) == {'target', 'control'}
           and all(type(value) is str for value in paths.values()), 'deployment_backup_pair_required', 503)
    result = {}
    for key, source in (('target', target), ('control', control)):
        path = Path(paths[key])
        before = _file(path, config)
        with a.connect(path) as backup:
            backup.execute('BEGIN')
            a.need(a.schema_fingerprint(backup) == a.schema_fingerprint(source)
                   and _contents(backup) == _contents(source), 'deployment_backup_mismatch', 503)
            _integrity(backup)
        a.need(_file(path, config) == before, 'deployment_backup_changed', 503)
        result[key] = before
    a.need(result['target']['path'] != result['control']['path'], 'deployment_backup_pair_required', 503)
    return result


def record(config, *, operator, reason, evidence, backups, expected_generation,
           session_token=None, primary_token=None, now=None):
    """Record real observations and a verified pair through existing audit owners."""
    from . import local_readiness as ready, operations, runtime_activation as owner, runtime_validation as runtime
    a.need(type(evidence) is dict and set(evidence) == CHECKS
           and all(operations._sha(value) for value in evidence.values()), 'deployment_qualification_evidence_required')
    a.need(type(operator) is str and 1 <= len(operator.strip()) <= 200
           and type(reason) is str and 1 <= len(reason.strip()) <= 2000,
           'deployment_qualification_operator_required')
    frozen = canonical(evidence)
    with a.connect(config.control) as control:
        bodies = [load(row[0]) for row in control.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation')]
        v3 = any(body.get('format') == 'recognition-local-control-v3' for body in bodies)

    def append(control, target, binding, when):
        from .runtime_profile_successor import eligible
        if binding['generation'] == 6:
            a.need(eligible(control, binding), 'deployment_qualification_generation_mismatch', 503)
        a.need(type(expected_generation) is int and binding['generation'] == expected_generation,
               'deployment_qualification_generation_mismatch', 503)
        a.need(ready._state(control, binding)['state'] == 'NOT_ACTIVATED', 'deployment_qualification_requires_not_activated', 503)
        permissions(config)
        qualify_locking(config)
        scope = _scope(config, binding)
        pair = _backups(config, control, target, binding, backups)
        a.need(canonical(evidence) == frozen, 'deployment_qualification_changed', 503)
        a._audit(control, ACTION, operator, when,
                 dict(scope=scope, evidence=load(frozen), locking=dict(LOCKING), backups=pair,
                      target_data_sha256=_contents(target), reason=reason))
        a.need(_scope(config, binding) == scope and canonical(evidence) == frozen,
               'deployment_qualification_changed', 503)
        permissions(config)
        for value in pair.values():
            a.need(_file(Path(value['path']), config) == value, 'deployment_backup_changed', 503)

    if v3:
        with owner._transaction(config) as context:
            if session_token is not None or primary_token is not None:
                owner._view(context).validate_session(session_token, primary_token=primary_token)
            control, target, binding, _ = owner._read_parts(context)
            append(control, target, binding, runtime._utc_now())
    else:
        a.need(session_token is None and primary_token is None, 'runtime_profile_required')
        with a.transaction(config, lock_target=True) as (control, target, binding):
            append(control, target, binding, now or runtime._utc_now())


def assess(config, control, binding, now, *, target=None, before_mutation=False):
    """Read-only; absent/stale scope never becomes implicit qualification."""
    from . import operations
    issues = []
    try:
        permissions(config)
        row = control.execute("SELECT body_json FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=? ORDER BY sequence DESC LIMIT 1", (ACTION,)).fetchone()
        a.need(row is not None, 'deployment_qualification_missing', 503)
        body = load(row[0]); value = body['subject']
        a.need(a.timestamp(body['at_utc']) <= a.timestamp(now) and value['scope'] == _scope(config, binding),
               'deployment_qualification_scope_changed', 503)
        a.need(set(value['evidence']) == CHECKS and all(operations._sha(v) for v in value['evidence'].values()),
               'deployment_qualification_invalid', 503)
        a.need(value['locking'] == LOCKING, 'deployment_unsafe_locking', 503)
        for backup in value['backups'].values():
            a.need(_file(Path(backup['path']), config) == backup, 'deployment_backup_changed', 503)
        a.need(set(value['backups']) == {'target', 'control'}, 'deployment_backup_pair_required', 503)
        if before_mutation:
            a.need(target is not None and _contents(target) == value['target_data_sha256'],
                   'deployment_recovery_point_stale', 503)
        return dict(ready=True, issues=[], qualification_sha256=digest(body))
    except a.AdminError as error:
        issues.append(error.code)
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        issues.append('deployment_qualification_invalid')
    return dict(ready=False, issues=issues, qualification_sha256=None)
