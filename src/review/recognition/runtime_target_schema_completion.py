"""Closed pre-activation maintenance owner. No runtime writer authority.

The only attached connection belongs to this synchronous API. Normal validators
still use isolated read-only connections; target DDL and its control audit commit
in one rollback-journal SQLite transaction. Journal modes are never changed.
"""

from contextlib import contextmanager, closing
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
import sqlite3
import tempfile

from . import administration as a, admin_auth as auth, runtime_auth
from . import runtime_validation as runtime, runtime_activation as owner, local_readiness
from . import event_schema, execution_schema, runtime_target_schema_lineage as lineage
from . import runtime_execution_claim_schema as claims, runtime_production_governance as governance
from . import readiness_diagnostics as diagnostics
from .rules import canonical, digest
from .trust import require, load, utc


ALIAS = 'completion_target'
PREVIEW_KIND = 'target_event_foundation_preview'


def preview_binding(subject):
    """Fixed inspection purpose; cannot authorize installation or an Authority."""
    from .trust import fields
    require(type(subject) is dict, 'foundation_preview_purpose')
    package = subject.get('package', lineage.PACKAGE)
    fields(subject, ('kind','operator','reason','package') if 'package' in subject else ('kind','operator','reason'))
    require('package' not in subject or package == lineage.RUNTIME_PACKAGE, 'foundation_preview_purpose')
    require(subject['kind'] == PREVIEW_KIND, 'foundation_preview_purpose')
    runtime.enrollment._text(subject['operator'], 200)
    runtime.enrollment._text(subject['reason'], 2000)
    return dict(family=package,permission='inspection',action='preview',
                operation_sha256=digest(subject),policy_sha256=digest(lineage.package_definitions(package)),
                population_sha256=None,reference=governance.contract.MANDATE)


def _objects(conn, namespace='main'):
    require(namespace in ('main', ALIAS), 'foundation_namespace')
    return [list(row) for row in conn.execute(
        f"SELECT type,name,tbl_name,sql FROM {namespace}.sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]


def _fingerprint(conn, namespace):
    return digest(dict(objects=_objects(conn, namespace),
        application_id=conn.execute(f'PRAGMA {namespace}.application_id').fetchone()[0],
        user_version=conn.execute(f'PRAGMA {namespace}.user_version').fetchone()[0]))


def _data(conn, namespace='main', *, exclude=()):
    # Internal table identifiers only; exact typed contents never leave this API.
    result = []
    for row in _objects(conn, namespace):
        if row[0] == 'table' and row[1] not in event_schema.TABLES and row[1] not in exclude:
            quoted = '"'+row[1].replace('"','""')+'"'
            result.append((row[1], sorted(repr(tuple(value)) for value in conn.execute(f'SELECT * FROM {namespace}.{quoted}'))))
    return digest(result)


def _journal(conn, namespace='main'):
    require(conn.execute(f'PRAGMA {namespace}.journal_mode').fetchone()[0].lower() == 'delete',
            'foundation_delete_journal_required')


def _source_package(target):
    """Only the known absent-prerequisite source is eligible for the new edge."""
    objects = dict((row[1], row[3]) for row in _objects(target))
    required = {'recognition_operation_contracts','recognition_operation_receipts',
                'recognition_execution_claims','recognition_execution_seals'}
    if required <= objects.keys():
        return lineage.PACKAGE, event_schema.definitions()
    require(not required.intersection(objects), 'foundation_partial_prerequisite_source')
    definitions = lineage.package_definitions(lineage.RUNTIME_PACKAGE)
    for name, sql in definitions.items():
        require(name not in objects or ' '.join(objects[name].split()) == ' '.join(sql.split()),
                'foundation_existing_definition_mismatch')
    # Existing related histories must also be empty; they are never rewritten.
    for name, sql in definitions.items():
        if name in objects and sql.startswith('CREATE TABLE ') and name != 'recognition_execution_storage':
            require(not target.execute('SELECT 1 FROM '+name+' LIMIT 1').fetchone(), 'foundation_existing_operation')
    return lineage.RUNTIME_PACKAGE, {name: sql for name, sql in definitions.items() if name not in objects}


def _session(config, control, target, session, primary):
    now = runtime._utc_now()
    scope = runtime._identity_snapshot(config, control, target, now)
    binding, profile, head = runtime._history(control)
    p = auth._primary(control, target, binding, primary, now)
    s, mfa = auth._session(control, target, binding, session, now)
    require(s['primary_hash'] == p['token_hash'], 'foundation_session_mismatch')
    runtime_auth._scope(control, scope, 'primary', p, now)
    runtime_auth._scope(control, scope, 'session', s, now)
    return binding, profile, head, scope, p, s, mfa


def _signed_session(config, control, target, authorization):
    """Signed-owner continuation of existing MFA records, never raw-token admission.

    Fresh signature verification precedes use of the existing persisted-session
    kernel. RO handles ensure even denials cannot mutate authentication records.
    No caller-provided holder or callback is accepted as authority.
    """
    require(all(conn.execute('PRAGMA query_only').fetchone()[0] == 1 for conn in (control,target)),
            'foundation_readonly_validation_required')
    lineage._protected_root(config)
    _, approval, _ = governance._verify(config, *authorization)
    require(approval['subject']['kind'] in (PREVIEW_KIND,lineage.KIND), 'foundation_approval_purpose')
    now = runtime._utc_now()
    scope = runtime._identity_snapshot(config,control,target,now)
    binding, profile, head = runtime._history(control)
    holder = approval['holder']
    require(holder['actor_id'] == scope['owner_id'] and approval['binding_sha256'] == scope['binding_sha256']
            and approval['installation_id'] == scope['installation_id'], 'foundation_approval_holder')
    s, mfa = auth._session_hash(control,target,binding,holder['session_sha256'],now)
    p = control.execute('SELECT * FROM recognition_admin_primary WHERE token_hash=?',
                        (holder['primary_sha256'],)).fetchone()
    require(p is not None and s['primary_hash'] == p['token_hash'], 'foundation_session_mismatch')
    runtime_auth._scope(control,scope,'primary',p,now)
    runtime_auth._scope(control,scope,'session',s,now)
    require(a.timestamp(approval['expires_at_utc']) <= min(p['expires'],s['expires']),
            'foundation_approval_credential_lifetime')
    return binding, profile, head, scope, p, s, mfa


def _plan(config, control, target, session, primary, *, operator, reason, created_at=None, deadline=None,
          signed_authorization=None):
    runtime.enrollment._text(operator, 200); runtime.enrollment._text(reason, 2000)
    if signed_authorization is None:
        binding, profile, head, scope, p, s, mfa = _session(config, control, target, session, primary)
    else:
        require(session is None and primary is None, 'foundation_mixed_authentication')
        binding, profile, head, scope, p, s, mfa = _signed_session(config,control,target,signed_authorization)
    require(type(binding['generation']) is int and binding['generation'] == 5, 'foundation_generation_required')
    require(not lineage.present(control), 'foundation_already_completed')
    require(binding['production_state'] == 'NOT_ACTIVATED'
            and local_readiness._state(control,binding)['state'] == 'NOT_ACTIVATED', 'foundation_requires_not_activated')
    _journal(control); _journal(target)
    original = dict((row[1],row[3]) for row in _objects(control))
    require(lineage.normalized_manifest(original) == lineage.normalized_manifest(lineage.source_definitions()),
            'foundation_source_control_topology')
    require(not any(row[1] in event_schema.definitions() for row in _objects(target)), 'foundation_event_objects_already_present')
    package, additions = _source_package(target)
    added_tables = {name for name, sql in additions.items() if sql.startswith('CREATE TABLE ')}
    if signed_authorization is not None:
        subject = load(signed_authorization[0])['subject']
        approved_package = subject.get('package', lineage.PACKAGE) if subject['kind'] == PREVIEW_KIND else subject['plan']['package']
        require(approved_package == package, 'foundation_preview_package_mismatch')
    # No live execution/operation continuation can be carried over this edge.
    for name in ('recognition_operation_contracts','recognition_execution_claims',
                 'recognition_execution_seals','recognition_operation_receipts'):
        if name not in added_tables:
            require(not target.execute('SELECT 1 FROM '+name+' LIMIT 1').fetchone(), 'foundation_existing_operation')
    for name in (claims.CLAIMS, claims.HISTORY):
        require(not control.execute('SELECT 1 FROM '+name+' LIMIT 1').fetchone(), 'foundation_existing_claim')
    for path in (config.control,config.target):
        # integrity_check may initialize TEMP; do not contaminate the ordinary
        # isolated validation connections with that implementation detail.
        with a.connect(path) as check:
            require([row[0] for row in check.execute('PRAGMA integrity_check')] == ['ok']
                    and not check.execute('PRAGMA foreign_key_check').fetchone(), 'foundation_integrity_failure')
    # Backup through a separate RO reader: backing up an active writer connection
    # can wait on its own reservation. The runtime owner already holds both writers.
    with diagnostics.stage('foundation_copy'), tempfile.TemporaryDirectory(prefix='recognition-foundation-preview-') as directory:
        preview_path = Path(directory)/'preview.db'
        with a.connect(config.target) as reader, closing(sqlite3.connect(preview_path)) as preview:
            reader.backup(preview)
            preview.row_factory = sqlite3.Row
            preview.execute('PRAGMA foreign_keys=ON')
            require(_fingerprint(preview,'main') == profile['target_schema_sha256'], 'foundation_preview_source_mismatch')
            preview.execute('BEGIN')
            with diagnostics.stage('foundation_schema'):
                for sql in additions.values():
                    preview.execute(sql)
                execution_schema.check_schema(preview)  # All readiness target schemas, not just event tables.
            with diagnostics.stage('foundation_inventory'):
                assessment = local_readiness._assess_inventory(control,preview,binding,runtime._utc_now(),config=config)
                require(assessment['activation_ready'], 'foundation_other_readiness_prerequisites')
            h1 = _fingerprint(preview,'main')
    now = runtime._utc_now()
    created_at = now if created_at is None else created_at
    limit = min(a.timestamp(created_at)+auth.RECENT_SECONDS, p['expires'], s['expires'])
    end = utc(created_at)+timedelta(seconds=limit-a.timestamp(created_at))
    deadline = end.strftime('%Y-%m-%dT%H:%M:%SZ') if deadline is None else deadline
    require(a.timestamp(created_at) <= a.timestamp(now) < a.timestamp(deadline) <= limit, 'foundation_plan_expired')
    plan = dict(format='recognition-target-schema-completion-plan-v2' if package == lineage.RUNTIME_PACKAGE else 'recognition-target-schema-completion-plan-v1', package=package,
        installation_id=binding['installation_id'],target_id=binding['target_id'],owner_id=binding['owner_id'],generation=5,
        binding_sha256=digest(binding),profile_sha256=profile['profile_sha256'],
        enrollment_audit_sha256=control.execute('SELECT body_sha256 FROM recognition_admin_audit WHERE sequence=?',
                                              (profile['audit_sequence'],)).fetchone()[0],
        h0=profile['target_schema_sha256'],h1=h1,control_before_sha256=lineage.normalized_manifest(original),
        control_after_sha256=lineage.normalized_manifest(lineage.upgrade_definitions(original)),
        definitions_sha256=digest(lineage.package_definitions(package)),
        physical=dict(target=asdict(a.target_identity(target)),control=asdict(a.target_identity(control))),
        auth_epoch=scope['auth_epoch'],mfa_epoch=mfa['epoch'],owner_key_sha256=scope['owner_key_sha256'],
        target_data_sha256=_data(target, exclude=added_tables),readiness_sha256=digest(local_readiness._assessment_binding(assessment)),
        source_audit_sha256=head['body_sha256'],operator=operator,reason=reason,
        created_at_utc=created_at,deadline_at_utc=deadline)
    if package == lineage.RUNTIME_PACKAGE:
        plan['added_objects'] = sorted(additions)
    lineage.validate_plan(plan)
    return plan


def preview(config, session_token, *, primary_token, operator, reason):
    with owner._transaction(config) as context:
        owner._view(context).validate_session(session_token, primary_token=primary_token)
        with a.connect(config.control) as control, a.connect(config.target) as target:
            control.execute('BEGIN');target.execute('BEGIN')
            with diagnostics.stage('foundation_prerequisites'):
                plan = _plan(config,control,target,session_token,primary_token,operator=operator,reason=reason)
    return dict(plan=plan,plan_sha256=digest(plan),execution_authority=False)


def _authorizer(action, first, second, database, source, *, additions=None):
    definitions = event_schema.definitions() if additions is None else additions
    tables = {name for name, sql in definitions.items() if sql.startswith('CREATE TABLE ')}
    writes = {sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE}
    if action in writes:
        return sqlite3.SQLITE_OK if ((first == 'sqlite_master' and database in ('main',ALIAS))
            or (action == sqlite3.SQLITE_INSERT and database == 'main' and first == 'recognition_admin_audit')) else sqlite3.SQLITE_DENY
    allowed = {
        sqlite3.SQLITE_CREATE_TABLE: database == ALIAS and first in tables,
        sqlite3.SQLITE_CREATE_INDEX: database == ALIAS and second in tables and first.startswith('sqlite_autoindex_'),
        sqlite3.SQLITE_CREATE_TRIGGER: (database == ALIAS and first in definitions)
            or (database == 'main' and first == claims.CLAIMS+'_scope_guard'),
        sqlite3.SQLITE_DROP_TRIGGER: database == 'main' and first == claims.CLAIMS+'_scope_guard',
    }
    if action in allowed:
        return sqlite3.SQLITE_OK if allowed[action] else sqlite3.SQLITE_DENY
    forbidden = {sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH,sqlite3.SQLITE_ALTER_TABLE,
                 sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_DROP_INDEX,sqlite3.SQLITE_CREATE_VIEW,sqlite3.SQLITE_DROP_VIEW,
                 sqlite3.SQLITE_CREATE_VTABLE,sqlite3.SQLITE_DROP_VTABLE,
                 sqlite3.SQLITE_CREATE_TEMP_TABLE,sqlite3.SQLITE_CREATE_TEMP_TRIGGER,sqlite3.SQLITE_CREATE_TEMP_VIEW,
                 sqlite3.SQLITE_CREATE_TEMP_INDEX,sqlite3.SQLITE_DROP_TEMP_TABLE,sqlite3.SQLITE_DROP_TEMP_TRIGGER,
                 sqlite3.SQLITE_DROP_TEMP_VIEW,sqlite3.SQLITE_DROP_TEMP_INDEX}
    if action in forbidden:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_PRAGMA:
        return sqlite3.SQLITE_OK if first in ('database_list','application_id','user_version','foreign_key_check','journal_mode','synchronous') and second is None else sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


@contextmanager
def _attached(config):
    # No supplied filename/namespace/SQL. Ordinary connection owners never see this handle.
    config.paths()
    require(config.target.resolve() != config.control.resolve(), 'foundation_distinct_files_required')
    with a.connect(config.control,write=True) as db:
        _journal(db)
        _synchronization(db,'main')
        db.execute('ATTACH DATABASE ? AS '+ALIAS, (config.target.resolve().as_uri()+'?mode=rw',))
        _journal(db,ALIAS)
        db.execute('PRAGMA '+ALIAS+'.synchronous=FULL')
        _synchronization(db,ALIAS)
        require(db.execute('PRAGMA foreign_keys').fetchone()[0] == 1, 'foundation_foreign_keys_required')
        db.execute('BEGIN IMMEDIATE')
        require([(row[1],str(Path(row[2]).resolve())) for row in db.execute('PRAGMA database_list')]
                == [('main',str(config.control.resolve())),(ALIAS,str(config.target.resolve()))], 'foundation_database_scope')
        yield db


def _synchronization(db, namespace):
    require(namespace in ('main',ALIAS) and db.execute(f'PRAGMA {namespace}.synchronous').fetchone()[0] == 2,
            'foundation_full_synchronization_required')


def _preview_authorizer(action, first, second, *rest):
    if action in runtime._AUTHENTICATION_DDL_DENY or action in (
            sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_PRAGMA:
        return sqlite3.SQLITE_OK if first in ('database_list','query_only','journal_mode','synchronous') and second is None else sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def preview_approved(config, *, serialized_approval, signature):
    """Explicit signed inspection; reserves both files and always rolls back."""
    authorization = _approval_input(serialized_approval,signature)
    _, approval, _ = governance._verify(config,*authorization)
    require(approval['subject']['kind'] == PREVIEW_KIND, 'foundation_preview_purpose')
    from .runtime_execution_claims import _Clock
    clock = _Clock()
    with _attached(config) as reserved:
        # No source writes or COMMIT are possible through this owner in preview.
        reserved.execute('PRAGMA query_only=ON')
        reserved.set_authorizer(_preview_authorizer)
        with a.connect(config.control) as control, a.connect(config.target) as target:
            control.execute('BEGIN');target.execute('BEGIN')
            plan = _plan(config,control,target,None,None,operator=approval['subject']['operator'],
                         reason=approval['subject']['reason'],signed_authorization=authorization)
            _signed_session(config,control,target,authorization)
            for key,path in (('control',config.control),('target',config.target)):
                require(asdict(a.target_identity(path)) == plan['physical'][key], 'foundation_physical_changed')
            clock.read()
            require(a.timestamp(runtime._utc_now()) < a.timestamp(plan['deadline_at_utc']), 'foundation_plan_expired')
    return dict(plan=plan,plan_sha256=digest(plan),generation=5,h0=plan['h0'],h1=plan['h1'],
                read_only=True,source_databases_modified=False,execution_authority=False,
                preconditions=['enrolled_generation_5_h0','exact_profile_physical_identity','verified_owner',
                               'live_profile_scoped_primary_and_mfa_admin_records','independent_signed_authorization',
                               'not_activated','delete_journals_full_synchronization','empty_work_and_claims',
                               'exact_control_topology','all_other_readiness_prerequisites'])


def _approval_input(serialized_approval,signature):
    require(type(serialized_approval) is str and len(serialized_approval.encode('utf-8')) <= 65536
            and type(signature) is str and len(signature) == 88, 'foundation_approval_encoding')
    return serialized_approval,signature


def _install(db, plan=None):
    definitions = event_schema.definitions() if plan is None else lineage.additions(plan)
    for name, sql in definitions.items():
        verb = 'CREATE TABLE ' if sql.startswith('CREATE TABLE ') else 'CREATE TRIGGER '
        require(sql.startswith(verb+name+' '), 'foundation_package_definition_changed')
        db.execute(sql.replace(verb+name+' ',verb+ALIAS+'.'+name+' ',1))
    guard = claims.CLAIMS+'_scope_guard'
    db.execute('DROP TRIGGER main.'+guard)
    sql = lineage.upgrade_definitions(claims.definitions())[guard]
    db.execute(sql.replace('CREATE TRIGGER '+guard+' ','CREATE TRIGGER main.'+guard+' ',1))


def _validate_after(db, plan):
    tables = {name for name, sql in lineage.additions(plan).items() if sql.startswith('CREATE TABLE ')}
    require(_fingerprint(db,ALIAS) == plan['h1'] and _data(db,ALIAS,exclude=tables) == plan['target_data_sha256'],
            'foundation_target_changed')
    require(lineage.normalized_manifest({row[1]:row[3] for row in _objects(db)}) == plan['control_after_sha256'],
            'foundation_control_changed')
    for name in tables:
        require(db.execute('SELECT COUNT(*) FROM '+ALIAS+'.'+name).fetchone()[0] == 0, 'foundation_created_target_data')
    require(not db.execute('PRAGMA '+ALIAS+'.foreign_key_check').fetchone(), 'foundation_foreign_key_failure')


def _commit(db):
    db.commit()


def complete(config, session_token, *, primary_token, serialized_approval, signature):
    # Existing public authentication preserves its normal denial semantics. The
    # reserved recheck below is RO and cannot update credentials or MFA counters.
    owner.require_recognition_admin(config,session_token,primary_token=primary_token)
    return _complete(config,session_token,primary_token,serialized_approval,signature)


def complete_approved(config, *, approved_plan_sha256, serialized_approval, signature):
    """Same atomic owner, independently signed exact plan, no token arguments."""
    runtime.r._check_sha(approved_plan_sha256)
    _approval_input(serialized_approval,signature)
    _, approval, _ = governance._verify(config,serialized_approval,signature)
    require(approval['subject']['kind'] == lineage.KIND
            and digest(approval['subject']['plan']) == approved_plan_sha256, 'foundation_plan_digest_mismatch')
    return _complete(config,None,None,serialized_approval,signature,signed=True)


def _complete(config, session_token, primary_token, serialized_approval, signature, *, signed=False):
    _approval_input(serialized_approval,signature)
    root, approval, _ = governance._verify(config,serialized_approval,signature)
    require(approval['subject']['kind'] == lineage.KIND, 'foundation_approval_purpose')
    plan = approval['subject']['plan']; lineage.validate_plan(plan)
    if not signed:
        require(approval['holder'] == dict(actor_id=plan['owner_id'],primary_sha256=a.token_hash(primary_token),
                                         session_sha256=a.token_hash(session_token)), 'foundation_approval_holder')
    from .runtime_execution_claims import _Clock
    clock = _Clock()
    with _attached(config) as db:
        with a.connect(config.control) as control, a.connect(config.target) as target:
            control.execute('BEGIN');target.execute('BEGIN')
            current = _plan(config,control,target,session_token,primary_token,operator=plan['operator'],reason=plan['reason'],
                            created_at=plan['created_at_utc'],deadline=plan['deadline_at_utc'],
                            signed_authorization=(serialized_approval,signature) if signed else None)
            require(current == plan, 'foundation_plan_changed')
        additions = lineage.additions(plan)
        db.set_authorizer(lambda *args: _authorizer(*args, additions=additions))
        if plan['package'] == lineage.PACKAGE:
            _install(db)
        else:
            _install(db, plan)
        _validate_after(db,plan)
        governance._verify(config,serialized_approval,signature)
        now = runtime._utc_now()
        require(a.timestamp(now) < a.timestamp(plan['deadline_at_utc']), 'foundation_plan_expired')
        a._audit(db,lineage.ACTION,plan['owner_id'],now,
                 dict(package=plan['package'],plan=plan,plan_sha256=digest(plan),approval=serialized_approval,
                      signature=signature,state='CONSUMED'))
        lineage.verify(db)
        for key,path in (('control',config.control),('target',config.target)):
            require(asdict(a.target_identity(path)) == plan['physical'][key], 'foundation_physical_changed')
        clock.read()
        require(a.timestamp(runtime._utc_now()) < min(a.timestamp(plan['deadline_at_utc']),a.timestamp(approval['expires_at_utc'])),
                'foundation_approval_expired')
        _commit(db)
        require(not db.in_transaction, 'foundation_commit_unconfirmed')
    with a.connect(config.control) as control, a.connect(config.target) as target:
        control.execute('BEGIN');target.execute('BEGIN')
        runtime._identity_snapshot(config,control,target,runtime._utc_now())
        execution_schema.check_schema(target)
    return dict(package=plan['package'],generation=5,state='COMPLETED',schema_sha256=plan['h1'],
                production_state='NOT_ACTIVATED',execution_authority=False)


def inspect(config):
    config.paths()
    with a.connect(config.control) as control, a.connect(config.target) as target:
        control.execute('BEGIN'); target.execute('BEGIN')
        binding, profile, _ = runtime._history(control)
        plan = lineage.verify(control)
        actual = a.observe_target(target)['schema_sha256']
        lineage.validate_target(control,target,binding,profile,actual)
        return dict(state='COMPLETED' if plan else 'NOT_COMPLETED',generation=binding['generation'],
                    profile_sha256=profile['profile_sha256'],enrolled_schema_sha256=profile['target_schema_sha256'],
                    current_schema_sha256=actual,activation_state=local_readiness._state(control,binding)['state'],
                    execution_authority=False)
