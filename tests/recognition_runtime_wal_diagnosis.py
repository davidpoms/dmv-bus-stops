"""R11-F bounded toy SQLite probes; no recognition migration or production data."""

from contextlib import closing
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import stat
import subprocess
import sys
import time
from uuid import uuid4


CHILD = r'''
import json, sqlite3, sys, time
from pathlib import Path
x=json.loads(sys.argv[1])
p=Path(x['path']).resolve(); root=Path(x['root']).resolve()
assert root.name.startswith('recognition-r11f-') and p.parent==root
c=sqlite3.connect(p.as_uri()+'?mode=rw',uri=True)
c.execute('PRAGMA foreign_keys=ON')
c.execute('PRAGMA synchronous=FULL')
c.execute('BEGIN IMMEDIATE')
c.execute("UPDATE probe SET value='child' WHERE id=1")
if x['committed']: c.commit()
pending=Path(x['ready']+'.writing')
pending.write_text(json.dumps(dict(in_transaction=c.in_transaction,
    journal=c.execute('PRAGMA journal_mode').fetchone()[0],
    synchronous=c.execute('PRAGMA synchronous').fetchone()[0])),encoding='utf-8')
pending.replace(x['ready'])
time.sleep(60)
'''


def error(exc):
    return dict(exception=type(exc).__name__, message=str(exc),
                sqlite_errorcode=getattr(exc, 'sqlite_errorcode', None),
                sqlite_errorname=getattr(exc, 'sqlite_errorname', None),
                errno=getattr(exc, 'errno', None), winerror=getattr(exc, 'winerror', None))


def files(path):
    result = {}
    for suffix in ('', '-wal', '-shm', '-journal'):
        p = Path(str(path)+suffix)
        if not p.exists():
            result[suffix or 'db'] = dict(exists=False)
            continue
        info = p.stat()
        item = dict(exists=True, size=info.st_size, mode=oct(stat.S_IMODE(info.st_mode)),
                    attributes=getattr(info, 'st_file_attributes', None))
        try:
            with p.open('rb') as stream:
                stream.read(1)
            item['ordinary_read'] = 'ok'
        except OSError as exc:
            item['ordinary_read'] = error(exc)
        result[suffix or 'db'] = item
    return result


def probe(root, mode, *, kill=False, committed=False, anchor=False):
    path = root / ('toy-'+uuid4().hex+'.db')
    ready = root / ('ready-'+uuid4().hex)
    stderr = root / ('stderr-'+uuid4().hex)
    result = dict(mode=mode, kill=kill, committed=committed, anchor=anchor,
                  path=str(path), uri=path.as_uri()+'?mode=rw')
    held = None
    child = None
    conn = None
    started = time.monotonic()
    try:
        with closing(sqlite3.connect(path)) as setup:
            result['initial_journal'] = setup.execute('PRAGMA journal_mode='+mode).fetchone()[0]
            setup.execute('PRAGMA synchronous=FULL')
            setup.execute('CREATE TABLE probe(id INTEGER PRIMARY KEY,value TEXT NOT NULL)')
            setup.execute("INSERT INTO probe VALUES(1,'original')")
            setup.commit()
        if anchor:
            held = sqlite3.connect(path.as_uri()+'?mode=rw', uri=True)
            held.execute('SELECT * FROM probe').fetchall()
            result['anchor_in_transaction'] = held.in_transaction
        if kill:
            args = dict(root=str(root), path=str(path), ready=str(ready), committed=committed)
            with stderr.open('wb') as output:
                child = subprocess.Popen([sys.executable, '-B', '-c', CHILD, json.dumps(args)],
                    stdout=subprocess.DEVNULL, stderr=output)
            deadline = time.monotonic()+8
            while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            if not ready.exists():
                raise AssertionError('toy child failed to reach boundary: '+stderr.read_text(encoding='utf-8')[:2048])
            result['child_boundary'] = json.loads(ready.read_text(encoding='utf-8'))
            child.kill(); child.wait(timeout=5)
            result['child_reaped'] = child.returncode is not None
        result['before_reopen'] = files(path)
        step = 'sqlite3.connect(uri, mode=rw)'
        try:
            conn = sqlite3.connect(path.as_uri()+'?mode=rw', uri=True)
            step = 'PRAGMA foreign_keys=ON'; conn.execute(step)
            step = 'PRAGMA synchronous=FULL'; conn.execute(step)
            step = 'BEGIN IMMEDIATE'; conn.execute(step)
            step = 'SELECT value FROM probe WHERE id=1'
            result['value'] = conn.execute(step).fetchone()[0]
            result['expected'] = 'child' if kill and committed else 'original'
            step = "INSERT INTO probe VALUES(2,'read/write probe')"; conn.execute(step)
            conn.rollback()
            result['reopen'] = 'ok'
        except sqlite3.Error as exc:
            result['reopen'] = dict(operation=step, **error(exc))
        result['after_reopen'] = files(path)
    finally:
        if conn is not None: conn.close()
        if held is not None: held.close()
        if child is not None and child.poll() is None:
            child.kill(); child.wait(timeout=5)
        result['elapsed_seconds'] = round(time.monotonic()-started, 6)
    return result


def main():
    parent = Path(__file__).resolve().parents[1]
    root = parent / ('recognition-r11f-'+uuid4().hex)
    os.mkdir(root, 0o777)
    report = dict(sqlite=sqlite3.sqlite_version, python=sys.version, platform=platform.platform(), runs=[])
    with closing(sqlite3.connect(':memory:')) as conn:
        report['compile_options'] = [r[0] for r in conn.execute('PRAGMA compile_options')]
    try:
        for mode in ('DELETE', 'WAL'):
            report['runs'].append(probe(root, mode))
            for committed in (False, True):
                report['runs'].append(probe(root, mode, kill=True, committed=committed))
        for committed in (False, True):
            report['runs'].append(probe(root, 'WAL', kill=True, committed=committed, anchor=True))
    finally:
        # Delete only this freshly allocated, verified probe directory.
        assert root.resolve().parent == parent and root.name.startswith('recognition-r11f-')
        shutil.rmtree(root)
        report['cleanup'] = not root.exists()
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
