"""R11-F instrumentation of the existing R11-E WAL child, not a correction."""

import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
from uuid import uuid4

from src.review.recognition import administration as admin, administration_schema as base
from src.review.recognition import runtime_schema_package_lineage as lineage
from tests.test_recognition_runtime_authority_lifetime_policy import LifetimePolicyMigrationTests, _CHILD
from tests.recognition_runtime_wal_diagnosis import error, files


BOUNDARY = r'''
    from src.review.recognition import administration_schema as base, runtime_schema_package_lineage as lineage
    from src.review.recognition import runtime_activation_authority_schema as authority
    c=current
    after=p._snapshot(c)
    audit='recognition_admin_audit'
    state=dict(in_transaction=c.in_transaction,journal=c.execute('PRAGMA journal_mode').fetchone()[0],
        synchronous=c.execute('PRAGMA synchronous').fetchone()[0],
        database_list=[r['name'] for r in c.execute('PRAGMA database_list')],
        staging_absent=not c.execute('SELECT 1 FROM sqlite_master WHERE name=?',(p.STAGING,)).fetchone(),
        foreign_key_check=[tuple(r) for r in c.execute('PRAGMA foreign_key_check')],
        protected_rows_equal=all(after[k]==v for k,v in before.items() if k!=audit),
        authority_bytes_equal=after[authority.AUTHORITIES]==before[authority.AUTHORITIES],
        old_audit_prefix_equal=after[audit][:len(before[audit])]==before[audit],
        audit_rows_added=len(after[audit])-len(before[audit]),
        policies=[json.loads(r[0])['lifetime_policy'] for r in c.execute('SELECT body_json FROM '+authority.AUTHORITIES)],
        upgrade_audit_count=len(authority._rows(c,p.ACTION)),
        successor_definitions_match=all(' '.join(sql.split())==' '.join(dict(base._control_objects(c))[n].split())
            for n,sql in lineage.successor_definitions().items()),
        raw_schema_sha256=p.claims.manifest(c))
    if x['committed']:
        base.check_control(c)
        state['full_check_control']='passed'
        state['lineage']=list(lineage.verify(c))
    else:
        state['full_check_control']='not a complete successor before upgrade audit/commit'
    pending=Path(x['marker']+'.writing')
    pending.write_text(json.dumps(state),encoding='utf-8')
    pending.replace(x['marker'])
    time.sleep(90)
'''


def main():
    cls = LifetimePolicyMigrationTests
    report = dict(runs=[])
    # Only add diagnostics to the existing child's same connection/boundaries.
    # No new database handle, DDL, audit, commit or PRAGMA setting is introduced.
    source = _CHILD.replace("    Path(x['marker']).write_text('reserved boundary',encoding='utf-8')\n    time.sleep(90)", BOUNDARY.rstrip())
    source = source.replace('rebuild=p._rebuild', 'before=None\ncurrent=None\nrebuild=p._rebuild')
    source = source.replace('def staged(conn):\n    rebuild(conn)',
        'def staged(conn):\n    global before,current\n    before=p._snapshot(conn)\n    current=conn\n    rebuild(conn)')
    assert source != _CHILD and 'global before,current' in source
    instance = cls('test_process_interruption_delete_and_wal')
    try:
        cls.setUpClass()
        instance.setUp()
        _, generation = instance.seed()
        template = cls.backup()
        try:
            for committed in (False, True):
                instance.restore(template)
                import sqlite3
                from contextlib import closing
                with closing(sqlite3.connect(instance.config.control)) as conn:
                    assert conn.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal'
                with admin.connect(instance.config.control) as conn:
                    now = json.loads(admin._audit_head(conn)['body_json'])['at_utc']
                marker = instance.workspace / ('r11f-migration-'+uuid4().hex)
                args = dict(target=str(instance.config.target),control=str(instance.config.control),
                    key=str(instance.config.key_file),root=str(instance.workspace),marker=str(marker),
                    generation=generation,now=now,committed=committed)
                item = dict(committed=committed, path=str(instance.config.control))
                child = subprocess.Popen([sys.executable,'-B','-c',source,json.dumps(args)],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                try:
                    deadline=time.monotonic()+30
                    while not marker.exists() and child.poll() is None and time.monotonic()<deadline:
                        time.sleep(0.025)
                    if not marker.exists():
                        raise AssertionError('child boundary not reached; exit='+str(child.poll()))
                    item['before_termination']=json.loads(marker.read_text(encoding='utf-8'))
                finally:
                    if child.poll() is None: child.kill()
                    child.wait(timeout=5)
                    marker.unlink(missing_ok=True); marker.with_name(marker.name+'.writing').unlink(missing_ok=True)
                item['files_before_reopen']=files(instance.config.control)
                try:
                    with admin.connect(instance.config.control,write=True) as conn:
                        conn.execute('BEGIN IMMEDIATE')
                        base.check_control(conn)
                        item['reopen']=dict(status='passed',lineage_present=lineage.present(conn))
                except Exception as exc:
                    frames=traceback.extract_tb(exc.__traceback__)
                    item['reopen']=dict(**error(exc), frames=[dict(file=Path(f.filename).name,line=f.lineno,
                        function=f.name,operation=f.line) for f in frames])
                report['runs'].append(item)
        finally:
            template.close()
        instance.tearDown()
    finally:
        instance.doCleanups()
        cls.doClassCleanups()
    report['cleanup']=not instance.workspace.exists()
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
