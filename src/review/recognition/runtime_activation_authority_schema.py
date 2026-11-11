"""4e-12 inert control storage and DATA codecs. No authority issuer/capability.

Only AUTHORIZED genesis is specified. A parsed object, including a valid storage
fixture, is never a runtime credential or an execution/writer admission object.
"""

from dataclasses import asdict
import sqlite3

from . import runtime_profile_schema as p, runtime_operation_contract as operation
from .rules import canonical, digest
from .trust import fields, identity, load, require, utc


MIGRATION = 'recognition-runtime-activation-authority-storage-v1'
ACTION = 'runtime_activation_authority_schema_installed'
AUTHORITIES = 'recognition_runtime_execution_authorities'
LIFECYCLE = 'recognition_runtime_execution_lifecycle'
FORMAT = 'recognition-runtime-execution-authority-v1'
EVENT_FORMAT = 'recognition-runtime-execution-lifecycle-event-v1'
EVIDENCE_FORMAT = 'recognition-runtime-authorized-genesis-evidence-v1'
LIFETIME = 'recognition-runtime-authority-lifetime-120s-v1'
READINESS = 'recognition-runtime-readiness-recompute-v1'
STEP = 'recognition-runtime-authority-step-up-v1'
CONFIRMATION = 'recognition-runtime-authority-confirmation-v1'
STEP_ACTION = 'runtime_authority_step_up_issued'
CONFIRM_ACTION = 'runtime_authority_confirmation_issued'
CONSUME_ACTION = 'runtime_authority_confirmation_consumed'
ISSUE_ACTION = 'runtime_execution_authority_issued'
MAX_BYTES = 1024 * 1024
BODY_FIELDS = '''format authority_id operation_reference runtime_target physical_snapshot
activation approval authentication producer_ceremony dependencies emergency_stop readiness
issued_at_utc expires_at_utc lifetime_policy'''.split()
REFERENCE_FIELDS = '''operation_id operation_sha256 event_id event_sha256 preparation_id
preparation_sha256 writer_family writer_manifest_sha256 population_sha256 proposal_reference'''.split()
EVENT_FIELDS = '''format authority_id authority_sha256 operation_id operation_sha256 sequence
state kind at_utc previous_sha256 entry_sha256 seal_sha256 receipt_sha256 actor_id reason evidence'''.split()
SUBJECT_FIELDS = '''operation_reference runtime_target physical_snapshot activation approval
authentication dependencies emergency_stop readiness reason'''.split()


def _json(value):
    operation._json(value)
    require(len(canonical(value).encode('utf-8')) <= MAX_BYTES, 'runtime_authority_size_limit')


def _time(value):
    from .administration import timestamp
    result = timestamp(value)
    require(0 <= result <= p.MAX_TIME, 'runtime_authority_timestamp')
    return result


def _reason(value):
    from .runtime_approval_ceremony import _reason as validate
    validate(value)


def validate_authority(value):
    """Validate detached canonical DATA, never current scope or permission."""
    from . import runtime_validation as runtime, dependencies, local_execution
    from .runtime_approval_ceremony import _reference
    _json(value)
    fields(value, BODY_FIELDS)
    require(value['format'] == FORMAT, 'runtime_authority_format')
    from .runtime_authority_lifetime_policy import seconds
    lifetime = seconds(value['lifetime_policy'])
    identity(value['authority_id'])
    scope, ref = value['runtime_target'], value['operation_reference']
    operation._shape(scope)
    fields(ref, REFERENCE_FIELDS)
    for key in ('operation_id', 'event_id', 'preparation_id'):
        identity(ref[key])
    for key in REFERENCE_FIELDS:
        if key.endswith('_sha256'):
            p._check_sha(ref[key])
    require(ref['writer_family'] in local_execution.SUPPORTED, 'runtime_authority_family')
    _reference(ref['proposal_reference'])
    require(ref['proposal_reference']['operation_id'] == ref['operation_id']
            and ref['proposal_reference']['operation_sha256'] == ref['operation_sha256'],
            'runtime_authority_proposal_scope')
    physical = value['physical_snapshot']
    fields(physical, ('target', 'control_identity'))
    fields(physical['target'], ('observation', 'schema_sha256'))
    p._check_sha(physical['target']['schema_sha256'])
    for observed in (physical['target']['observation'], physical['control_identity']):
        runtime._physical(observed)
    require(physical['target']['observation']['hostname'] == physical['control_identity']['hostname'],
            'runtime_authority_hostname_scope')
    fields(value['activation'], ('sequence', 'event_sha256'))
    operation._positive(value['activation']['sequence'])
    p._check_sha(value['activation']['event_sha256'])
    fields(value['approval'], ('approval_id', 'approval_sha256', 'effective_history_sha256'))
    identity(value['approval']['approval_id'])
    for key in ('approval_sha256', 'effective_history_sha256'):
        p._check_sha(value['approval'][key])
    fields(value['authentication'], ('actor_id', 'primary_sha256', 'session_sha256'))
    operation._positive(value['authentication']['actor_id'])
    require(value['authentication']['actor_id'] == scope['owner_id'], 'runtime_authority_actor_scope')
    for key in ('primary_sha256', 'session_sha256'):
        p._check_sha(value['authentication'][key])
    ceremony = value['producer_ceremony']
    fields(ceremony, ('step_artifact_sha256', 'confirmation_artifact_sha256',
                     'confirmation_token_sha256', 'decision', 'reason'))
    for key in ('step_artifact_sha256', 'confirmation_artifact_sha256', 'confirmation_token_sha256'):
        p._check_sha(ceremony[key])
    require(ceremony['decision'] == 'authorize_runtime_execution', 'runtime_authority_decision')
    _reason(ceremony['reason'])
    for key in ('dependencies', 'emergency_stop'):
        fields(value[key], ('snapshot', 'snapshot_sha256'))
        p._check_sha(value[key]['snapshot_sha256'])
        require(digest(value[key]['snapshot']) == value[key]['snapshot_sha256'], 'runtime_authority_snapshot_digest')
    dep = value['dependencies']['snapshot']
    fields(dep, ('format', 'family', 'manifest_sha256', 'boundary', 'observations', 'sha256'))
    fields(dep['observations'], ('assignment_inventory', 'review_evidence', 'completions',
        'qualification_rules', 'existence', 'identity', 'current_active', 'policy', 'permanent_records', 'scope_snapshot'))
    p._check_sha(dep['sha256'])
    require(dep['format'] == dependencies.FORMAT and dep['boundary'] == dependencies.BOUNDARY
            and dep['family'] == ref['writer_family'] and dep['manifest_sha256'] == ref['writer_manifest_sha256']
            and dep['sha256'] == digest({k:v for k,v in dep.items() if k != 'sha256'}), 'runtime_authority_dependencies')
    stop = value['emergency_stop']['snapshot']
    fields(stop, ('sequence', 'active', 'reason', 'actor', 'recorded_at_utc', 'previous_sha256'))
    operation._positive(stop['sequence'])
    require(stop['active'] is False, 'runtime_authority_stop')
    _reason(stop['reason']); _reason(stop['actor'])
    _time(stop['recorded_at_utc'])
    if stop['previous_sha256'] is not None:
        p._check_sha(stop['previous_sha256'])
    require((stop['sequence'] == 1) == (stop['previous_sha256'] is None), 'runtime_authority_stop_history')
    fields(value['readiness'], ('assessment_sha256', 'assessed_at_utc', 'policy'))
    p._check_sha(value['readiness']['assessment_sha256'])
    require(value['readiness']['policy'] == READINESS, 'runtime_authority_readiness_policy')
    issued, expires = _time(value['issued_at_utc']), _time(value['expires_at_utc'])
    require(issued <= p.MAX_TIME-lifetime and issued < expires <= issued+lifetime
            and _time(stop['recorded_at_utc']) <= issued
            and _time(value['readiness']['assessed_at_utc']) <= issued, 'runtime_authority_lifetime')
    return operation._copy(value)


def parse_authority(serialized, *, authority_sha256):
    require(type(serialized) is str and len(serialized.encode('utf-8')) <= MAX_BYTES, 'runtime_authority_size_limit')
    value = validate_authority(load(serialized))
    p._check_sha(authority_sha256)
    require(canonical(value) == serialized and digest(value) == authority_sha256, 'runtime_authority_integrity')
    return value


def authority_digest(value):
    return digest(validate_authority(value))


def validate_genesis_evidence(value, *, authority):
    fields(value, ('format', 'authority_id', 'authority_sha256'))
    identity(value['authority_id']); p._check_sha(value['authority_sha256'])
    require(value['format'] == EVIDENCE_FORMAT and value['authority_id'] == authority['authority_id']
            and value['authority_sha256'] == authority_digest(authority), 'runtime_authority_genesis_evidence')
    return operation._copy(value)


def validate_genesis(value, *, authority):
    authority = validate_authority(authority)
    _json(value); fields(value, EVENT_FIELDS)
    ref = authority['operation_reference']
    validate_genesis_evidence(value['evidence'], authority=authority)
    require(value['format'] == EVENT_FORMAT and value['state'] == 'AUTHORIZED' and value['kind'] == 'AUTHORIZE'
            and type(value['sequence']) is int and value['sequence'] == 1
            and value['authority_id'] == authority['authority_id'] and value['authority_sha256'] == digest(authority)
            and value['operation_id'] == ref['operation_id'] and value['operation_sha256'] == ref['operation_sha256']
            and type(value['actor_id']) is int and value['actor_id'] == authority['runtime_target']['owner_id']
            and value['reason'] == authority['producer_ceremony']['reason']
            and value['at_utc'] == authority['issued_at_utc']
            and all(value[k] is None for k in ('previous_sha256', 'entry_sha256', 'seal_sha256', 'receipt_sha256')),
            'runtime_authority_genesis_only')
    return operation._copy(value)


def parse_genesis(serialized, *, event_sha256, authority):
    value = validate_genesis(load(serialized), authority=authority)
    p._check_sha(event_sha256)
    require(canonical(value) == serialized and digest(value) == event_sha256, 'runtime_authority_event_integrity')
    return value


def definitions():
    c = p.column
    columns = [c('authority_id', 'TEXT', p.uuid('authority_id'))]
    kinds = dict(operation_id='uuid', operation_sha256='sha', writer_manifest_sha256='sha',
        installation_id='uuid', target_id='uuid', generation='int', profile_sha256='sha', owner_id='int',
        auth_epoch='int', mfa_epoch='int', activation_sequence='int', activation_sha256='sha',
        approval_id='uuid', approval_sha256='sha', confirmation_sha256='sha')
    for name, kind in kinds.items():
        check = p.uuid(name) if kind == 'uuid' else p.sha(name) if kind == 'sha' else p.integer(name, 1, 2**63-1)
        columns.append(c(name, 'INTEGER' if kind == 'int' else 'TEXT', check))
    body_check = "typeof(body_json)='text' AND instr(body_json,char(0))=0 AND length(CAST(body_json AS BLOB))<=1048576 AND json_valid(body_json) AND json_type(body_json)='object'"
    columns += [c('issued_at', 'INTEGER', p.integer('issued_at', 0, p.MAX_TIME-120)),
        c('expires_at', 'INTEGER', p.integer('expires_at')), c('body_json', 'TEXT', body_check),
        c('body_sha256', 'TEXT', p.sha('body_sha256')), c('audit_sequence', 'INTEGER', p.integer('audit_sequence', 1, 2**63-1)),
        'PRIMARY KEY(authority_id)', 'CHECK(issued_at<expires_at AND expires_at<=issued_at+120)']
    unique = ['operation_id', 'writer_manifest_sha256', 'confirmation_sha256', 'body_sha256', 'audit_sequence']
    columns += [f'UNIQUE({key})' for key in unique]
    for local, table, key in (('generation', 'recognition_admin_bindings', 'generation'),
        ('profile_sha256', p.PROFILES, 'profile_sha256'), ('activation_sequence', 'recognition_local_activation', 'sequence'),
        ('approval_id', 'recognition_approvals', 'approval_id'), ('confirmation_sha256', 'recognition_admin_confirmations', 'token_hash'),
        ('audit_sequence', 'recognition_admin_audit', 'sequence')):
        columns.append(f'FOREIGN KEY({local}) REFERENCES {table}({key})'+
            (' DEFERRABLE INITIALLY DEFERRED' if local == 'audit_sequence' else ''))
    event = [c('authority_id', 'TEXT', p.uuid('authority_id')),
        c('sequence', 'INTEGER', "typeof(sequence)='integer' AND sequence=1"),
        c('state', 'TEXT', "state='AUTHORIZED'"), c('kind', 'TEXT', "kind='AUTHORIZE'"),
        c('at', 'INTEGER', p.integer('at'))]
    for name in ('previous_sha256', 'entry_sha256', 'seal_sha256', 'receipt_sha256'):
        event.append(f'{name} TEXT CHECK({name} IS NULL)')
    event += [c('body_json', 'TEXT', body_check), c('body_sha256', 'TEXT', p.sha('body_sha256')),
        c('audit_sequence', 'INTEGER', p.integer('audit_sequence', 1, 2**63-1)),
        'PRIMARY KEY(authority_id,sequence)', 'UNIQUE(body_sha256)', 'UNIQUE(audit_sequence)',
        f'FOREIGN KEY(authority_id) REFERENCES {AUTHORITIES}(authority_id)',
        'FOREIGN KEY(audit_sequence) REFERENCES recognition_admin_audit(sequence) DEFERRABLE INITIALLY DEFERRED']
    result = {AUTHORITIES: f"CREATE TABLE {AUTHORITIES} ({', '.join(columns)})",
              LIFECYCLE: f"CREATE TABLE {LIFECYCLE} ({', '.join(event)})"}
    for table, keys in ((AUTHORITIES, [('authority_id',)]+[(k,) for k in unique]),
                        (LIFECYCLE, [('authority_id','sequence'), ('body_sha256',), ('audit_sequence',)])):
        for verb in ('UPDATE', 'DELETE'):
            result[table+'_immutable_'+verb.lower()] = (f'CREATE TRIGGER {table}_immutable_{verb.lower()} BEFORE {verb} ON {table} '
                "BEGIN SELECT RAISE(ABORT,'immutable_runtime_activation_authority'); END")
        collision = ' OR '.join('('+' AND '.join(f'{k}=NEW.{k}' for k in key)+')' for key in keys)
        result[table+'_immutable_replace'] = (f'CREATE TRIGGER {table}_immutable_replace BEFORE INSERT ON {table} '
            f"WHEN EXISTS(SELECT 1 FROM {table} WHERE {collision}) BEGIN SELECT RAISE(ABORT,'immutable_runtime_activation_authority'); END")
    result[AUTHORITIES+'_scope_idx'] = f'CREATE INDEX {AUTHORITIES}_scope_idx ON {AUTHORITIES}(installation_id,target_id,generation,profile_sha256,activation_sequence)'
    result[LIFECYCLE+'_state_idx'] = f'CREATE INDEX {LIFECYCLE}_state_idx ON {LIFECYCLE}(state,authority_id)'
    def guard(name, table, condition):
        result[name] = (f'CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN NOT COALESCE(({condition}),0) '
                        "BEGIN SELECT RAISE(ABORT,'runtime_activation_authority_scope_mismatch'); END")
    j = lambda path: f"json_extract(NEW.body_json,'$.{path}')"
    mappings = dict(authority_id='authority_id', operation_id='operation_reference.operation_id',
        operation_sha256='operation_reference.operation_sha256', writer_manifest_sha256='operation_reference.writer_manifest_sha256',
        installation_id='runtime_target.installation_id', target_id='runtime_target.target_id', generation='runtime_target.generation',
        profile_sha256='runtime_target.runtime_profile_sha256', owner_id='runtime_target.owner_id', auth_epoch='runtime_target.auth_epoch',
        mfa_epoch='runtime_target.mfa_epoch', activation_sequence='activation.sequence', activation_sha256='activation.event_sha256',
        approval_id='approval.approval_id', approval_sha256='approval.approval_sha256', confirmation_sha256='producer_ceremony.confirmation_token_sha256')
    matches = ' AND '.join(f'{j(path)}=NEW.{key}' +
        (f" AND json_type(NEW.body_json,'$.{path}')='integer'" if kinds.get(key) == 'int' else '') for key,path in mappings.items())
    physical = []
    for prefix, path in (('target', 'physical_snapshot.target.observation'), ('control', 'physical_snapshot.control_identity')):
        physical += [f"{j(path+'.hostname')}=r.hostname", f"{j(path+'.database')}=r.{prefix}_path"]
        for key in ('device', 'inode'):
            physical += [f"json_type(NEW.body_json,'$.{path}.{key}')='integer'",
                         f"(NEW.body_json -> '$.{path}.{key}')=r.{prefix}_{key}"]
    guard(AUTHORITIES+'_scope_guard', AUTHORITIES,
        f"{matches} AND {j('format')}='{FORMAT}' AND {j('issued_at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.issued_at,'unixepoch') "
        f"AND {j('lifetime_policy')}='{LIFETIME}' AND json_type(NEW.body_json,'$.authentication.actor_id')='integer' "
        f"AND {j('authentication.actor_id')}=NEW.owner_id "
        f"AND {j('expires_at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.expires_at,'unixepoch') "
        'AND NOT EXISTS(SELECT 1 FROM recognition_admin_audit WHERE sequence=NEW.audit_sequence) '
        "AND EXISTS(SELECT 1 FROM recognition_admin_audit ca WHERE "
        f"json_extract(ca.body_json,'$.action')='{CONSUME_ACTION}' "
        "AND json_extract(ca.body_json,'$.actor')=NEW.owner_id "
        f"AND json_extract(ca.body_json,'$.at_utc')={j('issued_at_utc')} "
        "AND json_extract(ca.body_json,'$.subject.token_sha256')=NEW.confirmation_sha256 "
        f"AND json_extract(ca.body_json,'$.subject.artifact_sha256')={j('producer_ceremony.confirmation_artifact_sha256')}) "
        f'AND NOT EXISTS(SELECT 1 FROM recognition_runtime_execution_claims WHERE operation_id=NEW.operation_id) '
        'AND NOT EXISTS(SELECT 1 FROM recognition_execution_blocks WHERE operation_id=NEW.operation_id) '
        'AND EXISTS(SELECT 1 FROM recognition_execution_stops st '
        'WHERE st.sequence=(SELECT MAX(sequence) FROM recognition_execution_stops) '
        f"AND st.body_sha256={j('emergency_stop.snapshot_sha256')} AND json_extract(st.body_json,'$.active')=0) "
        f'AND EXISTS(SELECT 1 FROM recognition_admin_bindings b JOIN {p.PROFILES} r ON r.profile_sha256=NEW.profile_sha256 '
        'JOIN recognition_local_activation x ON x.sequence=NEW.activation_sequence '
        'JOIN recognition_approvals ap ON ap.approval_id=NEW.approval_id '
        'JOIN recognition_admin_confirmations c ON c.token_hash=NEW.confirmation_sha256 '
        'WHERE b.generation=NEW.generation AND b.generation=(SELECT MAX(generation) FROM recognition_admin_bindings) '
        f"AND b.body_sha256={j('runtime_target.binding_sha256')} AND json_extract(b.body_json,'$.runtime_profile_sha256')=r.profile_sha256 "
        'AND r.generation=NEW.generation AND r.installation_id=NEW.installation_id AND r.target_id=NEW.target_id AND r.owner_id=NEW.owner_id '
        f"AND r.target_schema_sha256={j('physical_snapshot.target.schema_sha256')} AND {' AND '.join(physical)} "
        'AND x.sequence=(SELECT MAX(sequence) FROM recognition_local_activation) AND x.body_sha256=NEW.activation_sha256 '
        "AND json_extract(x.body_json,'$.state')='ACTIVATED' AND json_extract(x.body_json,'$.scope')='trusted-local-production' "
        "AND json_extract(x.body_json,'$.actor_id')=NEW.owner_id "
        "AND json_extract(x.body_json,'$.target.installation_id')=NEW.installation_id "
        "AND json_extract(x.body_json,'$.target.target_id')=NEW.target_id "
        "AND json_extract(x.body_json,'$.target.restore_generation')=NEW.generation "
        "AND json_extract(ap.body_json,'$.format')='recognition-runtime-approval-v2' AND ap.operation_id=NEW.operation_id "
        'AND ap.body_sha256=NEW.approval_sha256 '
        "AND (SELECT state FROM recognition_approval_history WHERE approval_id=ap.approval_id ORDER BY sequence DESC LIMIT 1)='APPROVED' "
        f"AND (SELECT body_sha256 FROM recognition_approval_history WHERE approval_id=ap.approval_id ORDER BY sequence DESC LIMIT 1)={j('approval.effective_history_sha256')} "
        'AND c.used=1 AND c.actor=NEW.owner_id AND c.generation=NEW.generation '
        "AND c.operation_id='runtime-authority:'||NEW.operation_id AND c.operation_sha256=NEW.operation_sha256 "
        f"AND c.session_hash={j('authentication.session_sha256')} AND c.expires>=NEW.expires_at "
        'AND EXISTS(SELECT 1 FROM recognition_admin_primary pr JOIN recognition_admin_sessions s ON s.primary_hash=pr.token_hash '
        f"JOIN {p.AUTH} ps ON ps.token_kind='primary' AND ps.token_hash=pr.token_hash "
        f"JOIN {p.AUTH} ss ON ss.token_kind='session' AND ss.token_hash=s.token_hash JOIN recognition_admin_mfa m ON m.actor=s.actor "
        f"WHERE pr.token_hash={j('authentication.primary_sha256')} AND s.token_hash=c.session_hash "
        'AND pr.revoked=0 AND s.revoked=0 AND pr.actor=NEW.owner_id AND s.actor=NEW.owner_id '
        'AND pr.generation=NEW.generation AND s.generation=NEW.generation AND pr.auth_epoch=NEW.auth_epoch AND s.auth_epoch=NEW.auth_epoch '
        "AND s.mfa_epoch=NEW.mfa_epoch AND m.epoch=NEW.mfa_epoch AND m.state='ENROLLED' "
        'AND ps.profile_sha256=NEW.profile_sha256 AND ss.profile_sha256=NEW.profile_sha256 '
        'AND pr.created<=NEW.issued_at AND s.created<=NEW.issued_at AND pr.expires>=NEW.expires_at AND s.expires>=NEW.expires_at))')
    guard(LIFECYCLE+'_sequence_guard', LIFECYCLE,
        f"{j('format')}='{EVENT_FORMAT}' AND {j('state')}='AUTHORIZED' AND {j('kind')}='AUTHORIZE' "
        'AND NOT EXISTS(SELECT 1 FROM recognition_admin_audit WHERE sequence=NEW.audit_sequence) '
        f"AND json_type(NEW.body_json,'$.sequence')='integer' AND {j('sequence')}=1 AND {j('authority_id')}=NEW.authority_id "
        f"AND {j('at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.at,'unixepoch') AND "
        + ' AND '.join(f"json_type(NEW.body_json,'$.{k}')='null'" for k in ('previous_sha256','entry_sha256','seal_sha256','receipt_sha256'))+
        f" AND {j('evidence.format')}='{EVIDENCE_FORMAT}' AND {j('evidence.authority_id')}=NEW.authority_id "
        "AND json_type(NEW.body_json,'$.evidence')='object' AND (SELECT count(*) FROM json_each(NEW.body_json,'$.evidence'))=3 "
        f"AND {j('evidence.authority_sha256')}={j('authority_sha256')} "
        f'AND EXISTS(SELECT 1 FROM {AUTHORITIES} a WHERE a.authority_id=NEW.authority_id '
        f"AND a.body_sha256={j('authority_sha256')} AND a.operation_id={j('operation_id')} AND a.operation_sha256={j('operation_sha256')} "
        f"AND json_type(NEW.body_json,'$.actor_id')='integer' AND a.owner_id={j('actor_id')} "
        f"AND {j('reason')}=json_extract(a.body_json,'$.producer_ceremony.reason') AND a.issued_at=NEW.at AND a.audit_sequence=NEW.audit_sequence)")
    name = AUTHORITIES+'_audit_guard'
    result[name] = (f'CREATE TRIGGER {name} BEFORE INSERT ON recognition_admin_audit '
        f'WHEN EXISTS(SELECT 1 FROM {AUTHORITIES} WHERE audit_sequence=NEW.sequence) '
        f'BEGIN SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM {AUTHORITIES} a JOIN {LIFECYCLE} e ON e.authority_id=a.authority_id '
        "WHERE a.audit_sequence=NEW.sequence AND e.audit_sequence=NEW.sequence AND json_type(NEW.body_json,'$.actor')='integer' "
        f"AND json_extract(NEW.body_json,'$.action')='{ISSUE_ACTION}' AND json_extract(NEW.body_json,'$.actor')=a.owner_id "
        "AND json_extract(NEW.body_json,'$.at_utc')=json_extract(e.body_json,'$.at_utc') "
        "AND json_extract(NEW.body_json,'$.subject.authority_id')=a.authority_id AND json_extract(NEW.body_json,'$.subject.authority_sha256')=a.body_sha256 "
        "AND json_type(NEW.body_json,'$.subject.event_sequence')='integer' AND json_extract(NEW.body_json,'$.subject.event_sequence')=1 "
        "AND json_extract(NEW.body_json,'$.subject.event_sha256')=e.body_sha256) "
        "THEN RAISE(ABORT,'runtime_authority_audit_mismatch') END; END")
    return result


def _rows(conn, action):
    return conn.execute("SELECT * FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=? ORDER BY sequence",
                        (action,)).fetchall()


def _record(row):
    value = load(row['body_json'])
    require(canonical(value) == row['body_json'] and digest(value) == row['body_sha256'], 'runtime_authority_record_integrity')
    if 'action' in value:
        fields(value, ('action','actor','at_utc','subject','previous_sha256'))
        if value['action'] in (STEP_ACTION, CONFIRM_ACTION, CONSUME_ACTION, ISSUE_ACTION):
            operation._positive(value['actor'])
            require(type(value['subject']) is dict, 'runtime_authority_audit_subject')
    return value


def _present(conn):
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (AUTHORITIES,)).fetchone() or _rows(conn, ACTION))


def check_manifest_transition(conn):
    """Verify S1, projected only through the explicitly verified S2 extension."""
    from . import runtime_schema_package_lineage as lineage
    if lineage.present(conn):
        return lineage.subject(conn, 'A')
    from . import runtime_execution_claim_schema as claims
    from .runtime_execution_attempt_schema import authority_manifest
    from .administration_schema import _control_objects
    actual = dict(_control_objects(conn))
    expected = definitions()
    require(all(name in actual and ' '.join(actual[name].split()) == ' '.join(sql.split())
                for name,sql in expected.items()), 'runtime_authority_partial_schema')
    rows = _rows(conn, ACTION)
    require(len(rows) == 1, 'runtime_authority_migration_audit')
    audit = _record(rows[0]); subject = audit['subject']
    fields(subject, ('migration_id','previous_schema_sha256','installed_schema_sha256','installation_id','generation','reason'))
    require(subject['migration_id'] == MIGRATION
            and subject['installed_schema_sha256'] == authority_manifest(conn)
            and subject['previous_schema_sha256'] == authority_manifest(conn, exclude=expected), 'runtime_authority_migration_manifest')
    identity(subject['installation_id']); operation._positive(subject['generation'])
    _reason(subject['reason']); _reason(audit['actor']); _time(audit['at_utc'])
    binding = conn.execute('SELECT body_json FROM recognition_admin_bindings WHERE generation=?', (subject['generation'],)).fetchone()
    require(binding is not None and load(binding[0])['installation_id'] == subject['installation_id'], 'runtime_authority_migration_scope')
    prior = _rows(conn, claims.ACTION)
    require(len(prior) == 1 and prior[0]['sequence'] < rows[0]['sequence']
            and _record(prior[0])['subject']['installed_schema_sha256'] == subject['previous_schema_sha256'],
            'runtime_authority_migration_predecessor')
    return subject


def historical_claim_manifest(conn, *, exclude=()):
    """4d-1's original manifest, reconstructed only after verified transition."""
    from . import runtime_schema_package_lineage as lineage
    if lineage.present(conn):
        return lineage.manifest_at(conn, 'A', before=True, exclude=exclude)
    from . import runtime_execution_claim_schema as claims
    from .runtime_execution_attempt_schema import authority_manifest
    if _present(conn):
        subject = check_manifest_transition(conn)
        # The preceding validator has just verified this exact projection via
        # authority_manifest(exclude=definitions()). Reconstructing it again
        # cannot add information inside this native, unchanged transaction.
        # No result survives this call; final validation always runs afresh.
        # Preserve all reads/ownership hooks for unreserved or adapted handles.
        if type(conn) is sqlite3.Connection and conn.in_transaction and not exclude:
            return subject['previous_schema_sha256']
        return authority_manifest(conn, exclude=set(exclude) | set(definitions()))
    return authority_manifest(conn, exclude=exclude)


def _artifact(conn, expected_digest, action, kind):
    matches = [_record(row) for row in _rows(conn, action)
               if digest(_record(row)['subject']) == expected_digest]
    require(len(matches) == 1, 'runtime_authority_ceremony_missing')
    audit = matches[0]; value = audit['subject']
    fields(value, ('format','token_sha256','subject','subject_sha256','actor_id','primary_sha256','session_sha256',
        'issued_at_utc','expires_at_utc') + (('step_artifact_sha256','decision') if kind == CONFIRMATION else ()))
    _json(value); require(value['format'] == kind, 'runtime_authority_ceremony_format')
    fields(value['subject'], SUBJECT_FIELDS)
    for key in ('token_sha256','subject_sha256','primary_sha256','session_sha256'):
        p._check_sha(value[key])
    operation._positive(value['actor_id'])
    require(digest(value['subject']) == value['subject_sha256'] and audit['actor'] == value['actor_id']
            and audit['at_utc'] == value['issued_at_utc']
            and 0 < _time(value['expires_at_utc'])-_time(value['issued_at_utc']) <= 600, 'runtime_authority_ceremony_integrity')
    if kind == CONFIRMATION:
        p._check_sha(value['step_artifact_sha256'])
        require(value['decision'] == 'authorize_runtime_execution', 'runtime_authority_decision')
    return value


def _historical_scope(conn, body):
    """Stored references at issue time, not live permission or authentication."""
    from . import production_operations, runtime_approval_contract as approvals, local_readiness, execution
    scope, ref = body['runtime_target'], body['operation_reference']
    issued, expires = _time(body['issued_at_utc']), _time(body['expires_at_utc'])
    execution._stop(conn)  # Validate the history without treating an old inactive observation as current.
    stop = body['emergency_stop']['snapshot']
    stop_row = conn.execute('SELECT * FROM recognition_execution_stops WHERE sequence=?', (stop['sequence'],)).fetchone()
    require(stop_row is not None and _record(stop_row) == stop, 'runtime_authority_stop_scope')
    from . import runtime_proposal_records as records
    ack_ref = ref['proposal_reference']
    ack_row = conn.execute('SELECT * FROM recognition_admin_audit WHERE sequence=?',
                           (ack_ref['acknowledgement_sequence'],)).fetchone()
    require(ack_row is not None and ack_row['body_sha256'] == ack_ref['acknowledgement_sha256'], 'runtime_authority_ack_missing')
    ack = records.parse_acknowledgement(ack_row['body_json'], acknowledgement_sha256=ack_row['body_sha256'])
    require(ack['subject']['local_target'] == scope and _time(ack['at_utc']) <= issued
            and all(ack['subject'][key] == ref[key] for key in ('operation_id','operation_sha256','event_id',
                    'event_sha256','preparation_id','preparation_sha256')), 'runtime_authority_ack_scope')
    binding_row = conn.execute('SELECT * FROM recognition_admin_bindings WHERE generation=?', (scope['generation'],)).fetchone()
    profile_row = conn.execute(f'SELECT * FROM {p.PROFILES} WHERE profile_sha256=?', (scope['runtime_profile_sha256'],)).fetchone()
    require(binding_row is not None and profile_row is not None, 'runtime_authority_profile_missing')
    binding, profile = _record(binding_row), dict(profile_row)
    require(digest(binding) == scope['binding_sha256'] and binding['runtime_profile_sha256'] == profile['profile_sha256']
            and all(scope[k] == binding[k] == profile[k] for k in ('generation','installation_id','target_id','owner_id')),
            'runtime_authority_profile_scope')
    for prefix, physical in (('target', body['physical_snapshot']['target']['observation']), ('control', body['physical_snapshot']['control_identity'])):
        require(physical['hostname'] == profile['hostname'] and physical['database'] == profile[prefix+'_path']
                and str(physical['device']) == profile[prefix+'_device'] and str(physical['inode']) == profile[prefix+'_inode'],
                'runtime_authority_physical_scope')
    require(body['physical_snapshot']['target']['schema_sha256'] == profile['target_schema_sha256']
            == binding['target']['schema_sha256'], 'runtime_authority_schema_scope')
    act = conn.execute('SELECT * FROM recognition_local_activation WHERE sequence=?', (body['activation']['sequence'],)).fetchone()
    require(act is not None and act['body_sha256'] == body['activation']['event_sha256'], 'runtime_authority_activation_scope')
    activation = _record(act)
    local_readiness._state(conn, binding)  # Complete historical ledger integrity, not current permission.
    require(type(activation['sequence']) is int and activation['sequence'] == body['activation']['sequence']
            and type(activation['actor_id']) is int and activation['actor_id'] == scope['owner_id']
            and activation['state'] == 'ACTIVATED' and activation['scope'] == 'trusted-local-production'
            and activation['target'] == production_operations.local_target(binding) and _time(activation['at_utc']) <= issued,
            'runtime_authority_activation_scope')
    activation_audits = [_record(r) for r in _rows(conn, 'local_activation_state_recorded')
                         if _record(r)['subject'] == activation]
    require(len(activation_audits) == 1 and type(activation_audits[0]['actor']) is int
            and activation_audits[0]['actor'] == scope['owner_id']
            and activation_audits[0]['at_utc'] == activation['at_utc'], 'runtime_authority_activation_audit')
    ac = conn.execute('SELECT * FROM recognition_admin_confirmations WHERE token_hash=?', (activation.get('confirmation_sha256'),)).fetchone()
    require(ac is not None and ac['used'] == 1 and ac['actor'] == scope['owner_id'] == activation['actor_id']
            and ac['generation'] == scope['generation'] and ac['operation_id'] == 'activation:'+scope['installation_id']
            and ac['operation_sha256'] == digest(production_operations.local_target(binding))
            and ac['state_sha256'] == activation.get('ceremony_sha256'), 'runtime_authority_activation_ceremony')
    approved = approvals._historical(conn, body['approval']['approval_id'])
    ap = approved['approval']
    require(approved['approval_sha256'] == body['approval']['approval_sha256'] and ap['binding']['local_target'] == scope
            and ap['binding']['reference'] == ref['proposal_reference']
            and any(digest(h) == body['approval']['effective_history_sha256'] and h['state'] == 'APPROVED'
                    and _time(h['at_utc']) <= issued for h in approved['history']), 'runtime_authority_approval_scope')
    auth_deadlines = []
    for kind, table in (('primary','recognition_admin_primary'), ('session','recognition_admin_sessions')):
        proof = conn.execute(f'SELECT * FROM {table} WHERE token_hash=?', (body['authentication'][kind+'_sha256'],)).fetchone()
        link = conn.execute(f'SELECT * FROM {p.AUTH} WHERE token_kind=? AND token_hash=?',
                            (kind,body['authentication'][kind+'_sha256'])).fetchone()
        require(proof is not None and link is not None and link['profile_sha256'] == scope['runtime_profile_sha256']
                and proof['generation'] == scope['generation'] and proof['actor'] == scope['owner_id']
                and proof['auth_epoch'] == scope['auth_epoch'] and proof['created'] <= issued < expires <= proof['expires'],
                'runtime_authority_authentication_scope')
        auth_deadlines.append(proof['expires'])
        if kind == 'session':
            require(proof['primary_hash'] == body['authentication']['primary_sha256']
                    and proof['mfa_epoch'] == scope['mfa_epoch'], 'runtime_authority_authentication_scope')
    ceremony = body['producer_ceremony']
    step = _artifact(conn, ceremony['step_artifact_sha256'], STEP_ACTION, STEP)
    confirm = _artifact(conn, ceremony['confirmation_artifact_sha256'], CONFIRM_ACTION, CONFIRMATION)
    require(_time(step['issued_at_utc']) <= _time(confirm['issued_at_utc']), 'runtime_authority_ceremony_order')
    require(type(step['subject']['readiness']) is dict, 'runtime_authority_readiness_shape')
    expected = {key:body[key] for key in SUBJECT_FIELDS if key not in ('readiness','reason')}
    expected.update(readiness=step['subject']['readiness'], reason=ceremony['reason'])
    require(canonical(step['subject']) == canonical(confirm['subject']) == canonical(expected)
            and digest(expected['readiness']) == body['readiness']['assessment_sha256']
            and expected['readiness'].get('code_ready') is True
            and expected['readiness'].get('rehearsal_evidence_present') is True
            and expected['readiness'].get('activation_state') == 'ACTIVATED'
            and confirm['step_artifact_sha256'] == digest(step) and confirm['token_sha256'] == ceremony['confirmation_token_sha256'],
            'runtime_authority_confirmation_scope')
    for artifact in (step,confirm):
        require(artifact['actor_id'] == scope['owner_id'] and artifact['primary_sha256'] == body['authentication']['primary_sha256']
                and artifact['session_sha256'] == body['authentication']['session_sha256']
                and _time(artifact['issued_at_utc']) <= issued < expires <= _time(artifact['expires_at_utc']) <= min(auth_deadlines),
                'runtime_authority_confirmation_lifetime')
    from .runtime_authority_lifetime_policy import seconds
    require(expires == min(issued+seconds(body['lifetime_policy']), _time(step['expires_at_utc']), _time(confirm['expires_at_utc']), *auth_deadlines),
        'runtime_authority_lifetime_extension')
    row = conn.execute('SELECT * FROM recognition_admin_confirmations WHERE token_hash=?', (ceremony['confirmation_token_sha256'],)).fetchone()
    require(row is not None and row['used'] == 1 and row['session_hash'] == body['authentication']['session_sha256']
            and row['actor'] == scope['owner_id'] and row['generation'] == scope['generation']
            and row['operation_id'] == 'runtime-authority:'+ref['operation_id'] and row['operation_sha256'] == ref['operation_sha256']
            and row['state_sha256'] == step['subject_sha256'] and row['expires'] == _time(confirm['expires_at_utc']),
            'runtime_authority_confirmation_row')
    consumed = [_record(r) for r in _rows(conn, CONSUME_ACTION)
                if _record(r)['subject'].get('token_sha256') == ceremony['confirmation_token_sha256']]
    require(len(consumed) == 1 and consumed[0]['actor'] == scope['owner_id'] and consumed[0]['at_utc'] == body['issued_at_utc']
            and consumed[0]['subject'] == dict(format='recognition-runtime-authority-confirmation-consumption-v1',
                token_sha256=ceremony['confirmation_token_sha256'], artifact_sha256=digest(confirm), subject_sha256=confirm['subject_sha256']),
            'runtime_authority_consumption_audit')
    require(sum(_record(r)['subject'].get('step_artifact_sha256') == digest(step) for r in _rows(conn, CONFIRM_ACTION)) == 1,
            'runtime_authority_step_replayed')
    step_sequence = next(r['sequence'] for r in _rows(conn, STEP_ACTION) if digest(_record(r)['subject']) == digest(step))
    confirmation_sequence = next(r['sequence'] for r in _rows(conn, CONFIRM_ACTION) if digest(_record(r)['subject']) == digest(confirm))
    consumption_sequence = next(r['sequence'] for r in _rows(conn, CONSUME_ACTION)
                                if _record(r)['subject'].get('token_sha256') == ceremony['confirmation_token_sha256'])
    issuance_sequence = conn.execute(f'SELECT audit_sequence FROM {AUTHORITIES} WHERE authority_id=?',
                                      (body['authority_id'],)).fetchone()[0]
    require(ack_ref['acknowledgement_sequence'] < step_sequence < confirmation_sequence < consumption_sequence < issuance_sequence,
            'runtime_authority_ceremony_order')
    if body['lifetime_policy'] != LIFETIME:
        from . import runtime_schema_package_lineage as lineage
        edges = lineage.verify(conn)
        require('L' in edges and edges['L']['sequence'] < step_sequence
                and issued >= _time(edges['L']['audit']['at_utc']), 'runtime_authority_policy_cutover')
    require(not conn.execute('SELECT 1 FROM recognition_runtime_execution_claims WHERE operation_id=?', (ref['operation_id'],)).fetchone(),
            'runtime_authority_preactivation_claim')


def check_rows(conn):
    from . import administration as a
    check_manifest_transition(conn)
    a._audit_head(conn)
    for row in conn.execute(f'SELECT * FROM {AUTHORITIES}'):
        body = parse_authority(row['body_json'], authority_sha256=row['body_sha256'])
        scope, ref = body['runtime_target'], body['operation_reference']
        indexed = dict(authority_id=body['authority_id'], operation_id=ref['operation_id'], operation_sha256=ref['operation_sha256'],
            writer_manifest_sha256=ref['writer_manifest_sha256'], installation_id=scope['installation_id'], target_id=scope['target_id'],
            generation=scope['generation'], profile_sha256=scope['runtime_profile_sha256'], owner_id=scope['owner_id'], auth_epoch=scope['auth_epoch'],
            mfa_epoch=scope['mfa_epoch'], activation_sequence=body['activation']['sequence'], activation_sha256=body['activation']['event_sha256'],
            approval_id=body['approval']['approval_id'], approval_sha256=body['approval']['approval_sha256'],
            confirmation_sha256=body['producer_ceremony']['confirmation_token_sha256'], issued_at=_time(body['issued_at_utc']), expires_at=_time(body['expires_at_utc']))
        require(all(row[key] == value for key,value in indexed.items()), 'runtime_authority_columns')
        _historical_scope(conn, body)
        history = conn.execute(f'SELECT * FROM {LIFECYCLE} WHERE authority_id=?', (row['authority_id'],)).fetchall()
        require(len(history) == 1, 'runtime_authority_genesis_missing')
        event = parse_genesis(history[0]['body_json'], event_sha256=history[0]['body_sha256'], authority=body)
        stored = history[0]
        require(stored['sequence'] == 1 and stored['state'] == 'AUTHORIZED' and stored['kind'] == 'AUTHORIZE'
                and stored['at'] == row['issued_at'] and stored['audit_sequence'] == row['audit_sequence']
                and all(stored[k] is None for k in ('previous_sha256','entry_sha256','seal_sha256','receipt_sha256')), 'runtime_authority_event_columns')
        audit_row = conn.execute('SELECT * FROM recognition_admin_audit WHERE sequence=?', (row['audit_sequence'],)).fetchone()
        require(audit_row is not None, 'runtime_authority_audit_missing')
        audit = _record(audit_row)
        require(audit['action'] == ISSUE_ACTION and audit['actor'] == scope['owner_id'] and audit['at_utc'] == event['at_utc']
                and type(audit['subject'].get('event_sequence')) is int
                and audit['subject'] == dict(authority_id=row['authority_id'], authority_sha256=row['body_sha256'],
                                            event_sequence=1, event_sha256=stored['body_sha256']), 'runtime_authority_audit_scope')
    require(not conn.execute('PRAGMA foreign_key_check').fetchone(), 'runtime_authority_foreign_key_mismatch')


def migrate(config, *, expected_generation, operator, reason):
    """Explicit local inert migration. Target reserved/query-only through commit."""
    from . import administration as a, administration_schema as base, runtime_execution_claim_schema as claims
    from . import runtime_challenges as challenges, runtime_validation as runtime, local_readiness
    require(type(config) is a.LocalAdministration, 'local_administration_required')
    config.paths(); operation._positive(expected_generation)
    runtime.enrollment._text(operator, 200); _reason(reason)
    with a.connect(config.control, write=True) as control:
        control.execute('BEGIN IMMEDIATE')
        base.check_control(control)
        require(all(control.execute('SELECT 1 FROM sqlite_master WHERE name=?', (name,)).fetchone()
                    for name in (claims.CLAIMS, 'recognition_approvals', 'recognition_local_activation')),
                'runtime_authority_migration_prerequisites')
        binding = challenges._deployment_binding(control)
        require(binding['generation'] == expected_generation, 'runtime_authority_migration_generation_conflict')
        require(asdict(a.target_identity(control)) == binding['control_identity'], 'control_identity_mismatch')
        require(binding['production_state'] == 'NOT_ACTIVATED'
                and local_readiness._state(control,binding)['state'] == 'NOT_ACTIVATED', 'runtime_authority_migration_requires_not_activated')
        if binding['runtime_profile_sha256'] is not None:
            runtime._history(control)
        with a.connect(config.target, write=True) as target:
            target.execute('BEGIN IMMEDIATE'); target.execute('PRAGMA query_only=ON')
            a._verify(config,control,target,binding)
            for path in (config.control,config.target):
                with a.connect(path) as preflight:
                    require([r[0] for r in preflight.execute('PRAGMA integrity_check')] == ['ok']
                            and not preflight.execute('PRAGMA foreign_key_check').fetchone(), 'runtime_authority_migration_integrity')
            if _present(control):
                check_rows(control)
                control.rollback()
                return dict(migration_id=MIGRATION, installed=False, generation=expected_generation)
            previous = claims.manifest(control)
            now = runtime._utc_now(); head = a._audit_head(control)
            require(head is None or _time(now) >= _time(load(head['body_json'])['at_utc']), 'administrative_clock_rollback')
            changes = target.total_changes
            control.execute('SAVEPOINT install_runtime_activation_authority')
            try:
                for sql in definitions().values():
                    control.execute(sql)
                a._audit(control,ACTION,operator,now,dict(migration_id=MIGRATION,
                    previous_schema_sha256=previous, installed_schema_sha256=claims.manifest(control),
                    installation_id=binding['installation_id'],generation=expected_generation,reason=reason))
                base.check_control(control)
                require(control.execute(f'SELECT count(*) FROM {AUTHORITIES}').fetchone()[0] == 0
                        and control.execute(f'SELECT count(*) FROM {LIFECYCLE}').fetchone()[0] == 0,
                        'runtime_authority_migration_created_authority')
                require(challenges._deployment_binding(control) == binding
                        and asdict(a.target_identity(control)) == binding['control_identity'], 'runtime_authority_migration_scope_changed')
                a._verify(config,control,target,binding)
                require(target.total_changes == changes and target.execute('PRAGMA query_only').fetchone()[0] == 1,
                        'runtime_authority_migration_target_changed')
                require(_time(runtime._utc_now()) >= _time(now), 'administrative_clock_rollback')
                control.execute('RELEASE install_runtime_activation_authority')
                control.commit()  # Target reservation remains held; never target commit.
                require(not control.in_transaction and target.in_transaction, 'runtime_authority_migration_commit_unconfirmed')
                # integrity_check may initialize TEMP. Use a separate read-only
                # committed snapshot, never relax the manager's main-only rule.
                # Any failure here reports failure after a possible durable
                # install: inspect state, never automatically retry or remove DDL.
                with a.connect(config.control) as verification:
                    verification.execute('BEGIN')
                    require([r[0] for r in verification.execute('PRAGMA integrity_check')] == ['ok']
                            and not verification.execute('PRAGMA foreign_key_check').fetchone(),
                            'runtime_authority_migration_integrity')
            except BaseException:
                if control.in_transaction:
                    control.rollback()
                raise
    return dict(migration_id=MIGRATION, installed=True, generation=expected_generation)
