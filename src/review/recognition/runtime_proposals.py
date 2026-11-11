"""4b-2 target-first proposal persistence. ACKNOWLEDGED is data, not authority.

No cross-database atomicity or orphan repair. Only the independent proposal
owner may commit. Public callers supply requests and existing credentials,
never manifests, observations, acknowledgements, connections or callbacks.
"""

from uuid import uuid4

from . import administration as a, dependencies, events, operations, operation_schema
from . import production_operations as legacy, runtime_operation_contract as contract
from . import runtime_proposal_records as records, runtime_proposal_transaction as owner
from . import runtime_validation as runtime
from .rules import canonical, digest
from .trust import require
from .runtime_proposal_transaction import (
    _persistence_mode as _mode, _target_query_only as _query_only, _target_commit_and_reserve)


def _request(value):
    contract._json(value)
    value = legacy._request(value)
    require(value['parent_operation_id'] is None, 'runtime_proposal_revision_not_enabled')
    require(len(canonical(value).encode('utf-8')) <= 262144, 'runtime_proposal_request_limit')
    return value


def _ack_rows(control, request_id, operation_id=None):
    a._audit_head(control)
    matches = []
    for row in control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence'):
        body = records._record(row)
        if body['action'] == records.ACK_ACTION:
            ack = records.parse_acknowledgement(row['body_json'], acknowledgement_sha256=row['body_sha256'])
            if (ack['subject']['creation']['request_id'] == request_id
                    or operation_id is not None and ack['subject']['operation_id'] == operation_id):
                matches.append(row)
        elif body['action'] == 'production_operation_created':
            require(body['subject'].get('request_id') != request_id
                    and (operation_id is None or body['subject'].get('operation_id') != operation_id),
                    'runtime_proposal_legacy_creation_conflict')
    require(len(matches) <= 1, 'runtime_proposal_ack_duplicate')
    return matches


def _inspect(state, request, session_token, primary_token):
    """Both stores inspected before any write, including after uncertain commit."""
    operation_schema.check_schema(state.body_target)
    rows = state.target.execute('SELECT * FROM recognition_operation_contracts '
        "WHERE json_extract(body_json,'$.creation.request_id')=?", (request['request_id'],)).fetchall()
    require(len(rows) <= 1, 'runtime_proposal_request_conflict')
    acks = _ack_rows(state.control, request['request_id'], rows[0]['operation_id'] if rows else None)
    if not rows:
        require(not acks, 'runtime_proposal_ack_target_missing')
        return dict(status='ABSENT')
    operation, _, sha = records._graph(state.body_target, rows[0]['operation_id'], state.view)
    require(operation['creation']['request_sha256'] == digest(request), 'runtime_proposal_request_conflict')
    if acks:
        return records.read_acknowledged_proposal(state.view, operation['operation_id'],
            session_token=session_token, primary_token=primary_token)
    # Never repair/promote a target-only graph, even with its original session.
    require(state.control.execute('SELECT 1 FROM recognition_approvals WHERE operation_id=?',
        (operation['operation_id'],)).fetchone() is None, 'runtime_proposal_unexpected_downstream_record')
    return dict(status='UNACKNOWLEDGED', operation_id=operation['operation_id'], operation_sha256=sha)


def inspect_proposal(config, session_token, request, *, primary_token):
    request = _request(request)
    with owner.proposal_transaction(config) as context:
        state = owner._state(context)
        state.view.validate_session(session_token, primary_token=primary_token)
        return _inspect(state, request, session_token, primary_token)


def _fresh_graph(state, operation_id):
    state.view.snapshot()
    operation, frozen, sha = records._graph(state.body_target, operation_id, state.view)
    p = frozen['preparation']
    # Use the original physical-identity dependency semantics on the owner's
    # actual connection; do not make a frozen preparation portable across hosts.
    require(dependencies.recheck(state.target, operation['event_id']) == dict(state='READY', reasons=[]),
            'runtime_proposal_dependencies_changed')
    require(events._generate(state.target, p['request']) == p['manifest'], 'runtime_proposal_manifest_changed')
    return operation, frozen, sha


def _final_check(state):
    pending = state.persistence
    state.view.validate_session(pending['session'], primary_token=pending['primary'])
    operation, _, sha = _fresh_graph(state, pending['operation_id'])
    require(sha == pending['operation_sha256'], 'runtime_proposal_durable_graph_changed')
    result = records.read_acknowledged_proposal(state.view, operation['operation_id'],
        session_token=pending['session'], primary_token=pending['primary'])
    require(result == pending['result'], 'runtime_proposal_ack_changed')


def create_proposal(config, session_token, request, *, primary_token):
    """Persist an initial graph then its exact ACK; never adopt a target orphan.

    Exceptions, including commit/cleanup failures, do not authorize a blind
    retry: inspect_proposal() reloads both stores. ABSENT permits a fresh attempt;
    UNACKNOWLEDGED is historical and requires a new request ID, not repair.
    """
    request = _request(request)
    with owner.proposal_transaction(config) as context:
        state = owner._state(context)
        actor = state.view.validate_session(session_token, primary_token=primary_token)
        existing = _inspect(state, request, session_token, primary_token)
        if existing['status'] != 'ABSENT':
            return existing
        now = runtime._utc_now()
        scope = state.view.snapshot()
        source = dict(family=request['family'], inputs=request['inputs'],
            evaluation_at_utc=request['evaluation_at_utc'], review_reference=request['review_reference'],
            preparer_id=str(actor['actor_id']),
            generation_reference=scope['installation_id'] + ':' + str(scope['generation']), parent_event_id=None)
        manifest = events._generate(state.target, source)
        p = dict(format='recognition-preparation-v1', preparation_id=str(uuid4()), request=source,
            generated_at_utc=now, generator='permanent._prepare:v1',
            target_observation=a.observe_target(state.target)['observation'], manifest=manifest,
            manifest_sha256=digest(manifest), population_sha256=digest(manifest['candidates']),
            dependencies=dependencies.build(state.target, manifest))
        e = dict(format='recognition-event-v1', event_id=str(uuid4()), preparation_id=p['preparation_id'],
            preparation_sha256=digest(p), parent_event_id=None, frozen_at_utc=now)
        frozen = dict(preparation=p, event=e)
        creation = dict(request_id=request['request_id'], request_sha256=digest(request),
            actor_id=actor['actor_id'], primary_sha256=a.token_hash(primary_token), session_sha256=a.token_hash(session_token))
        operation = contract.build_operation(state.view, frozen=frozen, operation_id=str(uuid4()),
            creation=creation, created_at_utc=now)
        state.view.validate_session(session_token, primary_token=primary_token)
        state.view.snapshot()
        _query_only(state, False)
        _mode(state, 'GRAPH')
        try:
            events._insert(state.target, 'recognition_preparations', 'preparation_id,parent_event_id',
                (p['preparation_id'], None), p)
            events._insert(state.target, 'recognition_frozen_events', 'event_id,preparation_id',
                (e['event_id'], p['preparation_id']), e)
            history = dict(event_id=e['event_id'], sequence=1, state='READY', reason='runtime-proposal-frozen',
                recorded_at_utc=now, previous_sha256=None)
            events._insert(state.target, 'recognition_event_history', 'event_id,sequence', (e['event_id'], 1), history)
            events._insert(state.target, 'recognition_operation_contracts', 'operation_id,event_id',
                (operation['operation_id'], e['event_id']), operation)
            operations._append_local(state.target, 'decisions', operation['operation_id'], [],
                'PREPARED', 'runtime-proposal-created', now)
            operations._append_local(state.target, 'executions', operation['operation_id'], [],
                'NOT_STARTED', 'runtime-proposal-created', now)
        finally:
            _mode(state, None)
        require(state.target.total_changes == state.target_changes + 6, 'runtime_proposal_graph_write_count')
        # Check the complete graph before making it durable as well as afterwards.
        _fresh_graph(state, operation['operation_id'])
        state.view.validate_session(session_token, primary_token=primary_token)
        _target_commit_and_reserve(state)
        state.view.validate_session(session_token, primary_token=primary_token)
        durable, frozen, sha = _fresh_graph(state, operation['operation_id'])
        require(durable == operation, 'runtime_proposal_durable_graph_changed')
        head = a._audit_head(state.control)
        ack = records.build_acknowledgement(durable, context=state.view, frozen=frozen, operation_sha256=sha,
            acknowledged_at_utc=runtime._utc_now(), previous_sha256=head['body_sha256'] if head else None)
        records.match_acknowledgement(durable, context=state.view, frozen=frozen, operation_sha256=sha,
            acknowledgement=ack, acknowledgement_sha256=digest(ack))
        _mode(state, 'ACK')
        try:
            state.control.execute('INSERT INTO recognition_admin_audit VALUES(?,?,?)',
                ((head['sequence'] + 1) if head else 1, canonical(ack), digest(ack)))
        finally:
            _mode(state, None)
        require(state.control.total_changes == state.control_changes + 1, 'runtime_proposal_ack_write_count')
        result = records.read_acknowledged_proposal(state.view, operation['operation_id'],
            session_token=session_token, primary_token=primary_token)
        state.target_changes += 6
        state.control_changes += 1
        state.persistence = dict(operation_id=operation['operation_id'], operation_sha256=sha,
            session=session_token, primary=primary_token, result=result)
        return result  # The owner's __exit__ validates and commits before return.
