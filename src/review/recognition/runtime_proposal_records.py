"""4b-1 acknowledgement data codecs and read-only proposal fences.

No persistence, transaction manager, route, admission context or writer exists
here. Digests establish content linkage, not authentication or cross-DB atomicity.
"""

from . import administration as a, events, operation_schema, operations, runtime_profile_schema as profiles
from . import runtime_operation_contract as contract, runtime_scope_validation as scope
from . import runtime_validation as runtime
from .rules import canonical, digest
from .trust import fields, identity, load, require, utc


ACK_FORMAT = 'recognition-runtime-proposal-acknowledgement-v1'
ACK_ACTION = 'runtime_operation_proposal_acknowledged'
REFERENCE_FORMAT = 'recognition-runtime-proposal-reference-v1'
SUBJECT_FIELDS = frozenset('''format operation_id operation_sha256 event_id event_sha256
    preparation_id preparation_sha256 local_target creation created_at_utc'''.split())
AUDIT_FIELDS = frozenset('action actor at_utc subject previous_sha256'.split())
REFERENCE_FIELDS = frozenset('''format operation_id operation_sha256
    acknowledgement_sequence acknowledgement_sha256'''.split())


def _sha(value):
    profiles._check_sha(value)


def _creation(value):
    fields(value, contract.CREATION_FIELDS)
    identity(value['request_id'])
    contract._positive(value['actor_id'])
    for key in ('request_sha256', 'primary_sha256', 'session_sha256'):
        _sha(value[key])


def _shape(value):
    contract._json(value)
    fields(value, AUDIT_FIELDS)
    require(value['action'] == ACK_ACTION, 'runtime_proposal_ack_action')
    contract._positive(value['actor'])
    utc(value['at_utc'])
    if value['previous_sha256'] is not None:
        _sha(value['previous_sha256'])
    subject = value['subject']
    fields(subject, SUBJECT_FIELDS)
    require(subject['format'] == ACK_FORMAT, 'runtime_proposal_ack_format')
    for key in ('operation_id', 'event_id', 'preparation_id'):
        identity(subject[key])
    for key in ('operation_sha256', 'event_sha256', 'preparation_sha256'):
        _sha(subject[key])
    contract._shape(subject['local_target'])
    _creation(subject['creation'])
    require(value['actor'] == subject['creation']['actor_id'] == subject['local_target']['owner_id'],
            'runtime_proposal_ack_owner')
    require(utc(subject['created_at_utc']) <= utc(value['at_utc']), 'runtime_proposal_ack_time_order')


def _subject(operation, operation_sha256):
    return dict(format=ACK_FORMAT, operation_id=operation['operation_id'],
        operation_sha256=operation_sha256, event_id=operation['event_id'],
        event_sha256=operation['event_sha256'], preparation_id=operation['preparation_id'],
        preparation_sha256=operation['preparation_sha256'], local_target=operation['local_target'],
        creation=operation['creation'], created_at_utc=operation['created_at_utc'])


def build_acknowledgement(operation, *, context, frozen, operation_sha256,
                          acknowledged_at_utc, previous_sha256):
    """Construct detached audit-body data; never appends it or proves authority."""
    operation = contract.validate_operation(operation, context=context, frozen=frozen,
                                            operation_sha256=operation_sha256)
    value = dict(action=ACK_ACTION, actor=operation['creation']['actor_id'],
                 at_utc=acknowledged_at_utc, subject=_subject(operation, operation_sha256),
                 previous_sha256=previous_sha256)
    _shape(value)
    return contract._copy(value)


def acknowledgement_digest(value):
    """Digest the complete existing audit body, including time and chain link."""
    _shape(value)
    return digest(value)


def parse_acknowledgement(serialized, *, acknowledgement_sha256):
    value = load(serialized)
    require(canonical(value) == serialized, 'runtime_proposal_ack_noncanonical_json')
    _shape(value)
    _sha(acknowledgement_sha256)
    require(digest(value) == acknowledgement_sha256, 'runtime_proposal_ack_digest')
    return contract._copy(value)


def match_acknowledgement(operation, *, context, frozen, operation_sha256,
                           acknowledgement, acknowledgement_sha256):
    """Exact content/current-scope comparison, not durable acknowledgement proof."""
    _shape(acknowledgement)
    _sha(acknowledgement_sha256)
    require(digest(acknowledgement) == acknowledgement_sha256, 'runtime_proposal_ack_digest')
    operation = contract.validate_operation(operation, context=context, frozen=frozen,
                                            operation_sha256=operation_sha256)
    expected = _subject(operation, operation_sha256)
    require(canonical(acknowledgement['subject']) == canonical(expected), 'runtime_proposal_ack_mismatch')
    moment = utc(acknowledgement['at_utc'])
    require(moment <= utc(runtime._utc_now()), 'runtime_proposal_ack_future')
    control, _, current, _ = contract._current(context)
    # Creation references are historical, not credentials. Expired/revoked-now
    # records may still describe creation, but must fit the claimed scope/time.
    for kind in ('primary', 'session'):
        table = 'recognition_admin_primary' if kind == 'primary' else 'recognition_admin_sessions'
        proof = control.execute(f'SELECT * FROM {table} WHERE token_hash=?',
                                (operation['creation'][kind + '_sha256'],)).fetchone()
        require(proof['auth_epoch'] == current['auth_epoch']
                and proof['created'] <= a.timestamp(operation['created_at_utc'])
                and proof['created'] <= a.timestamp(acknowledgement['at_utc']) < proof['expires'],
                'runtime_proposal_ack_authentication_scope')
        if kind == 'primary':
            require(proof['key_hash'] == current['owner_key_sha256'], 'runtime_proposal_ack_authentication_scope')
        else:
            require(proof['mfa_epoch'] == operation['local_target']['mfa_epoch'],
                    'runtime_proposal_ack_authentication_scope')
    return contract._copy(acknowledgement)


def _record(row):
    require(row is not None, 'runtime_proposal_record_missing')
    value = load(row['body_json'])
    require(type(value) is dict, 'runtime_proposal_record_integrity')
    contract._json(value)
    _sha(row['body_sha256'])
    require(canonical(value) == row['body_json'] and digest(value) == row['body_sha256'],
            'runtime_proposal_record_integrity')
    return value


def _graph(target, operation_id, context):
    operation_schema.check_schema(target)
    row = target.execute('SELECT * FROM recognition_operation_contracts WHERE operation_id=?',
                          (operation_id,)).fetchone()
    body = _record(row)
    require(type(body) is dict and body.get('format') == contract.OPERATION_FORMAT,
            'runtime_proposal_v2_required')
    fields(body, contract.ENVELOPE_FIELDS)
    identity(body['event_id'])
    require(body['operation_id'] == operation_id and row['event_id'] == body['event_id'],
            'runtime_proposal_graph_mismatch')
    require(body['parent_event_id'] is None, 'runtime_proposal_revision_not_enabled')
    frozen = events.get_event(target, body['event_id'])
    for item in frozen['history']:
        contract._json(item)
        contract._positive(item['sequence'])
    require(len(frozen['history']) == 1 and frozen['state'] == 'READY', 'runtime_proposal_event_not_initial')
    require(utc(frozen['history'][0]['recorded_at_utc']) == utc(frozen['event']['frozen_at_utc']),
            'runtime_proposal_history_time')
    detached = dict(preparation=frozen['preparation'], event=frozen['event'])
    contract.validate_operation(body, context=context, frozen=detached, operation_sha256=row['body_sha256'])
    for kind, initial in (('decisions', 'PREPARED'), ('executions', 'NOT_STARTED')):
        history = operations._history(target, kind, operation_id, local=True)
        for item in history:
            contract._json(item)
            contract._positive(item['sequence'])
        require(len(history) == 1 and history[0]['state'] == initial and history[0]['evidence'] is None,
                'runtime_proposal_operation_not_initial')
        require(utc(history[0]['recorded_at_utc']) == utc(body['created_at_utc']), 'runtime_proposal_history_time')
    for table in ('recognition_operation_receipts', 'recognition_execution_claims',
                  'recognition_execution_seals', 'recognition_execution_audit'):
        if target.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
            require(target.execute(f'SELECT 1 FROM {table} WHERE operation_id=?', (operation_id,)).fetchone() is None,
                    'runtime_proposal_unexpected_downstream_record')
    duplicates = target.execute("SELECT operation_id FROM recognition_operation_contracts "
        "WHERE json_extract(body_json,'$.creation.request_id')=?", (body['creation']['request_id'],)).fetchall()
    require(len(duplicates) == 1 and duplicates[0][0] == operation_id, 'runtime_proposal_request_conflict')
    return body, detached, row['body_sha256']


def read_acknowledged_proposal(context, operation_id, *, session_token, primary_token):
    return _read_pair(context, operation_id, session_token=session_token, primary_token=primary_token)


def _read_pair(context, operation_id, *, session_token, primary_token, approval=None):
    """Reload a durable pair under current authentication; return DATA only.

    No detached acknowledgement/reference is accepted as proof. No retry repair,
    graph creation, acknowledgement append or downstream admission occurs.
    """
    identity(operation_id)
    if type(context) is scope.RuntimeReadView:
        view = context
    else:
        view = scope.read_view(context)
    view.validate_session(session_token, primary_token=primary_token)
    _, (control, target, _, _), _ = scope._view_parts(view)
    operation, frozen, operation_sha256 = _graph(target, operation_id, view)
    # Validate the complete chain, not just a JSON-filtered subset of rows.
    a._audit_head(control)
    matches = []
    for row in control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence'):
        body = _record(row)
        fields(body, AUDIT_FIELDS)
        if body['action'] == 'production_operation_created':
            legacy = body['subject']
            require(type(legacy) is dict and legacy.get('operation_id') != operation_id
                    and legacy.get('request_id') != operation['creation']['request_id'],
                    'runtime_proposal_legacy_creation_conflict')
        if body.get('action') != ACK_ACTION:
            continue
        ack = parse_acknowledgement(row['body_json'], acknowledgement_sha256=row['body_sha256'])
        if (ack['subject']['operation_id'] == operation_id
                or ack['subject']['creation']['request_id'] == operation['creation']['request_id']):
            matches.append((row['sequence'], row['body_sha256'], ack))
    require(len(matches) == 1, 'runtime_proposal_ack_missing_or_duplicate')
    sequence, ack_sha256, ack = matches[0]
    contract._positive(sequence)
    match_acknowledgement(operation, context=view, frozen=frozen, operation_sha256=operation_sha256,
                          acknowledgement=ack, acknowledgement_sha256=ack_sha256)
    existing = control.execute('SELECT * FROM recognition_approvals WHERE operation_id=?', (operation_id,)).fetchone()
    if approval is None:
        require(existing is None, 'runtime_proposal_unexpected_downstream_record')
    else:
        require(existing is not None and existing['body_json'] == canonical(approval)
                and existing['body_sha256'] == digest(approval), 'runtime_proposal_approval_mismatch')
    # Revalidate the borrowed scope/MFA epoch before returning detached data.
    view.snapshot()
    reference = dict(format=REFERENCE_FORMAT, operation_id=operation_id, operation_sha256=operation_sha256,
                     acknowledgement_sequence=sequence, acknowledgement_sha256=ack_sha256)
    return contract._copy(dict(status='ACKNOWLEDGED', operation=operation,
                               acknowledgement=ack, reference=reference))


def read_approved_proposal(context, approval, *, session_token, primary_token):
    """Separate read-only v2 linkage fence; ordinary proposal reader stays strict."""
    from . import runtime_approval_contract as approved
    approval = approved.validate(approval)
    contract.validate_target(approval['binding']['local_target'], context=context)
    _, (control, _, _, _), _ = scope._view_parts(context)
    history = approved._historical(control, approval['approval_id'])
    require(history['state'] == 'APPROVED' and history['approval_sha256'] == digest(approval),
            'runtime_proposal_approval_not_current')
    pair = _read_pair(context, approval['binding']['reference']['operation_id'],
        session_token=session_token, primary_token=primary_token, approval=approval)
    require(pair['reference'] == approval['binding']['reference'], 'runtime_proposal_approval_reference_mismatch')
    return pair


def read_proposal_reference(context, value, *, session_token, primary_token):
    """Resolve lookup data by reloading the durable pair, never trusting a cache."""
    contract._json(value)
    fields(value, REFERENCE_FIELDS)
    require(value['format'] == REFERENCE_FORMAT, 'runtime_proposal_reference_format')
    identity(value['operation_id'])
    _sha(value['operation_sha256'])
    _sha(value['acknowledgement_sha256'])
    contract._positive(value['acknowledgement_sequence'])
    proposal = read_acknowledged_proposal(context, value['operation_id'],
        session_token=session_token, primary_token=primary_token)
    require(canonical(value) == canonical(proposal['reference']), 'runtime_proposal_reference_mismatch')
    return contract._copy(proposal)
