"""Z31 inert DATA/DDL only. No connection opener, installer, producer or authority.

A detached witness is not evidence of persistence or of actual business effects.
Those facts require a separately reviewed transaction owner and effect verifier.
"""

from . import runtime_activation_authority_schema as authority
from . import runtime_operation_contract as operation, runtime_profile_schema as profiles
from .rules import canonical, digest
from .trust import fields, identity, load, require


DECISIONS = 'recognition_runtime_outcome_decisions'
HISTORY = 'recognition_runtime_outcome_history'
WITNESSES = 'recognition_runtime_outcome_witnesses'
DECISION_FORMAT = 'recognition-runtime-outcome-decision-v1'
EVENT_FORMAT = 'recognition-runtime-outcome-event-v1'
WITNESS_FORMAT = 'recognition-runtime-outcome-witness-v1'
MAX_BYTES = 1_000_000  # Also respects trust.load's bounded parser.
STATES = ('DECISION_CREATED', 'TARGET_PENDING', 'TARGET_UNCERTAIN', 'TARGET_FAILED', 'COMPLETED')
TRANSITIONS = {
    'DECISION_CREATED': ('TARGET_PENDING',),
    'TARGET_PENDING': ('TARGET_UNCERTAIN', 'TARGET_FAILED', 'COMPLETED'),
    'TARGET_UNCERTAIN': ('TARGET_FAILED', 'COMPLETED'),
    'TARGET_FAILED': (), 'COMPLETED': (),
}
CLASSIFICATIONS = ('COMMIT_UNCONFIRMED', 'CONNECTION_FAILURE', 'CLEANUP_FAILURE',
                   'INSPECTION_UNCONFIRMED', 'RESULT_PUBLICATION_FAILURE')


def _data(value, keys):
    operation._json(value)
    fields(value, keys)
    require(len(canonical(value).encode('utf-8')) <= MAX_BYTES, 'outcome_journal_size')


def _time(value):
    return authority._time(value)


def _source(decision):
    return authority.validate_authority(decision['authority'])


def validate_decision(value):
    _data(value, ('format', 'authority', 'recorded_at_utc'))
    require(value['format'] == DECISION_FORMAT, 'outcome_journal_format')
    source = _source(value)
    require(_time(source['issued_at_utc']) <= _time(value['recorded_at_utc']) <
            _time(source['expires_at_utc']), 'outcome_journal_decision_time')
    return operation._copy(value)


def _binding(value, decision):
    source = _source(validate_decision(decision))
    identity(value['authority_id']); profiles._check_sha(value['authority_sha256'])
    require(value['authority_id'] == source['authority_id'] and
            value['authority_sha256'] == digest(source), 'outcome_journal_scope')
    return source


def _genesis(decision):
    source = _source(decision)
    return dict(format=EVENT_FORMAT, authority_id=source['authority_id'], authority_sha256=digest(source),
                sequence=1, state='DECISION_CREATED', at_utc=decision['recorded_at_utc'], previous_sha256=None,
                actor_id=source['runtime_target']['owner_id'], evidence=dict(decision_sha256=digest(decision)))


def validate_event(value, *, decision, previous=None, pending=None, witness=None, _local_only=False):
    _data(value, ('format', 'authority_id', 'authority_sha256', 'sequence', 'state',
                  'at_utc', 'previous_sha256', 'actor_id', 'evidence'))
    require(value['format'] == EVENT_FORMAT and value['state'] in STATES, 'outcome_journal_state')
    source = _binding(value, decision)
    operation._positive(value['sequence']); operation._positive(value['actor_id'])
    require(value['actor_id'] == source['runtime_target']['owner_id'], 'outcome_journal_actor')
    now = _time(value['at_utc'])
    require(now >= _time(decision['recorded_at_utc']), 'outcome_journal_time')
    if previous is None:
        require(value['sequence'] == 1 and value['state'] == 'DECISION_CREATED' and
                value['previous_sha256'] is None and value['at_utc'] == decision['recorded_at_utc'],
                'outcome_journal_predecessor')
    else:
        require(previous['state'] in ('DECISION_CREATED', 'TARGET_PENDING', 'TARGET_UNCERTAIN'),
                'outcome_journal_predecessor')
        if previous['state'] == 'DECISION_CREATED':
            validate_event(previous, decision=decision)
        elif previous['state'] == 'TARGET_PENDING':
            validate_event(previous, decision=decision, previous=_genesis(decision))
        else:
            require(pending is not None, 'outcome_journal_pending')
            validate_event(previous, decision=decision, previous=pending, pending=pending)
        _binding(previous, decision)
        profiles._check_sha(value['previous_sha256'])
        require(value['sequence'] == previous['sequence'] + 1 and
                value['previous_sha256'] == digest(previous) and
                value['state'] in TRANSITIONS.get(previous['state'], ()) and
                now >= _time(previous['at_utc']), 'outcome_journal_predecessor')
    evidence = value['evidence']
    state = value['state']
    if state in ('DECISION_CREATED', 'TARGET_PENDING'):
        fields(evidence, ('decision_sha256',))
        require(evidence['decision_sha256'] == digest(decision), 'outcome_journal_decision_digest')
        require(now < _time(source['expires_at_utc']), 'outcome_journal_start_expired')
    else:
        require(pending is not None and pending['state'] == 'TARGET_PENDING', 'outcome_journal_pending')
        _binding(pending, decision)
        require(pending['sequence'] == 2 and pending['evidence'] == {'decision_sha256': digest(decision)}
                and _time(pending['at_utc']) < _time(source['expires_at_utc'])
                and now >= _time(pending['at_utc']), 'outcome_journal_pending')
        expected = {'TARGET_UNCERTAIN': ('pending_sha256', 'classification'),
                    'TARGET_FAILED': ('pending_sha256', 'no_commit_evidence_sha256'),
                    'COMPLETED': ('pending_sha256', 'witness_sha256')}[state]
        fields(evidence, expected)
        require(evidence['pending_sha256'] == digest(pending), 'outcome_journal_pending_digest')
        if state == 'TARGET_UNCERTAIN':
            require(evidence['classification'] in CLASSIFICATIONS, 'outcome_journal_classification')
        elif state == 'TARGET_FAILED':
            profiles._check_sha(evidence['no_commit_evidence_sha256'])
        else:
            if _local_only:
                # Local control structure only. No assertion of target commit;
                # callers admitting/publishing success must use the default
                # full witness/effect inspection under the finalization owner.
                profiles._check_sha(evidence['witness_sha256'])
                return operation._copy(value)
            require(witness is not None, 'outcome_journal_witness_required')
            validate_witness(witness)
            require(witness['decision'] == decision and witness['pending'] == pending and
                    evidence['witness_sha256'] == digest(witness) and
                    now >= _time(witness['recorded_at_utc']), 'outcome_journal_witness_scope')
    return operation._copy(value)


def validate_witness(value):
    _data(value, ('format', 'decision', 'pending', 'recorded_at_utc', 'outcome', 'effect_evidence_sha256'))
    require(value['format'] == WITNESS_FORMAT and value['outcome'] == 'TARGET_COMMITTED',
            'outcome_journal_witness_format')
    decision = validate_decision(value['decision'])
    pending = value['pending']
    # Validate the complete start graph, not a caller's asserted pending digest.
    source = _source(decision)
    genesis = _genesis(decision)
    validate_event(genesis, decision=decision)
    validate_event(pending, decision=decision, previous=genesis)
    require(pending['state'] == 'TARGET_PENDING', 'outcome_journal_pending')
    profiles._check_sha(value['effect_evidence_sha256'])
    require(_time(pending['at_utc']) <= _time(value['recorded_at_utc']) < _time(source['expires_at_utc']),
            'outcome_journal_witness_time')
    return operation._copy(value)


def encode_decision(value):
    return canonical(validate_decision(value))


def encode_event(value, **scope):
    return canonical(validate_event(value, **scope))


def encode_witness(value):
    return canonical(validate_witness(value))


def _parse(serialized, expected_sha256, validator, **scope):
    require(type(serialized) is str and len(serialized.encode('utf-8')) <= MAX_BYTES, 'outcome_journal_size')
    profiles._check_sha(expected_sha256)
    value = validator(load(serialized), **scope)
    require(canonical(value) == serialized and digest(value) == expected_sha256, 'outcome_journal_canonical')
    return value


def parse_decision(serialized, *, expected_sha256):
    return _parse(serialized, expected_sha256, validate_decision)


def parse_event(serialized, *, expected_sha256, **scope):
    return _parse(serialized, expected_sha256, validate_event, **scope)


def parse_witness(serialized, *, expected_sha256):
    return _parse(serialized, expected_sha256, validate_witness)


def definitions(side):
    """Return deterministic DDL only. Never executes it or changes a manifest."""
    require(side in ('control', 'target'), 'outcome_journal_side')
    c = profiles.column
    common = [c('authority_id', 'TEXT', profiles.uuid('authority_id')),
              c('authority_sha256', 'TEXT', profiles.sha('authority_sha256')),
              c('installation_id', 'TEXT', profiles.uuid('installation_id')),
              c('target_id', 'TEXT', profiles.uuid('target_id')),
              c('operation_id', 'TEXT', profiles.uuid('operation_id')),
              c('operation_sha256', 'TEXT', profiles.sha('operation_sha256')),
              c('writer_manifest_sha256', 'TEXT', profiles.sha('writer_manifest_sha256'))]
    body = [c('body_json', 'TEXT', "typeof(body_json)='text' AND instr(body_json,char(0))=0 "
              f'AND length(CAST(body_json AS BLOB))<={MAX_BYTES} AND json_valid(body_json)'),
            c('body_sha256', 'TEXT', profiles.sha('body_sha256'))]
    table = DECISIONS if side == 'control' else WITNESSES
    cols = common + [c('recorded_at', 'INTEGER', profiles.integer('recorded_at'))] + body
    keys = [('authority_id',), ('authority_sha256',), ('installation_id', 'target_id', 'operation_id'),
            ('installation_id', 'target_id', 'writer_manifest_sha256'), ('body_sha256',)]
    if side == 'target':
        cols += [c('pending_sha256', 'TEXT', profiles.sha('pending_sha256')),
                 c('effect_evidence_sha256', 'TEXT', profiles.sha('effect_evidence_sha256'))]
    cols += ['PRIMARY KEY(authority_id)'] + ['UNIQUE('+','.join(k)+')' for k in keys[1:]]
    result = {table: f"CREATE TABLE {table} ({', '.join(cols)})"}
    tables = {table: keys}
    if side == 'control':
        cols = [c('authority_id', 'TEXT', profiles.uuid('authority_id')),
                c('authority_sha256', 'TEXT', profiles.sha('authority_sha256')),
                c('sequence', 'INTEGER', profiles.integer('sequence', 1, 4)),
                c('state', 'TEXT', 'state IN ('+','.join(repr(s) for s in STATES)+')'),
                c('at', 'INTEGER', profiles.integer('at')), 'previous_sha256 TEXT CHECK(previous_sha256 IS NULL OR ('+
                profiles.sha('previous_sha256')+'))'] + body + [
                'PRIMARY KEY(authority_id,sequence)', 'UNIQUE(body_sha256)',
                f'FOREIGN KEY(authority_id) REFERENCES {DECISIONS}(authority_id)']
        result[HISTORY] = f"CREATE TABLE {HISTORY} ({', '.join(cols)})"
        tables[HISTORY] = [('authority_id', 'sequence'), ('body_sha256',)]
    for name, unique in tables.items():
        for verb in ('UPDATE', 'DELETE'):
            trigger = name+'_immutable_'+verb.lower()
            result[trigger] = f"CREATE TRIGGER {trigger} BEFORE {verb} ON {name} BEGIN SELECT RAISE(ABORT,'immutable_outcome_journal'); END"
        collisions = ' OR '.join('('+' AND '.join(f'{k}=NEW.{k}' for k in key)+')' for key in unique)
        trigger = name+'_immutable_replace'
        result[trigger] = f"CREATE TRIGGER {trigger} BEFORE INSERT ON {name} WHEN EXISTS(SELECT 1 FROM {name} WHERE {collisions}) BEGIN SELECT RAISE(ABORT,'immutable_outcome_journal'); END"
    def guard(name, condition):
        result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {HISTORY if name.endswith('_transition') else table} WHEN NOT COALESCE(({condition}),0) BEGIN SELECT RAISE(ABORT,'outcome_journal_binding'); END"
    prefix = '$.authority' if side == 'control' else '$.decision.authority'
    pairs = {'authority_id': prefix+'.authority_id', 'installation_id': prefix+'.runtime_target.installation_id',
             'target_id': prefix+'.runtime_target.target_id', 'operation_id': prefix+'.operation_reference.operation_id',
             'operation_sha256': prefix+'.operation_reference.operation_sha256',
             'writer_manifest_sha256': prefix+'.operation_reference.writer_manifest_sha256'}
    condition = [f"json_extract(NEW.body_json,'{path}')=NEW.{key}" for key, path in pairs.items()]
    condition += [f"json_extract(NEW.body_json,'$.format')='{DECISION_FORMAT if side == 'control' else WITNESS_FORMAT}'",
                  "json_type(NEW.body_json)='object'",
                  f"(SELECT count(*) FROM json_each(NEW.body_json))={3 if side == 'control' else 6}",
                  "json_extract(NEW.body_json,'$.recorded_at_utc')=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.recorded_at,'unixepoch')"]
    if side == 'target':
        condition += ["json_extract(NEW.body_json,'$.outcome')='TARGET_COMMITTED'",
                      "json_extract(NEW.body_json,'$.effect_evidence_sha256')=NEW.effect_evidence_sha256",
                      "json_extract(NEW.body_json,'$.pending.authority_sha256')=NEW.authority_sha256"]
    guard(table+'_binding', ' AND '.join(condition))
    if side == 'control':
        permitted = ' OR '.join(f"(old.state='{old}' AND NEW.state='{new}')" for old, targets in TRANSITIONS.items() for new in targets)
        guard(HISTORY+'_transition',
              f"EXISTS(SELECT 1 FROM {DECISIONS} d WHERE d.authority_id=NEW.authority_id AND d.authority_sha256=NEW.authority_sha256 AND d.recorded_at<=NEW.at) AND "
              f"NEW.sequence=COALESCE((SELECT MAX(sequence) FROM {HISTORY} WHERE authority_id=NEW.authority_id),0)+1 AND "
              "json_extract(NEW.body_json,'$.authority_id')=NEW.authority_id AND "
              "json_extract(NEW.body_json,'$.authority_sha256')=NEW.authority_sha256 AND "
              "json_type(NEW.body_json)='object' AND (SELECT count(*) FROM json_each(NEW.body_json))=9 AND "
              "json_type(NEW.body_json,'$.sequence')='integer' AND json_type(NEW.body_json,'$.actor_id')='integer' AND "
              "json_extract(NEW.body_json,'$.sequence')=NEW.sequence AND json_extract(NEW.body_json,'$.state')=NEW.state AND "
              "json_extract(NEW.body_json,'$.at_utc')=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.at,'unixepoch') AND "
              "((NEW.sequence=1 AND NEW.state='DECISION_CREATED' AND NEW.previous_sha256 IS NULL AND "
              "json_type(NEW.body_json,'$.previous_sha256')='null') OR "
              f"EXISTS(SELECT 1 FROM {HISTORY} old WHERE old.authority_id=NEW.authority_id AND old.sequence=NEW.sequence-1 "
              "AND old.body_sha256=NEW.previous_sha256 AND json_extract(NEW.body_json,'$.previous_sha256')=NEW.previous_sha256 "
              f"AND old.at<=NEW.at AND ({permitted})))")
    return result


def check_schema(connection, side):
    """Exact read-only package check; does not register a runtime manifest."""
    expected = definitions(side)
    tables = (DECISIONS, HISTORY) if side == 'control' else (WITNESSES,)
    actual = {}
    for row in connection.execute("SELECT name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL"):
        name, table, sql = tuple(row)
        if name.startswith('recognition_runtime_outcome_') or table in tables:
            actual[name] = sql
    require(actual == expected and len(connection.execute('PRAGMA database_list').fetchall()) == 1,
            'outcome_journal_partial_schema')


def inspect_rows(connection, side, *, witnesses=None, _local_only=False):
    """Read-only DATA integrity inspection, never current authority/admission."""
    require(side in ('control', 'target'), 'outcome_journal_side')
    check_schema(connection, side)
    table = DECISIONS if side == 'control' else WITNESSES
    decisions = {}
    for row in connection.execute(f'SELECT * FROM {table}'):
        row = dict(row)
        value = _parse(row['body_json'], row['body_sha256'], validate_decision if side == 'control' else validate_witness)
        decision = value if side == 'control' else value['decision']
        source = _source(decision)
        expected = dict(authority_id=source['authority_id'], authority_sha256=digest(source),
                        installation_id=source['runtime_target']['installation_id'], target_id=source['runtime_target']['target_id'],
                        operation_id=source['operation_reference']['operation_id'],
                        operation_sha256=source['operation_reference']['operation_sha256'],
                        writer_manifest_sha256=source['operation_reference']['writer_manifest_sha256'],
                        recorded_at=_time(value['recorded_at_utc']))
        if side == 'target':
            expected.update(pending_sha256=digest(value['pending']), effect_evidence_sha256=value['effect_evidence_sha256'])
        require(all(row[k] == v for k, v in expected.items()), 'outcome_journal_columns')
        decisions[row['authority_id']] = decision
    if side == 'control':
        for key, decision in decisions.items():
            previous = pending = None
            for row in connection.execute(f'SELECT * FROM {HISTORY} WHERE authority_id=? ORDER BY sequence', (key,)):
                row = dict(row)
                raw = load(row['body_json'])
                witness = None
                if raw['state'] == 'COMPLETED':
                    if not _local_only:
                        require(type(witnesses) is dict and key in witnesses, 'outcome_journal_target_inspection_required')
                        witness = witnesses[key]
                if _local_only:
                    value = validate_event(raw, decision=decision, previous=previous, pending=pending,
                                           witness=witness, _local_only=True)
                    require(row['body_json'] == canonical(value) and row['body_sha256'] == digest(value),
                            'outcome_journal_noncanonical')
                else:
                    value = parse_event(row['body_json'], expected_sha256=row['body_sha256'],
                                        decision=decision, previous=previous, pending=pending, witness=witness)
                require(row['sequence'] == value['sequence'] and row['state'] == value['state'] and
                        row['at'] == _time(value['at_utc']) and row['previous_sha256'] == value['previous_sha256'] and
                        row['authority_sha256'] == value['authority_sha256'], 'outcome_journal_columns')
                if value['state'] == 'TARGET_PENDING':
                    pending = value
                previous = value
            require(previous is not None, 'outcome_journal_missing_genesis')
    require(not connection.execute('PRAGMA foreign_key_check').fetchone(), 'outcome_journal_foreign_key')
    return dict(decisions=len(decisions), execution_authority=False, retry_authorized=False)
