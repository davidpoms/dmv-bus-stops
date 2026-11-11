"""Inert target-entry SQL package and historical DATA codecs. No installer/issuer."""

from . import runtime_profile_schema as p, runtime_operation_contract as operation
from . import runtime_activation_authority_schema as authority
from . import runtime_execution_attempt_schema as attempts
from .rules import canonical, digest
from .trust import fields, identity, load, require


PACKAGE = 'recognition-runtime-target-entry-storage-v1'
TABLE = 'recognition_runtime_execution_entries'
FORMAT = 'recognition-runtime-target-entry-v1'
BODY_FIELDS = '''format state attempt_id attempt_sha256 creation_event_sha256 authority_id
authority_sha256 operation_reference runtime_target physical_snapshot activation approval
authentication entered_at_utc expires_at_utc'''.split()
SCOPE_FIELDS = ('operation_reference', 'runtime_target', 'physical_snapshot',
                'activation', 'approval', 'authentication')
COLUMNS = ('attempt_id', 'operation_id', 'authority_sha256', 'writer_manifest_sha256',
           'entered_at', 'body_json', 'body_sha256')


def validate_entry(value, *, authority_body, attempt, creation_event):
    """Validate detached DATA against complete source DATA; never establishes provenance."""
    authority._json(value); fields(value, BODY_FIELDS)
    require(value['format'] == FORMAT and value['state'] == 'TARGET_ENTRY_CREATED', 'target_entry_format')
    for key in ('attempt_id', 'authority_id'):
        identity(value[key])
    for key in ('attempt_sha256', 'creation_event_sha256', 'authority_sha256'):
        p._check_sha(value[key])
    source = authority.validate_authority(authority_body)
    attempt = attempts.validate_attempt(attempt)
    operation._json(creation_event); fields(creation_event, attempts.EVENT_FIELDS)
    require(attempt['authority_id'] == source['authority_id'] == value['authority_id']
            and attempt['authority_sha256'] == digest(source) == value['authority_sha256']
            and attempt['attempt_id'] == value['attempt_id']
            and digest(attempt) == value['attempt_sha256'], 'target_entry_attempt_binding')
    expected_event = dict(format=attempts.EVENT_FORMAT, attempt_id=attempt['attempt_id'],
        attempt_sha256=digest(attempt), sequence=1, state='ATTEMPT_CREATED',
        at_utc=attempt['created_at_utc'], previous_sha256=None,
        actor_id=source['runtime_target']['owner_id'], reason=source['producer_ceremony']['reason'])
    # Canonical comparison also distinguishes booleans from integer fields.
    require(canonical(creation_event) == canonical(expected_event)
            and digest(creation_event) == value['creation_event_sha256'], 'target_entry_creation_binding')
    require(all(canonical(value[k]) == canonical(source[k]) for k in SCOPE_FIELDS), 'target_entry_scope')
    issued, created, entered, expires = map(authority._time, (source['issued_at_utc'],
        attempt['created_at_utc'], value['entered_at_utc'], value['expires_at_utc']))
    require(issued <= created <= entered < expires
            and value['expires_at_utc'] == attempt['expires_at_utc'] == source['expires_at_utc'], 'target_entry_lifetime')
    return operation._copy(value)


def encode_entry(value, **sources):
    return canonical(validate_entry(value, **sources))


def parse_entry(serialized, *, entry_sha256, **sources):
    require(type(serialized) is str and len(serialized.encode('utf-8')) <= authority.MAX_BYTES, 'target_entry_size_limit')
    p._check_sha(entry_sha256)
    value = validate_entry(load(serialized), **sources)
    require(canonical(value) == serialized and digest(value) == entry_sha256, 'target_entry_integrity')
    return value


def definitions():
    """Exact additive name-to-SQL manifest; calling this performs no SQLite operations."""
    c = p.column
    cols = [c('attempt_id', 'TEXT', p.uuid('attempt_id')),
        c('operation_id', 'TEXT', p.uuid('operation_id')),
        c('authority_sha256', 'TEXT', p.sha('authority_sha256')),
        c('writer_manifest_sha256', 'TEXT', p.sha('writer_manifest_sha256')),
        c('entered_at', 'INTEGER', p.integer('entered_at')),
        c('body_json', 'TEXT', "typeof(body_json)='text' AND instr(body_json,char(0))=0 "
          f"AND length(CAST(body_json AS BLOB))<={authority.MAX_BYTES} AND json_valid(body_json) AND json_type(body_json)='object'"),
        c('body_sha256', 'TEXT', p.sha('body_sha256')),
        'PRIMARY KEY(attempt_id)', 'UNIQUE(operation_id)', 'UNIQUE(authority_sha256)',
        'UNIQUE(writer_manifest_sha256)', 'UNIQUE(body_sha256)',
        'FOREIGN KEY(operation_id) REFERENCES recognition_operation_contracts(operation_id)']
    result = {TABLE: f"CREATE TABLE {TABLE} ({', '.join(cols)})"}
    for verb in ('UPDATE', 'DELETE'):
        name = TABLE+'_immutable_'+verb.lower()
        result[name] = f"CREATE TRIGGER {name} BEFORE {verb} ON {TABLE} BEGIN SELECT RAISE(ABORT,'immutable_runtime_target_entry'); END"
    name = TABLE+'_immutable_replace'
    collision = ' OR '.join(f'{k}=NEW.{k}' for k in ('attempt_id', 'operation_id', 'authority_sha256', 'writer_manifest_sha256', 'body_sha256'))
    result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {TABLE} WHEN EXISTS(SELECT 1 FROM {TABLE} WHERE {collision}) BEGIN SELECT RAISE(ABORT,'immutable_runtime_target_entry'); END"
    j = lambda k: f"json_extract(NEW.body_json,'$.{k}')"
    conditions = [f"(SELECT count(*) FROM json_each(NEW.body_json))={len(BODY_FIELDS)}",
        f"{j('format')}='{FORMAT}'", f"{j('state')}='TARGET_ENTRY_CREATED'",
        f"{j('attempt_id')}=NEW.attempt_id", f"{j('operation_reference.operation_id')}=NEW.operation_id",
        f"{j('authority_sha256')}=NEW.authority_sha256",
        f"{j('operation_reference.writer_manifest_sha256')}=NEW.writer_manifest_sha256",
        f"{j('entered_at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.entered_at,'unixepoch')",
        f"typeof({j('expires_at_utc')})='text'",
        f"{j('expires_at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',{j('expires_at_utc')})",
        f"{j('expires_at_utc')}>{j('entered_at_utc')}"]
    for key in BODY_FIELDS:
        conditions.append(f"json_type(NEW.body_json,'$.{key}') IS NOT NULL")
    for key in ('authority_id',):
        conditions.append(p.uuid(j(key)))
    for key in ('attempt_sha256', 'creation_event_sha256'):
        conditions.append(p.sha(j(key)))
    name = TABLE+'_body_guard'
    result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {TABLE} WHEN NOT COALESCE(({' AND '.join(conditions)}),0) BEGIN SELECT RAISE(ABORT,'runtime_target_entry_columns'); END"
    return result


def package_manifest():
    """Definition digest is a contribution, NOT the full target H1 fingerprint."""
    return dict(migration_id=PACKAGE, codec=FORMAT, definitions=definitions(),
                added_definitions_sha256=digest(definitions()))


def check_schema(conn):
    """Read-only exact package inspection, including unexpected attached triggers/indexes."""
    from . import operation_schema
    require(len(conn.execute('PRAGMA database_list').fetchall()) == 1, 'target_entry_attached_database')
    operation_schema.check_schema(conn)
    expected = definitions()
    objects = conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
    actual = {name: sql for _, name, _, sql in objects}
    require(all(actual.get(k) == sql for k, sql in expected.items()), 'target_entry_schema_mismatch')
    require(all(name in expected for _, name, table, _ in objects
                if table == TABLE or name.startswith(TABLE)), 'target_entry_unexpected_object')
    require(tuple(r[1] for r in conn.execute(f'PRAGMA table_info({TABLE})')) == COLUMNS, 'target_entry_columns')
    return package_manifest()


def check_rows(target, control):
    """Historical cross-store inspection only; caller owns stable paired reservations.

    No lookup result can recreate a continuation or authorize retries/admission.
    """
    from .administration_schema import check_control
    check_schema(target); check_control(control); attempts.check_rows(control)
    for row in target.execute(f'SELECT * FROM {TABLE}'):
        values = dict(zip(COLUMNS, tuple(row)))
        attempt_row = control.execute(f'SELECT body_json,body_sha256 FROM {attempts.ATTEMPTS} WHERE attempt_id=?', (values['attempt_id'],)).fetchone()
        require(attempt_row is not None, 'target_entry_attempt_missing')
        attempt = attempts.parse_attempt(attempt_row[0], attempt_sha256=attempt_row[1])
        event = control.execute(f'SELECT body_json FROM {attempts.HISTORY} WHERE attempt_id=? AND sequence=1', (attempt['attempt_id'],)).fetchone()
        source = control.execute(f'SELECT body_json FROM {authority.AUTHORITIES} WHERE authority_id=?', (attempt['authority_id'],)).fetchone()
        require(event is not None and source is not None, 'target_entry_sources_missing')
        body = parse_entry(values['body_json'], entry_sha256=values['body_sha256'],
            authority_body=load(source[0]), attempt=attempt, creation_event=load(event[0]))
        require(values['operation_id'] == body['operation_reference']['operation_id']
                and values['authority_sha256'] == body['authority_sha256']
                and values['writer_manifest_sha256'] == body['operation_reference']['writer_manifest_sha256']
                and values['entered_at'] == authority._time(body['entered_at_utc']), 'target_entry_columns')
        operation_row = target.execute('SELECT body_json,body_sha256 FROM recognition_operation_contracts WHERE operation_id=?', (values['operation_id'],)).fetchone()
        require(operation_row is not None and digest(load(operation_row[0])) == operation_row[1]
                == body['operation_reference']['operation_sha256'], 'target_entry_operation_mismatch')
    require(not target.execute('PRAGMA foreign_key_check').fetchone(), 'target_entry_foreign_key')
