"""Inert attempt DATA/storage. No producer, continuation or execution authority."""

from dataclasses import asdict
from pathlib import Path
import sqlite3

from . import administration as a, runtime_profile_schema as p
from . import runtime_activation_authority_schema as authority
from . import runtime_operation_contract as operation, runtime_execution_claim_schema as claims
from .rules import canonical, digest
from .trust import fields, identity, load, require


MIGRATION = 'recognition-runtime-execution-attempt-storage-v1'
ACTION = 'runtime_execution_attempt_schema_installed'
CREATE_ACTION = 'runtime_execution_attempt_created'
ATTEMPTS = 'recognition_runtime_execution_attempts'
HISTORY = 'recognition_runtime_execution_attempt_history'
FORMAT = 'recognition-runtime-live-attempt-v1'
EVENT_FORMAT = 'recognition-runtime-attempt-created-event-v1'
BODY_FIELDS = ('format','attempt_id','authority_id','authority_sha256','created_at_utc','expires_at_utc')
EVENT_FIELDS = ('format','attempt_id','attempt_sha256','sequence','state','at_utc','previous_sha256','actor_id','reason')
SCOPE_FIELDS = ('operation_reference','runtime_target','physical_snapshot','activation','approval',
                'authentication','dependencies','emergency_stop')


def validate_attempt(value):
    operation._json(value); fields(value, BODY_FIELDS)
    require(len(canonical(value).encode('utf-8')) <= 4096 and value['format'] == FORMAT, 'runtime_attempt_format')
    identity(value['attempt_id']); identity(value['authority_id']); p._check_sha(value['authority_sha256'])
    require(authority._time(value['created_at_utc']) < authority._time(value['expires_at_utc']), 'runtime_attempt_lifetime')
    return operation._copy(value)


def parse_attempt(serialized, *, attempt_sha256):
    require(type(serialized) is str and len(serialized.encode('utf-8')) <= 4096, 'runtime_attempt_size_limit')
    value = validate_attempt(load(serialized)); p._check_sha(attempt_sha256)
    require(canonical(value) == serialized and digest(value) == attempt_sha256, 'runtime_attempt_integrity')
    return value


def attempt_digest(value):
    return digest(validate_attempt(value))


def _authority(conn, value):
    # Durable historical validation only. Never accept a supplied authority body.
    authority.check_rows(conn)
    row = conn.execute(f'SELECT * FROM {authority.AUTHORITIES} WHERE authority_id=?', (value['authority_id'],)).fetchone()
    require(row is not None and row['body_sha256'] == value['authority_sha256'], 'runtime_attempt_authority_mismatch')
    return authority.parse_authority(row['body_json'], authority_sha256=row['body_sha256'])


def validate_binding(conn, value, *, expected_scope=None):
    """Compare DATA to durable authority. Not authentication/current admission."""
    value = validate_attempt(value); body = _authority(conn, value)
    require(authority._time(body['issued_at_utc']) <= authority._time(value['created_at_utc'])
            and value['expires_at_utc'] == body['expires_at_utc'], 'runtime_attempt_authority_lifetime')
    if expected_scope is not None:
        operation._json(expected_scope); fields(expected_scope, SCOPE_FIELDS)
        require(canonical(expected_scope) == canonical({k:body[k] for k in SCOPE_FIELDS}), 'runtime_attempt_scope_mismatch')
    return operation._copy(body)


def validate_expiry(value, *, now):
    """Timestamp comparison only; supplied time/data never grants permission."""
    value = validate_attempt(value); moment = authority._time(now)
    require(authority._time(value['created_at_utc']) <= moment < authority._time(value['expires_at_utc']),
            'runtime_attempt_expired_or_clock_rollback')


def validate_created(conn, value, *, attempt):
    operation._json(value); fields(value, EVENT_FIELDS)
    require(len(canonical(value).encode('utf-8')) <= 16384, 'runtime_attempt_event_size_limit')
    body = validate_binding(conn, attempt)
    require(value['format'] == EVENT_FORMAT and value['attempt_id'] == attempt['attempt_id']
            and value['attempt_sha256'] == attempt_digest(attempt) and type(value['sequence']) is int
            and value['sequence'] == 1 and value['state'] == 'ATTEMPT_CREATED'
            and value['previous_sha256'] is None and value['at_utc'] == attempt['created_at_utc']
            and type(value['actor_id']) is int and value['actor_id'] == body['runtime_target']['owner_id']
            and value['reason'] == body['producer_ceremony']['reason'], 'runtime_attempt_genesis_only')
    return operation._copy(value)


def parse_created(conn, serialized, *, event_sha256, attempt):
    require(type(serialized) is str and len(serialized.encode('utf-8')) <= 16384, 'runtime_attempt_event_size_limit')
    value = validate_created(conn, load(serialized), attempt=attempt); p._check_sha(event_sha256)
    require(canonical(value) == serialized and digest(value) == event_sha256, 'runtime_attempt_event_integrity')
    return value


def definitions():
    c = p.column
    json_check = lambda limit: ("typeof(body_json)='text' AND instr(body_json,char(0))=0 "
        f"AND length(CAST(body_json AS BLOB))<={limit} AND json_valid(body_json) AND json_type(body_json)='object'")
    cols = [c('attempt_id','TEXT',p.uuid('attempt_id')), c('authority_id','TEXT',p.uuid('authority_id')),
        c('authority_sha256','TEXT',p.sha('authority_sha256')), c('created_at','INTEGER',p.integer('created_at')),
        c('expires_at','INTEGER',p.integer('expires_at')), c('body_json','TEXT',json_check(4096)),
        c('body_sha256','TEXT',p.sha('body_sha256')), c('audit_sequence','INTEGER',p.integer('audit_sequence',1,2**63-1)),
        'PRIMARY KEY(attempt_id)', 'UNIQUE(authority_id)', 'UNIQUE(body_sha256)', 'UNIQUE(audit_sequence)',
        'CHECK(created_at<expires_at)', f'FOREIGN KEY(authority_id) REFERENCES {authority.AUTHORITIES}(authority_id)',
        f'FOREIGN KEY(authority_sha256) REFERENCES {authority.AUTHORITIES}(body_sha256)',
        'FOREIGN KEY(audit_sequence) REFERENCES recognition_admin_audit(sequence) DEFERRABLE INITIALLY DEFERRED']
    history = [c('attempt_id','TEXT',p.uuid('attempt_id')), c('sequence','INTEGER',"typeof(sequence)='integer' AND sequence=1"),
        c('state','TEXT',"state='ATTEMPT_CREATED'"), c('at','INTEGER',p.integer('at')),
        'previous_sha256 TEXT CHECK(previous_sha256 IS NULL)', c('body_json','TEXT',json_check(16384)),
        c('body_sha256','TEXT',p.sha('body_sha256')), c('audit_sequence','INTEGER',p.integer('audit_sequence',1,2**63-1)),
        'PRIMARY KEY(attempt_id,sequence)', 'UNIQUE(body_sha256)', 'UNIQUE(audit_sequence)',
        f'FOREIGN KEY(attempt_id) REFERENCES {ATTEMPTS}(attempt_id)',
        'FOREIGN KEY(audit_sequence) REFERENCES recognition_admin_audit(sequence) DEFERRABLE INITIALLY DEFERRED']
    result = {ATTEMPTS:f"CREATE TABLE {ATTEMPTS} ({', '.join(cols)})", HISTORY:f"CREATE TABLE {HISTORY} ({', '.join(history)})"}
    for table, keys in ((ATTEMPTS,[('attempt_id',),('authority_id',),('body_sha256',),('audit_sequence',)]),
                        (HISTORY,[('attempt_id','sequence'),('body_sha256',),('audit_sequence',)])):
        for verb in ('UPDATE','DELETE'):
            name = table+'_immutable_'+verb.lower()
            result[name] = f"CREATE TRIGGER {name} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_runtime_attempt'); END"
        name = table+'_immutable_replace'
        collision = ' OR '.join('('+' AND '.join(f'{k}=NEW.{k}' for k in key)+')' for key in keys)
        result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN EXISTS(SELECT 1 FROM {table} WHERE {collision}) BEGIN SELECT RAISE(ABORT,'immutable_runtime_attempt'); END"
    def guard(name, table, condition):
        result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN NOT COALESCE(({condition}),0) BEGIN SELECT RAISE(ABORT,'runtime_attempt_scope_mismatch'); END"
    j = lambda key: f"json_extract(NEW.body_json,'$.{key}')"
    guard(ATTEMPTS+'_binding_guard', ATTEMPTS,
        f"{j('format')}='{FORMAT}' AND (SELECT count(*) FROM json_each(NEW.body_json))=6 "
        f"AND {j('attempt_id')}=NEW.attempt_id AND {j('authority_id')}=NEW.authority_id AND {j('authority_sha256')}=NEW.authority_sha256 "
        f"AND {j('created_at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.created_at,'unixepoch') "
        f"AND {j('expires_at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.expires_at,'unixepoch') "
        'AND NOT EXISTS(SELECT 1 FROM recognition_admin_audit WHERE sequence=NEW.audit_sequence) '
        f'AND EXISTS(SELECT 1 FROM {authority.AUTHORITIES} a JOIN {authority.LIFECYCLE} g ON g.authority_id=a.authority_id '
        "WHERE a.authority_id=NEW.authority_id AND a.body_sha256=NEW.authority_sha256 AND g.state='AUTHORIZED' AND g.sequence=1 "
        'AND a.issued_at<=NEW.created_at AND a.expires_at=NEW.expires_at)')
    guard(HISTORY+'_genesis_guard', HISTORY,
        f"{j('format')}='{EVENT_FORMAT}' AND (SELECT count(*) FROM json_each(NEW.body_json))=9 "
        f"AND {j('attempt_id')}=NEW.attempt_id AND json_type(NEW.body_json,'$.sequence')='integer' AND {j('sequence')}=1 "
        f"AND {j('state')}='ATTEMPT_CREATED' AND json_type(NEW.body_json,'$.previous_sha256')='null' "
        f"AND {j('at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.at,'unixepoch') "
        'AND NOT EXISTS(SELECT 1 FROM recognition_admin_audit WHERE sequence=NEW.audit_sequence) '
        f'AND EXISTS(SELECT 1 FROM {ATTEMPTS} t JOIN {authority.AUTHORITIES} a ON a.authority_id=t.authority_id '
        f"WHERE t.attempt_id=NEW.attempt_id AND t.body_sha256={j('attempt_sha256')} AND t.created_at=NEW.at "
        f"AND t.audit_sequence=NEW.audit_sequence AND json_type(NEW.body_json,'$.actor_id')='integer' AND a.owner_id={j('actor_id')} "
        f"AND json_extract(a.body_json,'$.producer_ceremony.reason')={j('reason')})")
    name = ATTEMPTS+'_audit_guard'
    result[name] = (f'CREATE TRIGGER {name} BEFORE INSERT ON recognition_admin_audit '
        f'WHEN EXISTS(SELECT 1 FROM {ATTEMPTS} WHERE audit_sequence=NEW.sequence) '
        f'BEGIN SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM {ATTEMPTS} t JOIN {HISTORY} h ON h.attempt_id=t.attempt_id '
        f'JOIN {authority.AUTHORITIES} a ON a.authority_id=t.authority_id WHERE t.audit_sequence=NEW.sequence AND h.audit_sequence=NEW.sequence '
        f"AND json_extract(NEW.body_json,'$.action')='{CREATE_ACTION}' AND json_type(NEW.body_json,'$.actor')='integer' "
        "AND json_extract(NEW.body_json,'$.actor')=a.owner_id AND json_extract(NEW.body_json,'$.at_utc')=json_extract(h.body_json,'$.at_utc') "
        "AND json_extract(NEW.body_json,'$.subject.attempt_id')=t.attempt_id AND json_extract(NEW.body_json,'$.subject.attempt_sha256')=t.body_sha256 "
        "AND json_type(NEW.body_json,'$.subject.event_sequence')='integer' AND json_extract(NEW.body_json,'$.subject.event_sequence')=1 "
        "AND json_extract(NEW.body_json,'$.subject.event_sha256')=h.body_sha256) THEN RAISE(ABORT,'runtime_attempt_audit_mismatch') END; END")
    return result


def present(conn):
    from .administration_schema import _control_names
    names = _control_names(conn)
    return any(n.startswith((ATTEMPTS,HISTORY)) for n in names) or ('recognition_admin_audit' in names and bool(authority._rows(conn,ACTION)))


def check_manifest_transition(conn):
    from . import runtime_schema_package_lineage as lineage
    if lineage.present(conn):
        return lineage.subject(conn, 'T')
    from .runtime_enrollment_transition_schema import historical_manifest
    from .administration_schema import _control_objects
    expected = definitions()
    actual = dict(_control_objects(conn))
    require(all(n in actual and ' '.join(actual[n].split()) == ' '.join(sql.split()) for n,sql in expected.items()), 'runtime_attempt_partial_schema')
    rows = authority._rows(conn,ACTION)
    require(len(rows) == 1, 'runtime_attempt_migration_audit')
    audit = authority._record(rows[0]); subject = audit['subject']
    fields(subject, ('migration_id','previous_schema_sha256','installed_schema_sha256','installation_id','generation','reason'))
    require(subject['migration_id'] == MIGRATION and subject['installed_schema_sha256'] == historical_manifest(conn)
            and subject['previous_schema_sha256'] == historical_manifest(conn,exclude=expected), 'runtime_attempt_migration_manifest')
    identity(subject['installation_id']); operation._positive(subject['generation'])
    authority._reason(subject['reason']); authority._reason(audit['actor']); authority._time(audit['at_utc'])
    binding = conn.execute('SELECT body_json FROM recognition_admin_bindings WHERE generation=?',(subject['generation'],)).fetchone()
    require(binding is not None and load(binding[0])['installation_id'] == subject['installation_id'], 'runtime_attempt_migration_scope')
    prior = authority._rows(conn,authority.ACTION)
    require(len(prior) == 1 and prior[0]['sequence'] < rows[0]['sequence']
            and authority._record(prior[0])['subject']['installed_schema_sha256'] == subject['previous_schema_sha256'],
            'runtime_attempt_migration_predecessor')
    return subject


def authority_manifest(conn, *, exclude=()):
    """S1 reconstruction only after validating the exact recognized S2 transition."""
    from . import runtime_schema_package_lineage as lineage
    if lineage.present(conn):
        return lineage.manifest_at(conn, 'A', exclude=exclude)
    if present(conn):
        subject = check_manifest_transition(conn)
        # That validator just reconstructed and verified the exact S1 projection.
        # Reuse only its immutable digest, only inside this unchanged native
        # transaction/call. No admission/history result survives to _finish().
        # Unknown adapters and unreserved/additional-exclusion readers keep all
        # original reads and their ownership hooks.
        if (type(conn) is sqlite3.Connection and conn.in_transaction
                and type(exclude) is tuple and not exclude):
            return subject['previous_schema_sha256']
        from .runtime_enrollment_transition_schema import historical_manifest
        return historical_manifest(conn,exclude=set(exclude)|set(definitions()))
    return claims.manifest(conn,exclude=exclude)


def check_rows(conn):
    check_manifest_transition(conn)
    for row in conn.execute(f'SELECT * FROM {ATTEMPTS} ORDER BY attempt_id'):
        value = parse_attempt(row['body_json'],attempt_sha256=row['body_sha256'])
        validate_binding(conn,value)
        require(row['attempt_id'] == value['attempt_id'] and row['authority_id'] == value['authority_id']
                and row['authority_sha256'] == value['authority_sha256'] and row['created_at'] == authority._time(value['created_at_utc'])
                and row['expires_at'] == authority._time(value['expires_at_utc']), 'runtime_attempt_columns')
        history = conn.execute(f'SELECT * FROM {HISTORY} WHERE attempt_id=?',(row['attempt_id'],)).fetchall()
        require(len(history) == 1, 'runtime_attempt_genesis_missing')
        h = history[0]; event = parse_created(conn,h['body_json'],event_sha256=h['body_sha256'],attempt=value)
        require(h['sequence'] == 1 and h['state'] == 'ATTEMPT_CREATED' and h['previous_sha256'] is None
                and h['at'] == row['created_at'] and h['audit_sequence'] == row['audit_sequence'], 'runtime_attempt_event_columns')
        audit_row = conn.execute('SELECT * FROM recognition_admin_audit WHERE sequence=?',(row['audit_sequence'],)).fetchone()
        require(audit_row is not None, 'runtime_attempt_audit_missing')
        audit = authority._record(audit_row)
        require(audit['action'] == CREATE_ACTION and type(audit['actor']) is int and audit['actor'] == event['actor_id']
                and audit['at_utc'] == event['at_utc'] and canonical(audit['subject']) == canonical(dict(
                    attempt_id=row['attempt_id'],attempt_sha256=row['body_sha256'],event_sequence=1,event_sha256=h['body_sha256'])),
                'runtime_attempt_audit_scope')
    require(not conn.execute('PRAGMA foreign_key_check').fetchone(), 'runtime_attempt_foreign_key_mismatch')


def inspect_attempt(control_path, *, attempt_id, authority_id=None):
    """Read-only historical DATA. VALID does not mean current or executable."""
    from .administration_schema import check_control
    from .runtime_execution_admission import _freeze
    identity(attempt_id)
    if authority_id is not None: identity(authority_id)
    require(type(control_path) is Path or isinstance(control_path,Path), 'runtime_attempt_control_path_required')
    require(control_path.is_absolute(), 'runtime_attempt_control_path_required')
    result = dict(attempt_id=attempt_id,execution_authority=False,retry_authorized=False)
    try:
        with a.connect(control_path) as conn:
            conn.execute('BEGIN'); check_control(conn)
            require(present(conn), 'runtime_attempt_storage_not_installed')
            rows = conn.execute(f'SELECT * FROM {ATTEMPTS} WHERE attempt_id=? OR authority_id=?',(attempt_id,authority_id)).fetchall()
            if not rows: return _freeze(dict(result,status='MISSING'))
            if len(rows) != 1 or rows[0]['attempt_id'] != attempt_id or authority_id is not None and rows[0]['authority_id'] != authority_id:
                return _freeze(dict(result,status='CONFLICTING'))
            row = rows[0]
            event = conn.execute(f'SELECT body_sha256 FROM {HISTORY} WHERE attempt_id=?',(attempt_id,)).fetchone()
            return _freeze(dict(result,status='VALID',historical_only=True,state='ATTEMPT_CREATED',event_sha256=event[0],attempt_sha256=row['body_sha256'],
                attempt=parse_attempt(row['body_json'],attempt_sha256=row['body_sha256'])))
    except (ValueError,OSError,sqlite3.Error,KeyError,TypeError):
        return _freeze(dict(result,status='MALFORMED'))


def migrate(config, *, expected_generation, operator, reason):
    """Explicit inert local migration. Established query-only target reservation."""
    from . import administration_schema as base, runtime_challenges, runtime_validation as runtime, local_readiness
    require(type(config) is a.LocalAdministration, 'local_administration_required')
    config.paths(); operation._positive(expected_generation)
    runtime.enrollment._text(operator,200); authority._reason(reason)
    with a.connect(config.control,write=True) as control:
        control.execute('BEGIN IMMEDIATE'); base.check_control(control)
        require(authority._present(control), 'runtime_attempt_migration_prerequisites')
        binding = runtime_challenges._deployment_binding(control)
        require(binding['generation'] == expected_generation, 'runtime_attempt_migration_generation_conflict')
        require(asdict(a.target_identity(control)) == binding['control_identity'], 'control_identity_mismatch')
        require(binding['production_state'] == 'NOT_ACTIVATED' and local_readiness._state(control,binding)['state']
                in ('NOT_ACTIVATED','DEACTIVATED'), 'runtime_attempt_migration_requires_nonactive')
        if binding['runtime_profile_sha256'] is not None: runtime._history(control)
        with a.connect(config.target,write=True) as target:
            target.execute('BEGIN IMMEDIATE'); target.execute('PRAGMA query_only=ON')
            a._verify(config,control,target,binding)
            for path in (config.control,config.target):
                with a.connect(path) as preflight:
                    require([r[0] for r in preflight.execute('PRAGMA integrity_check')] == ['ok']
                            and not preflight.execute('PRAGMA foreign_key_check').fetchone(), 'runtime_attempt_migration_integrity')
            if present(control):
                check_rows(control); control.rollback()
                return dict(migration_id=MIGRATION,installed=False,generation=expected_generation)
            previous = claims.manifest(control); now = runtime._utc_now(); head = a._audit_head(control)
            require(head is None or authority._time(now) >= authority._time(load(head['body_json'])['at_utc']), 'administrative_clock_rollback')
            changes = target.total_changes
            control.execute('SAVEPOINT install_runtime_execution_attempts')
            try:
                for sql in definitions().values(): control.execute(sql)
                a._audit(control,ACTION,operator,now,dict(migration_id=MIGRATION,previous_schema_sha256=previous,
                    installed_schema_sha256=claims.manifest(control),installation_id=binding['installation_id'],
                    generation=expected_generation,reason=reason))
                base.check_control(control)
                require(control.execute(f'SELECT count(*) FROM {ATTEMPTS}').fetchone()[0] == 0
                        and control.execute(f'SELECT count(*) FROM {HISTORY}').fetchone()[0] == 0, 'runtime_attempt_migration_created_attempt')
                require(runtime_challenges._deployment_binding(control) == binding
                        and asdict(a.target_identity(control)) == binding['control_identity'], 'runtime_attempt_migration_scope_changed')
                a._verify(config,control,target,binding)
                require(target.total_changes == changes and target.execute('PRAGMA query_only').fetchone()[0] == 1, 'runtime_attempt_migration_target_changed')
                require(authority._time(runtime._utc_now()) >= authority._time(now), 'administrative_clock_rollback')
                control.execute('RELEASE install_runtime_execution_attempts'); control.commit()
                require(not control.in_transaction and target.in_transaction, 'runtime_attempt_migration_commit_unconfirmed')
                with a.connect(config.control) as verification:
                    verification.execute('BEGIN')
                    require([r[0] for r in verification.execute('PRAGMA integrity_check')] == ['ok']
                            and not verification.execute('PRAGMA foreign_key_check').fetchone(), 'runtime_attempt_migration_integrity')
            except BaseException:
                if control.in_transaction: control.rollback()
                raise
    return dict(migration_id=MIGRATION,installed=True,generation=expected_generation)
