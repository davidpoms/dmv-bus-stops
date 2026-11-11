"""Inert transition DATA/storage. No plan producer, target DDL or enrollment API."""

from dataclasses import asdict
from pathlib import Path
import sqlite3

from . import administration as a, runtime_profile_schema as p
from . import runtime_activation_authority_schema as authority
from . import runtime_execution_claim_schema as claims, runtime_operation_contract as operation
from .rules import canonical, digest
from .trust import fields, identity, load, require


MIGRATION = 'recognition-runtime-enrollment-transition-storage-v1'
ACTION = 'runtime_schema_transition_storage_installed'
PLANS = 'recognition_runtime_schema_transition_plans'
HISTORY = 'recognition_runtime_schema_transition_history'
FORMAT = 'recognition-runtime-target-schema-transition-v1'
EVENT_FORMAT = 'recognition-runtime-schema-transition-event-v1'
PACKAGE = 'recognition-runtime-target-entry-storage-v1'
STATES = ('PREPARED', 'MIGRATION_INTENT', 'SCHEMA_BOUND', 'FINALIZED')
ACTIONS = ('runtime_target_schema_transition_prepared', 'runtime_target_schema_transition_intent_recorded',
           'runtime_target_schema_transition_completed', 'runtime_target_schema_transition_finalized')
BODY_FIELDS = '''format plan_id installation_id target_id owner_id source_generation source_binding_sha256
source_profile_sha256 source_auth_epoch source_mfa_epoch target_schema control_schema_sha256 migration_id
activation_head created_at_utc deadline_at_utc operator reason'''.split()
EVENT_FIELDS = '''format plan_id plan_sha256 sequence state at_utc previous_sha256 actor_id operator reason evidence'''.split()
EVIDENCE = (('source_binding_sha256', 'source_profile_sha256'), ('prepared_event_sha256',),
            ('intent_event_sha256', 'observed_schema_sha256', 'generation', 'binding_sha256'),
            ('schema_bound_event_sha256', 'generation', 'binding_sha256', 'profile_sha256',
             'challenge_sha256', 'observation_sha256', 'review_sha256'))


def validate_plan(value):
    operation._json(value); fields(value, BODY_FIELDS)
    require(len(canonical(value).encode('utf-8')) <= authority.MAX_BYTES, 'transition_size_limit')
    from .runtime_finalization_schema_upgrade import PACKAGE as journal_package
    require(value['format'] == FORMAT and value['migration_id'] in (PACKAGE,journal_package), 'transition_format')
    for key in ('plan_id', 'installation_id', 'target_id'): identity(value[key])
    for key in ('source_binding_sha256', 'source_profile_sha256', 'control_schema_sha256'): p._check_sha(value[key])
    from .runtime_enrollment import _integer, _text
    _integer(value['source_generation'], 1, 2**63-3)
    for key in ('owner_id', 'source_auth_epoch', 'source_mfa_epoch'): _integer(value[key], 1, 2**63-1)
    schema = value['target_schema']
    fields(schema, ('before_sha256', 'after_sha256', 'added_definitions_sha256'))
    for sha in schema.values(): p._check_sha(sha)
    require(schema['before_sha256'] != schema['after_sha256'], 'transition_schema_unchanged')
    head = value['activation_head']; fields(head, ('sequence', 'event_sha256', 'state'))
    _integer(head['sequence'], 1, 2**63-1); p._check_sha(head['event_sha256'])
    require(head['state'] in ('NOT_ACTIVATED', 'DEACTIVATED'), 'transition_requires_nonactive')
    require(authority._time(value['created_at_utc']) < authority._time(value['deadline_at_utc']), 'transition_deadline')
    _text(value['operator'], 200); _text(value['reason'], 2000)
    return operation._copy(value)


def _parse(serialized, sha, validator):
    require(type(serialized) is str and len(serialized.encode('utf-8')) <= authority.MAX_BYTES, 'transition_size_limit')
    p._check_sha(sha); body = validator(load(serialized))
    require(canonical(body) == serialized and digest(body) == sha, 'transition_integrity')
    return body


def parse_plan(serialized, *, plan_sha256):
    return _parse(serialized, plan_sha256, validate_plan)


def plan_digest(value):
    return digest(validate_plan(value))


def validate_expiry(plan, *, now):
    plan = validate_plan(plan)
    require(authority._time(plan['created_at_utc']) <= authority._time(now) < authority._time(plan['deadline_at_utc']),
            'transition_expired_or_clock_rollback')


def validate_event(value):
    operation._json(value); fields(value, EVENT_FIELDS)
    require(len(canonical(value).encode('utf-8')) <= authority.MAX_BYTES and value['format'] == EVENT_FORMAT,
            'transition_event_format')
    identity(value['plan_id']); p._check_sha(value['plan_sha256'])
    require(type(value['sequence']) is int and 1 <= value['sequence'] <= 4
            and value['state'] == STATES[value['sequence']-1], 'transition_event_edge')
    if value['sequence'] == 1: require(value['previous_sha256'] is None, 'transition_event_predecessor')
    else: p._check_sha(value['previous_sha256'])
    operation._positive(value['actor_id']); authority._time(value['at_utc'])
    from .runtime_enrollment import _text
    _text(value['operator'], 200); _text(value['reason'], 2000)
    evidence = value['evidence']; fields(evidence, EVIDENCE[value['sequence']-1])
    for key, item in evidence.items():
        if key == 'generation': operation._positive(item)
        else: p._check_sha(item)
    return operation._copy(value)


def parse_event(serialized, *, event_sha256):
    return _parse(serialized, event_sha256, validate_event)


def definitions():
    c = p.column
    json_check = ("typeof(body_json)='text' AND instr(body_json,char(0))=0 AND "
        f"length(CAST(body_json AS BLOB))<={authority.MAX_BYTES} AND json_valid(body_json) AND json_type(body_json)='object'")
    plans = [c('plan_id','TEXT',p.uuid('plan_id')),c('installation_id','TEXT',p.uuid('installation_id')),
        c('source_generation','INTEGER',p.integer('source_generation',1,2**63-3)),
        c('source_binding_sha256','TEXT',p.sha('source_binding_sha256')),
        c('source_profile_sha256','TEXT',p.sha('source_profile_sha256')),
        c('created_at','INTEGER',p.integer('created_at')),c('deadline_at','INTEGER',p.integer('deadline_at')),
        c('body_json','TEXT',json_check),c('body_sha256','TEXT',p.sha('body_sha256')),
        c('audit_sequence','INTEGER',p.integer('audit_sequence',1,2**63-1)),
        'PRIMARY KEY(plan_id)','UNIQUE(installation_id,source_generation)','UNIQUE(source_binding_sha256)',
        'UNIQUE(body_sha256)','UNIQUE(audit_sequence)','CHECK(created_at<deadline_at)',
        'FOREIGN KEY(source_generation) REFERENCES recognition_admin_bindings(generation)',
        'FOREIGN KEY(source_binding_sha256) REFERENCES recognition_admin_bindings(body_sha256)',
        f'FOREIGN KEY(source_profile_sha256) REFERENCES {p.PROFILES}(profile_sha256)',
        'FOREIGN KEY(audit_sequence) REFERENCES recognition_admin_audit(sequence) DEFERRABLE INITIALLY DEFERRED']
    history = [c('plan_id','TEXT',p.uuid('plan_id')),c('sequence','INTEGER',p.integer('sequence',1,4)),
        c('state','TEXT',"state IN ('PREPARED','MIGRATION_INTENT','SCHEMA_BOUND','FINALIZED')"),
        c('at','INTEGER',p.integer('at')),f'previous_sha256 TEXT CHECK(previous_sha256 IS NULL OR ({p.sha("previous_sha256")}))',
        c('body_json','TEXT',json_check),c('body_sha256','TEXT',p.sha('body_sha256')),
        c('audit_sequence','INTEGER',p.integer('audit_sequence',1,2**63-1)),
        f'destination_generation INTEGER CHECK(destination_generation IS NULL OR ({p.integer("destination_generation",1,2**63-1)}))',
        f'destination_binding_sha256 TEXT CHECK(destination_binding_sha256 IS NULL OR ({p.sha("destination_binding_sha256")}))',
        f'destination_profile_sha256 TEXT CHECK(destination_profile_sha256 IS NULL OR ({p.sha("destination_profile_sha256")}))',
        'PRIMARY KEY(plan_id,sequence)','UNIQUE(plan_id,state)','UNIQUE(body_sha256)','UNIQUE(audit_sequence)',
        f'FOREIGN KEY(plan_id) REFERENCES {PLANS}(plan_id)',
        'FOREIGN KEY(audit_sequence) REFERENCES recognition_admin_audit(sequence) DEFERRABLE INITIALLY DEFERRED',
        'FOREIGN KEY(destination_generation) REFERENCES recognition_admin_bindings(generation) DEFERRABLE INITIALLY DEFERRED',
        'FOREIGN KEY(destination_binding_sha256) REFERENCES recognition_admin_bindings(body_sha256) DEFERRABLE INITIALLY DEFERRED',
        f'FOREIGN KEY(destination_profile_sha256) REFERENCES {p.PROFILES}(profile_sha256) DEFERRABLE INITIALLY DEFERRED']
    # SQLite requires a UNIQUE parent key for the approved digest foreign keys.
    result = {'recognition_transition_binding_digest':
        'CREATE UNIQUE INDEX recognition_transition_binding_digest ON recognition_admin_bindings(body_sha256)',
        PLANS:f"CREATE TABLE {PLANS} ({', '.join(plans)})", HISTORY:f"CREATE TABLE {HISTORY} ({', '.join(history)})"}
    keys = {PLANS:(('plan_id',),('installation_id','source_generation'),('source_binding_sha256',),('body_sha256',),('audit_sequence',)),
            HISTORY:(('plan_id','sequence'),('plan_id','state'),('body_sha256',),('audit_sequence',))}
    for table, groups in keys.items():
        for verb in ('UPDATE','DELETE'):
            name = table+'_immutable_'+verb.lower()
            result[name] = f"CREATE TRIGGER {name} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_transition'); END"
        collision = ' OR '.join('('+' AND '.join(f'{k}=NEW.{k}' for k in group)+')' for group in groups)
        name = table+'_immutable_replace'
        result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN EXISTS(SELECT 1 FROM {table} WHERE {collision}) BEGIN SELECT RAISE(ABORT,'immutable_transition'); END"
    def guard(name, table, condition):
        result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN NOT COALESCE(({condition}),0) BEGIN SELECT RAISE(ABORT,'transition_scope_mismatch'); END"
    j = lambda key: f"json_extract(NEW.body_json,'$.{key}')"
    pending = f'EXISTS(SELECT 1 FROM {PLANS} q WHERE NOT EXISTS(SELECT 1 FROM {HISTORY} h WHERE h.plan_id=q.plan_id AND h.sequence=4))'
    guard(PLANS+'_source_guard', PLANS,
        f"{j('format')}='{FORMAT}' AND {j('migration_id')}='{PACKAGE}' AND (SELECT count(*) FROM json_each(NEW.body_json))={len(BODY_FIELDS)} "
        f"AND {j('plan_id')}=NEW.plan_id AND {j('installation_id')}=NEW.installation_id AND {j('source_generation')}=NEW.source_generation "
        f"AND {j('source_binding_sha256')}=NEW.source_binding_sha256 AND {j('source_profile_sha256')}=NEW.source_profile_sha256 "
        f"AND {j('created_at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.created_at,'unixepoch') "
        f"AND {j('deadline_at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.deadline_at,'unixepoch') "
        f"AND {j('target_schema.before_sha256')}<>{j('target_schema.after_sha256')} AND NOT ({pending}) "
        f"AND {p.sha(j('target_schema.after_sha256'))} AND {p.sha(j('target_schema.added_definitions_sha256'))} "
        f"AND {p.sha(j('control_schema_sha256'))} AND json_type(NEW.body_json,'$.source_generation')='integer' "
        f"AND json_type(NEW.body_json,'$.owner_id')='integer' AND {p.integer(j('source_auth_epoch'),1,2**63-1)} "
        f"AND json_type(NEW.body_json,'$.source_mfa_epoch')='integer' "
        'AND NOT EXISTS(SELECT 1 FROM recognition_runtime_execution_attempts) '
        'AND NOT EXISTS(SELECT 1 FROM recognition_admin_audit WHERE sequence=NEW.audit_sequence) '
        f'AND EXISTS(SELECT 1 FROM recognition_admin_bindings b JOIN {p.PROFILES} r ON r.profile_sha256=NEW.source_profile_sha256 '
        'JOIN recognition_admin_mfa m ON m.actor=r.owner_id WHERE b.generation=NEW.source_generation '
        'AND b.generation=(SELECT max(generation) FROM recognition_admin_bindings) AND b.body_sha256=NEW.source_binding_sha256 '
        "AND json_extract(b.body_json,'$.runtime_profile_sha256')=r.profile_sha256 AND r.generation=b.generation "
        f"AND r.installation_id=NEW.installation_id AND r.owner_id={j('owner_id')} AND r.target_id={j('target_id')} "
        f"AND r.target_schema_sha256={j('target_schema.before_sha256')} AND m.state='ENROLLED' AND m.epoch={j('source_mfa_epoch')}) "
        f"AND EXISTS(SELECT 1 FROM recognition_local_activation x WHERE x.sequence={j('activation_head.sequence')} "
        f"AND x.sequence=(SELECT max(sequence) FROM recognition_local_activation) AND x.body_sha256={j('activation_head.event_sha256')} "
        f"AND json_extract(x.body_json,'$.state')={j('activation_head.state')} AND {j('activation_head.state')} IN ('NOT_ACTIVATED','DEACTIVATED'))")
    # Exact linked event graph; destination FKs deliberately allow event-before-binding/profile.
    guard(HISTORY+'_edge_guard', HISTORY,
        f"{j('format')}='{EVENT_FORMAT}' AND (SELECT count(*) FROM json_each(NEW.body_json))={len(EVENT_FIELDS)} "
        f"AND {j('plan_id')}=NEW.plan_id AND json_type(NEW.body_json,'$.sequence')='integer' "
        f"AND {j('sequence')}=NEW.sequence AND {j('state')}=NEW.state "
        f"AND {j('previous_sha256')} IS NEW.previous_sha256 AND {j('at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.at,'unixepoch') "
        f'AND EXISTS(SELECT 1 FROM {PLANS} q WHERE q.plan_id=NEW.plan_id AND q.body_sha256={j("plan_sha256")} '
        f"AND json_extract(q.body_json,'$.owner_id')={j('actor_id')} AND NEW.at>=q.created_at AND NEW.at<q.deadline_at "
        'AND ((NEW.sequence=1 AND NEW.state=\'PREPARED\' AND NEW.previous_sha256 IS NULL AND NEW.audit_sequence=q.audit_sequence '
        f"AND {j('operator')}=json_extract(q.body_json,'$.operator') AND {j('reason')}=json_extract(q.body_json,'$.reason')) "
        f'OR EXISTS(SELECT 1 FROM {HISTORY} old WHERE old.plan_id=NEW.plan_id AND old.sequence=NEW.sequence-1 '
        "AND old.body_sha256=NEW.previous_sha256 AND NEW.at>=old.at AND NEW.audit_sequence>old.audit_sequence "
        "AND ((NEW.sequence=2 AND NEW.state='MIGRATION_INTENT') OR (NEW.sequence=3 AND NEW.state='SCHEMA_BOUND') "
        "OR (NEW.sequence=4 AND NEW.state='FINALIZED'))))) "
        'AND NOT EXISTS(SELECT 1 FROM recognition_admin_audit WHERE sequence=NEW.audit_sequence) '
        'AND ((NEW.sequence<=2 AND NEW.destination_generation IS NULL AND NEW.destination_binding_sha256 IS NULL AND NEW.destination_profile_sha256 IS NULL) '
        f'OR (NEW.sequence>=3 AND NEW.destination_generation=(SELECT source_generation+NEW.sequence-2 FROM {PLANS} WHERE plan_id=NEW.plan_id) '
        f"AND NEW.destination_generation={j('evidence.generation')} AND NEW.destination_binding_sha256={j('evidence.binding_sha256')} "
        f"AND ((NEW.sequence=3 AND NEW.destination_profile_sha256 IS NULL) OR (NEW.sequence=4 AND NEW.destination_profile_sha256={j('evidence.profile_sha256')}))))")
    guard(HISTORY+'_evidence_guard', HISTORY,
        f'EXISTS(SELECT 1 FROM {PLANS} q WHERE q.plan_id=NEW.plan_id AND ('
        f"(NEW.sequence=1 AND (SELECT count(*) FROM json_each(NEW.body_json,'$.evidence'))=2 "
        f"AND {j('evidence.source_binding_sha256')}=q.source_binding_sha256 AND {j('evidence.source_profile_sha256')}=q.source_profile_sha256) OR "
        f"(NEW.sequence=2 AND (SELECT count(*) FROM json_each(NEW.body_json,'$.evidence'))=1 AND {j('evidence.prepared_event_sha256')}=NEW.previous_sha256) OR "
        f"(NEW.sequence=3 AND (SELECT count(*) FROM json_each(NEW.body_json,'$.evidence'))=4 AND {j('evidence.intent_event_sha256')}=NEW.previous_sha256 "
        f"AND {j('evidence.observed_schema_sha256')}=json_extract(q.body_json,'$.target_schema.after_sha256')) OR "
        f"(NEW.sequence=4 AND (SELECT count(*) FROM json_each(NEW.body_json,'$.evidence'))=7 AND {j('evidence.schema_bound_event_sha256')}=NEW.previous_sha256)))")
    # A binding/profile cannot commit an unlinked transition or bypass atomic finalization.
    guard('recognition_transition_binding_guard', 'recognition_admin_bindings',
        f'(NOT ({pending}) AND NOT EXISTS(SELECT 1 FROM recognition_admin_bindings old '
        "WHERE old.generation=(SELECT max(generation) FROM recognition_admin_bindings) "
        "AND json_type(old.body_json,'$.runtime_profile_sha256')='text' "
        "AND json_type(NEW.body_json,'$.runtime_profile_sha256')='null')) "
        f'OR EXISTS(SELECT 1 FROM {HISTORY} h WHERE h.sequence IN (3,4) '
        'AND h.destination_generation=NEW.generation AND h.destination_binding_sha256=NEW.body_sha256)')
    physical = ('hostname','target_path','target_device','target_inode','control_path','control_device','control_inode')
    same_physical = ' AND '.join(f'NEW.{key}=old.{key}' for key in physical)
    guard('recognition_transition_profile_guard', p.PROFILES,
        f'NOT EXISTS(SELECT 1 FROM {PLANS} WHERE NEW.generation=source_generation+2) OR EXISTS(SELECT 1 FROM {PLANS} q JOIN {HISTORY} h ON h.plan_id=q.plan_id AND h.sequence=4 '
        f'JOIN {p.PROFILES} old ON old.profile_sha256=q.source_profile_sha256 '
        f'WHERE h.destination_profile_sha256=NEW.profile_sha256 AND NEW.generation=q.source_generation+2 AND {same_physical} '
        "AND NEW.target_schema_sha256=json_extract(q.body_json,'$.target_schema.after_sha256') "
        'AND NEW.installation_id=q.installation_id AND NEW.target_id=old.target_id AND NEW.owner_id=old.owner_id)')
    # No current token scope may be minted while an unfinished plan exists.
    guard('recognition_transition_auth_guard', p.AUTH, f'NOT ({pending})')
    # Every event audit proves graph completeness, exact predecessor/evidence and denials.
    name = 'recognition_transition_audit_guard'
    action_case = "CASE h.sequence "+' '.join(f"WHEN {i+1} THEN '{v}'" for i,v in enumerate(ACTIONS))+" END"
    result[name] = (f'CREATE TRIGGER {name} BEFORE INSERT ON recognition_admin_audit WHEN EXISTS('
        f'SELECT 1 FROM {HISTORY} WHERE audit_sequence=NEW.sequence) OR EXISTS(SELECT 1 FROM {PLANS} WHERE audit_sequence=NEW.sequence) '
        'BEGIN SELECT CASE WHEN NOT EXISTS('
        f'SELECT 1 FROM {HISTORY} h JOIN {PLANS} q ON q.plan_id=h.plan_id WHERE h.audit_sequence=NEW.sequence '
        f"AND json_extract(NEW.body_json,'$.action')=({action_case}) "
        "AND json_extract(NEW.body_json,'$.actor')=json_extract(h.body_json,'$.operator') "
        "AND json_extract(NEW.body_json,'$.at_utc')=json_extract(h.body_json,'$.at_utc') "
        "AND json_extract(NEW.body_json,'$.subject.plan_id')=q.plan_id AND json_extract(NEW.body_json,'$.subject.plan_sha256')=q.body_sha256 "
        "AND json_extract(NEW.body_json,'$.subject.event_sequence')=h.sequence AND json_extract(NEW.body_json,'$.subject.event_sha256')=h.body_sha256 "
        "AND EXISTS(SELECT 1 FROM recognition_admin_mfa m WHERE m.actor=json_extract(q.body_json,'$.owner_id') "
        "AND m.state='ENROLLED' AND m.epoch=json_extract(q.body_json,'$.source_mfa_epoch')) "
        "AND EXISTS(SELECT 1 FROM recognition_local_activation x WHERE x.sequence=(SELECT max(sequence) FROM recognition_local_activation) "
        "AND x.sequence=json_extract(q.body_json,'$.activation_head.sequence') AND x.body_sha256=json_extract(q.body_json,'$.activation_head.event_sha256')) "
        'AND NOT EXISTS(SELECT 1 FROM recognition_admin_primary WHERE revoked=0) '
        'AND NOT EXISTS(SELECT 1 FROM recognition_admin_sessions WHERE revoked=0) '
        'AND NOT EXISTS(SELECT 1 FROM recognition_admin_stepups) '
        'AND NOT EXISTS(SELECT 1 FROM recognition_admin_confirmations WHERE used=0) '
        'AND NOT EXISTS(SELECT 1 FROM recognition_approval_history ap WHERE ap.state=\'APPROVED\' '
        'AND ap.sequence=(SELECT max(newer.sequence) FROM recognition_approval_history newer WHERE newer.approval_id=ap.approval_id)) '
        f'AND (h.sequence<3 OR EXISTS(SELECT 1 FROM recognition_admin_bindings b WHERE b.generation=h.destination_generation '
        'AND b.body_sha256=h.destination_binding_sha256)) '
        f'AND (h.sequence<>4 OR EXISTS(SELECT 1 FROM {p.PROFILES} r JOIN recognition_admin_audit en ON en.sequence=r.audit_sequence '
        'WHERE r.profile_sha256=h.destination_profile_sha256 AND r.generation=h.destination_generation '
        "AND json_extract(en.body_json,'$.action')='runtime_profile_enrolled' "
        "AND json_type(en.body_json,'$.subject.private_log_review_confirmed')='true' "
        "AND json_type(en.body_json,'$.subject.enrollment_confirmed')='true' "
        "AND json_extract(en.body_json,'$.subject.profile_sha256')=r.profile_sha256))) "
        "THEN RAISE(ABORT,'transition_audit_incomplete') END; END")
    # The new UNIQUE parent index must not introduce an OR REPLACE deletion key.
    result['recognition_transition_binding_digest_replace'] = (
        'CREATE TRIGGER recognition_transition_binding_digest_replace BEFORE INSERT ON recognition_admin_bindings '
        'WHEN EXISTS(SELECT 1 FROM recognition_admin_bindings WHERE body_sha256=NEW.body_sha256) '
        "BEGIN SELECT RAISE(ABORT,'immutable_transition_binding_digest'); END")
    return result


def present(conn):
    from .administration_schema import _control_names
    names = _control_names(conn)
    return any(n.startswith(('recognition_runtime_schema_transition', 'recognition_transition_')) for n in names) or ('recognition_admin_audit' in names and bool(authority._rows(conn, ACTION)))


def historical_manifest(conn, *, exclude=()):
    """Reconstruct S2 only after independently validating the exact S3 extension."""
    from . import runtime_schema_package_lineage as lineage
    if lineage.present(conn):
        edges = lineage.verify(conn)
        edge = 'E' if 'E' in edges else 'T' if 'T' in edges else 'A'
        objects = edges[edge]['before' if edge == 'E' else 'after']
        allowed = set(authority.definitions()) | set(claims.definitions())
        from . import runtime_execution_attempt_schema as attempts
        allowed.update(attempts.definitions()); allowed.update(definitions())
        omitted = set(exclude)
        require(omitted <= allowed, 'lineage_unknown_projection')
        return digest({k:v for k,v in objects.items() if k not in omitted})
    if not present(conn): return claims.manifest(conn, exclude=exclude)
    from .administration_schema import _control_objects
    expected = definitions(); actual = dict(_control_objects(conn))
    # These projections describe the very same sqlite_master observation already
    # required below. No writes, external callbacks or transaction/mode changes
    # occur in this reader. Keep it local: every invocation reads again, including
    # final validation and calls after a mutation. This is not a history cache.
    # Unreserved readers and unknown connection adapters retain the original
    # separate reads (including each adapter's ownership checks).
    reserved = type(conn) is sqlite3.Connection and conn.in_transaction
    normalized = tuple((name, ' '.join(sql.split())) for name, sql in actual.items()) if reserved else ()
    def projected(omitted=()):
        if not reserved:
            return claims.manifest(conn, exclude=omitted)
        return digest({name: sql for name, sql in normalized if name not in omitted})
    require(all(n in actual and ' '.join(actual[n].split()) == ' '.join(sql.split()) for n,sql in expected.items()), 'transition_partial_schema')
    rows = authority._rows(conn, ACTION); require(len(rows) == 1, 'transition_migration_audit')
    audit = authority._record(rows[0]); subject = audit['subject']
    fields(subject, ('migration_id','previous_schema_sha256','installed_schema_sha256','installation_id','generation','reason'))
    from . import runtime_execution_attempt_schema as attempts
    prior = authority._rows(conn, attempts.ACTION)
    require(len(prior) == 1 and prior[0]['sequence'] < rows[0]['sequence'] and subject['migration_id'] == MIGRATION
            and subject['installed_schema_sha256'] == projected()
            and subject['previous_schema_sha256'] == projected(expected)
            and authority._record(prior[0])['subject']['installed_schema_sha256'] == subject['previous_schema_sha256'], 'transition_migration_manifest')
    identity(subject['installation_id']); operation._positive(subject['generation']); authority._reason(subject['reason']); authority._reason(audit['actor'])
    binding = conn.execute('SELECT body_json FROM recognition_admin_bindings WHERE generation=?',(subject['generation'],)).fetchone()
    require(binding and load(binding[0])['installation_id'] == subject['installation_id'], 'transition_migration_scope')
    return projected(set(exclude)|set(expected))


def _binding(conn, generation):
    row = conn.execute('SELECT * FROM recognition_admin_bindings WHERE generation=?',(generation,)).fetchone()
    require(row is not None, 'transition_binding_missing')
    body = load(row['body_json']); require(digest(body) == row['body_sha256'] and canonical(body) == row['body_json'], 'transition_binding_integrity')
    return body


def _source(conn, plan):
    source = _binding(conn, plan['source_generation'])
    require(digest(source) == plan['source_binding_sha256'] and source['runtime_profile_sha256'] == plan['source_profile_sha256']
            and source['production_state'] == 'NOT_ACTIVATED'
            and all(source[k] == plan[k] for k in ('installation_id','target_id','owner_id'))
            and source['target']['schema_sha256'] == plan['target_schema']['before_sha256'], 'transition_source_mismatch')
    row = conn.execute(f'SELECT * FROM {p.PROFILES} WHERE profile_sha256=?',(plan['source_profile_sha256'],)).fetchone()
    require(row is not None and row['generation'] == plan['source_generation'], 'transition_source_profile')
    head = conn.execute('SELECT body_json,body_sha256 FROM recognition_local_activation WHERE sequence=?',(plan['activation_head']['sequence'],)).fetchone()
    require(head and head['body_sha256'] == plan['activation_head']['event_sha256'] and digest(load(head['body_json'])) == head['body_sha256']
            and load(head['body_json'])['state'] == plan['activation_head']['state'], 'transition_activation_mismatch')
    return source, dict(row)


def check_rows(conn):
    from . import runtime_finalization_schema_upgrade as journal_upgrade
    edges=None
    from . import runtime_schema_package_lineage as lineage
    if type(conn) is sqlite3.Connection and conn.in_transaction and (journal_upgrade.present(conn) or lineage.present(conn)):
        edges=lineage.verify(conn)  # One full graph, only within this read operation/snapshot.
    else:
        historical_manifest(conn)
    for row in conn.execute(f'SELECT * FROM {PLANS}'):
        plan = parse_plan(row['body_json'], plan_sha256=row['body_sha256']); source, old_profile = _source(conn, plan)
        for key in ('plan_id','installation_id','source_generation','source_binding_sha256','source_profile_sha256'):
            require(row[key] == plan[key], 'transition_plan_columns')
        require(row['created_at'] == authority._time(plan['created_at_utc']) and row['deadline_at'] == authority._time(plan['deadline_at_utc']), 'transition_plan_columns')
        from .runtime_finalization_schema_upgrade import plan_manifest
        require(plan['control_schema_sha256'] == plan_manifest(conn,plan,row['audit_sequence'],_edges=edges), 'transition_control_schema_changed')
        previous, last_time = None, row['created_at']
        history = conn.execute(f'SELECT * FROM {HISTORY} WHERE plan_id=? ORDER BY sequence',(row['plan_id'],)).fetchall()
        require(history, 'transition_preparation_missing')
        for sequence, h in enumerate(history, 1):
            event = parse_event(h['body_json'], event_sha256=h['body_sha256']); evidence = event['evidence']
            require(event['sequence'] == h['sequence'] == sequence and event['state'] == h['state']
                    and event['plan_id'] == row['plan_id'] and event['plan_sha256'] == row['body_sha256']
                    and event['previous_sha256'] == h['previous_sha256'] == previous and event['actor_id'] == plan['owner_id']
                    and h['at'] == authority._time(event['at_utc']) and last_time <= h['at'] < row['deadline_at'], 'transition_history_integrity')
            if sequence == 1:
                require(evidence == {k:plan[k] for k in EVIDENCE[0]} and h['audit_sequence'] == row['audit_sequence']
                        and event['operator'] == plan['operator'] and event['reason'] == plan['reason'], 'transition_prepared_scope')
            else:
                require(evidence[EVIDENCE[sequence-1][0]] == previous, 'transition_evidence_predecessor')
            if sequence <= 2:
                require(all(h[k] is None for k in ('destination_generation','destination_binding_sha256','destination_profile_sha256')), 'transition_destination')
            else:
                generation = plan['source_generation']+sequence-2; binding = _binding(conn, generation)
                expected = operation._copy(source if sequence == 3 else _binding(conn, generation-1))
                expected.update(generation=generation, previous_sha256=digest(source if sequence == 3 else _binding(conn,generation-1)),
                                at_utc=binding['at_utc'],production_state='NOT_ACTIVATED',
                                runtime_profile_sha256=None if sequence == 3 else evidence['profile_sha256'])
                expected['target']['schema_sha256'] = plan['target_schema']['after_sha256']
                require(binding == expected and evidence['generation'] == h['destination_generation'] == generation
                        and digest(binding) == evidence['binding_sha256'] == h['destination_binding_sha256'], 'transition_destination')
                if sequence == 3:
                    require(h['destination_profile_sha256'] is None and evidence['observed_schema_sha256'] == plan['target_schema']['after_sha256']
                            and binding['at_utc'] == event['at_utc'], 'transition_schema_bound')
                else:
                    profile = conn.execute(f'SELECT * FROM {p.PROFILES} WHERE profile_sha256=?',(evidence['profile_sha256'],)).fetchone()
                    require(profile is not None and h['destination_profile_sha256'] == profile['profile_sha256'] and profile['generation'] == generation
                            and all(profile[k] == old_profile[k] for k in ('hostname','target_path','target_device','target_inode','control_path','control_device','control_inode'))
                            and profile['target_schema_sha256'] == plan['target_schema']['after_sha256'], 'transition_profile_continuity')
                    enrollment_audit = conn.execute('SELECT body_json FROM recognition_admin_audit WHERE sequence=?',(profile['audit_sequence'],)).fetchone()
                    require(enrollment_audit is not None, 'transition_enrollment_audit')
                    enrolled = load(enrollment_audit[0]); subject = enrolled['subject']
                    fields(subject, ('reason','previous_generation','generation','source_binding_sha256','binding_sha256',
                        'challenge_sha256','profile_sha256','observation_sha256','review_sha256',
                        'private_log_review_confirmed','enrollment_confirmed','review'))
                    require(enrolled['action'] == 'runtime_profile_enrolled' and all(subject[k] == evidence[k] for k in
                        ('profile_sha256','challenge_sha256','observation_sha256','review_sha256'))
                        and subject['private_log_review_confirmed'] is True and subject['enrollment_confirmed'] is True
                        and type(subject['generation']) is int and subject['generation'] == generation
                        and type(subject['previous_generation']) is int and subject['previous_generation'] == generation-1
                        and subject['source_binding_sha256'] == digest(_binding(conn,generation-1))
                        and subject['binding_sha256'] == digest(binding)
                        and enrolled['actor'] == profile['operator'] == event['operator']
                        and subject['reason'] == profile['reason'] == event['reason']
                        and enrolled['at_utc'] == binding['at_utc']
                        and authority._time(enrolled['at_utc']) == profile['created_at'], 'transition_enrollment_audit')
                    from . import runtime_enrollment as enrollment
                    review = enrollment.parse_review(canonical(subject['review']))
                    require(digest(review) == subject['review_sha256'] and review['selected_observation_sha256'] == profile['observation_sha256'], 'transition_review_integrity')
                    challenge = dict(conn.execute(f'SELECT * FROM {p.CHALLENGES} WHERE challenge_id=?',(profile['challenge_id'],)).fetchone())
                    require(challenge['challenge_sha256'] == evidence['challenge_sha256'], 'transition_challenge_mismatch')
                    enrollment.validate_review_scope(review,challenge,_binding(conn,generation-1),enrolled['at_utc'])
                    selected = next(x['observation'] for x in review['observations'] if x['observation_sha256'] == profile['observation_sha256'])
                    require(all(profile[k] == selected[k] for k in enrollment.PHYSICAL_FIELDS)
                            and profile['observed_at'] == selected['observed_at'] and profile['evidence_channel'] == selected['evidence_channel'], 'transition_observation_mismatch')
            audit_row = conn.execute('SELECT * FROM recognition_admin_audit WHERE sequence=?',(h['audit_sequence'],)).fetchone()
            require(audit_row is not None, 'transition_audit_missing'); audit = authority._record(audit_row)
            require(audit['action'] == ACTIONS[sequence-1] and audit['actor'] == event['operator'] and audit['at_utc'] == event['at_utc']
                    and audit['subject'] == dict(plan_id=plan['plan_id'],plan_sha256=row['body_sha256'],event_sequence=sequence,event_sha256=h['body_sha256']), 'transition_audit_scope')
            previous, last_time = h['body_sha256'], h['at']
    require(not conn.execute('PRAGMA foreign_key_check').fetchone(), 'transition_foreign_key_mismatch')


def require_no_pending(conn):
    """Additional admission fence; structural schema validation still permits DATA."""
    if present(conn):
        from . import runtime_history_validation as history
        if not history.validated(conn):check_rows(conn)
        a.need(not conn.execute(f'SELECT 1 FROM {PLANS} q WHERE NOT EXISTS(SELECT 1 FROM {HISTORY} h WHERE h.plan_id=q.plan_id AND h.sequence=4)').fetchone(), 'runtime_schema_transition_pending', 503)


def inspect_transition(control_path, *, plan_id):
    """Control-only historical inspection; never claims a paired target commit."""
    from .administration_schema import check_control
    from .runtime_execution_admission import _freeze
    identity(plan_id); require(isinstance(control_path,Path) and control_path.is_absolute(), 'transition_control_path_required')
    result = dict(plan_id=plan_id,execution_authority=False,retry_authorized=False,target_commit_verified=False)
    try:
        with a.connect(control_path) as conn:
            conn.execute('BEGIN'); check_control(conn); require(present(conn), 'transition_storage_missing')
            row = conn.execute(f'SELECT * FROM {PLANS} WHERE plan_id=?',(plan_id,)).fetchone()
            if row is None: return _freeze(dict(result,status='NO_PLAN'))
            history = conn.execute(f'SELECT state FROM {HISTORY} WHERE plan_id=? ORDER BY sequence DESC',(plan_id,)).fetchone()
            plan = parse_plan(row['body_json'],plan_sha256=row['body_sha256'])
            state = history[0]
            # No wall-clock argument can upgrade this historical DATA into authority.
            from .runtime_validation import _utc_now
            expired = authority._time(_utc_now()) >= row['deadline_at']
            return _freeze(dict(result,status=state,plan=plan,pending=state!='FINALIZED',expired=expired,
                                inspection_only=True,uncertain_target_outcome=state=='MIGRATION_INTENT'))
    except (ValueError,OSError,sqlite3.Error,KeyError,TypeError):
        return _freeze(dict(result,status='MALFORMED',pending=True))


def migrate(config, *, expected_generation, operator, reason):
    """Install inert control definitions only. No target writes/plan/enrollment."""
    from . import administration_schema as base, runtime_execution_attempt_schema as attempts
    from . import runtime_challenges, runtime_validation as runtime, local_readiness
    require(type(config) is a.LocalAdministration, 'local_administration_required'); config.paths()
    operation._positive(expected_generation); runtime.enrollment._text(operator,200); authority._reason(reason)
    with a.connect(config.control,write=True) as control:
        control.execute('BEGIN IMMEDIATE'); base.check_control(control)
        require(attempts.present(control), 'transition_migration_prerequisites')
        binding = runtime_challenges._deployment_binding(control)
        require(binding['generation'] == expected_generation, 'transition_migration_generation_conflict')
        require(asdict(a.target_identity(control)) == binding['control_identity'], 'control_identity_mismatch')
        require(binding['production_state'] == 'NOT_ACTIVATED' and local_readiness._state(control,binding)['state'] in ('NOT_ACTIVATED','DEACTIVATED'), 'transition_requires_nonactive')
        if binding['runtime_profile_sha256'] is not None: runtime._history(control)
        with a.connect(config.target,write=True) as target:
            target.execute('BEGIN IMMEDIATE'); target.execute('PRAGMA query_only=ON'); a._verify(config,control,target,binding)
            for path in (config.control,config.target):
                with a.connect(path) as check:
                    require([r[0] for r in check.execute('PRAGMA integrity_check')] == ['ok'] and not check.execute('PRAGMA foreign_key_check').fetchone(), 'transition_migration_integrity')
            if present(control):
                check_rows(control); control.rollback(); return dict(installed=False,migration_id=MIGRATION,generation=expected_generation)
            previous = claims.manifest(control); now = runtime._utc_now(); changes = target.total_changes
            control.execute('SAVEPOINT install_runtime_transition')
            try:
                for sql in definitions().values(): control.execute(sql)
                a._audit(control,ACTION,operator,now,dict(migration_id=MIGRATION,previous_schema_sha256=previous,
                    installed_schema_sha256=claims.manifest(control),installation_id=binding['installation_id'],generation=expected_generation,reason=reason))
                base.check_control(control); a._audit_head(control)
                require(not control.execute(f'SELECT 1 FROM {PLANS}').fetchone(), 'transition_migration_created_plan')
                require(runtime_challenges._deployment_binding(control) == binding and asdict(a.target_identity(control)) == binding['control_identity'], 'transition_migration_scope_changed')
                a._verify(config,control,target,binding)
                require(target.total_changes == changes and target.execute('PRAGMA query_only').fetchone()[0] == 1, 'transition_migration_target_changed')
                require(authority._time(runtime._utc_now()) >= authority._time(now), 'administrative_clock_rollback')
                control.execute('RELEASE install_runtime_transition'); control.commit()
                require(not control.in_transaction and target.in_transaction, 'transition_migration_commit_unconfirmed')
                with a.connect(config.control) as verification:
                    verification.execute('BEGIN'); base.check_control(verification)
                    require([r[0] for r in verification.execute('PRAGMA integrity_check')] == ['ok']
                            and not verification.execute('PRAGMA foreign_key_check').fetchone(), 'transition_migration_integrity')
            except BaseException:
                if control.in_transaction: control.rollback()
                raise
    return dict(installed=True,migration_id=MIGRATION,generation=expected_generation)
