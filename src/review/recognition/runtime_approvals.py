"""Fixed ACKNOWLEDGED -> APPROVED protocol. No downstream admission authority."""

from copy import deepcopy

from . import administration as a, dependencies, runtime_validation as runtime
from . import runtime_approval_transaction as owner, runtime_approval_ceremony as ceremony
from . import runtime_approval_contract as codec, runtime_operation_contract as contract
from . import runtime_proposal_records as records
from .rules import canonical, digest
from .trust import fields, identity, load, require


ACTION = 'runtime_approval_issued'


def _request(serialized):
    require(type(serialized) is str and len(serialized.encode('utf-8')) <= 8192,
            'runtime_approval_request_limit')
    value = load(serialized)
    contract._json(value)
    fields(value, ('approval_id', 'reference'))
    identity(value['approval_id'])
    ceremony._reference(value['reference'])
    require(canonical(value) == serialized, 'runtime_approval_request_noncanonical')
    return value


def _rows(control, table, order):
    return [tuple(row) for row in control.execute('SELECT * FROM '+table+' ORDER BY '+order)]


def _confirmation(state, token, session, primary, reference):
    confirmation = ceremony._artifact(state.control, a.token_hash(token), ceremony.CONFIRMATION)
    ceremony._check_scope(state, confirmation, session, primary, reference)
    ceremony._row(state, confirmation, ceremony.CONFIRMATION)
    ceremony._unused(state.control, confirmation)
    steps, confirmations = [], []
    for row in state.control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence'):
        audit = records._record(row)
        if audit['action'] == ceremony.STEP_ACTION and digest(audit['subject']) == confirmation['step_up_sha256']:
            steps.append(ceremony._artifact(state.control, audit['subject']['token_sha256'], ceremony.STEP))
        if audit['action'] == ceremony.CONFIRM_ACTION and audit['subject'].get('step_up_sha256') == confirmation['step_up_sha256']:
            confirmations.append(ceremony.validate_artifact(audit['subject']))
    require(len(steps) == 1 and confirmations == [confirmation], 'runtime_approval_step_mismatch')
    step = steps[0]
    ceremony._check_scope(state, step, session, primary, reference)
    require(state.control.execute('SELECT 1 FROM recognition_admin_stepups WHERE token_hash=?',
            (step['token_sha256'],)).fetchone() is None,
            'runtime_approval_step_consumption')
    require(all(step[key] == confirmation[key] for key in (
        'reference', 'local_target', 'actor_id', 'primary_sha256', 'session_sha256'))
        and step['issued_at_utc'] <= confirmation['issued_at_utc']
        and confirmation['expires_at_utc'] <= step['expires_at_utc'], 'runtime_approval_ceremony_mismatch')
    return confirmation


def _dependencies(state, value):
    operation_id = value['approval']['binding']['reference']['operation_id']
    pair = records.read_approved_proposal(state.view, value['approval'],
        session_token=state.pending_issuance['session'], primary_token=state.pending_issuance['primary'])
    require(pair['operation']['operation_id'] == operation_id
            and dependencies.recheck(state.target, pair['operation']['event_id']) == dict(state='READY', reasons=[]),
            'runtime_approval_dependencies_not_ready')


def _final_check(state):
    pending = state.pending_issuance
    value = codec.read_current(state.view, pending['approval_id'],
        session_token=pending['session'], primary_token=pending['primary'])
    require(value == pending['result'], 'runtime_approval_result_changed')
    _dependencies(state, value)
    require(runtime._denial_baseline(state.control) == pending['protected'], 'runtime_approval_protected_state_changed')
    for table, order, key in (('recognition_approvals', 'approval_id', 'bodies'),
                              ('recognition_approval_history', 'approval_id,sequence', 'history')):
        require(_rows(state.control, table, order) == pending[key], 'runtime_approval_write_integrity')
    rows = [tuple(row) for row in state.control.execute(
        'SELECT * FROM recognition_admin_audit WHERE sequence>? ORDER BY sequence', (state.audit_sequence,))]
    require(rows == pending['audit'], 'runtime_approval_audit_integrity')


def issue_approval(config, session_token, confirmation_token, serialized_request, *, primary_token):
    """Explicit confirmed owner intent, exact pair, one effective immutable approval.

    The request supplies lookup/idempotency data only. All authority and decision
    data are reloaded from current durable scope and the one-use confirmation.
    Commit errors are uncertain: retry this SAME identity to inspect durable state.
    """
    request = _request(serialized_request)
    with owner.approval_transaction(config) as context:
        state = owner._state(context)
        state.view.validate_session(session_token, primary_token=primary_token)
        reference = request['reference']
        existing = state.control.execute('SELECT * FROM recognition_approvals WHERE approval_id=? OR operation_id=?',
            (request['approval_id'], reference['operation_id'])).fetchall()
        if existing:
            require(len(existing) == 1 and existing[0]['approval_id'] == request['approval_id'],
                    'runtime_approval_identity_conflict')
            value = codec.read_current(state.view, request['approval_id'],
                session_token=session_token, primary_token=primary_token)
            body = value['approval']
            require(body['binding']['reference'] == reference
                    and body['confirmation_sha256'] == a.token_hash(confirmation_token)
                    and body['session_sha256'] == a.token_hash(session_token)
                    and body['primary_sha256'] == a.token_hash(primary_token), 'runtime_approval_retry_conflict')
            # The exact committed transition needs no new ceremony or writes.
            state.pending_issuance = dict(approval_id=request['approval_id'], session=session_token, primary=primary_token,
                result=value, protected=deepcopy(state.baseline),
                bodies=_rows(state.control, 'recognition_approvals', 'approval_id'),
                history=_rows(state.control, 'recognition_approval_history', 'approval_id,sequence'), audit=[])
            return value
        actor, _ = ceremony._current(state, session_token, primary_token, reference)
        confirmation = _confirmation(state, confirmation_token, session_token, primary_token, reference)
        now = runtime._utc_now()
        require(a.timestamp(confirmation['issued_at_utc']) <= a.timestamp(now)
                < a.timestamp(confirmation['expires_at_utc']), 'runtime_approval_artifact_expired')
        body = codec.validate(dict(format=codec.FORMAT, approval_id=request['approval_id'],
            binding=dict(reference=contract._copy(reference), local_target=contract.build_target(state.view),
                step_up_sha256=confirmation['step_up_sha256'], confirmation_artifact_sha256=digest(confirmation)),
            actor_id=actor['actor_id'], primary_sha256=a.token_hash(primary_token), session_sha256=a.token_hash(session_token),
            confirmation_sha256=confirmation['token_sha256'], approved_at_utc=now, state='APPROVED',
            decision=confirmation['decision'], reason=confirmation['reason'], predecessor_sha256=None, execution_authority=False))
        history = codec._history_body(body, [], 'APPROVED', body['actor_id'], now, body['reason'])
        protected = deepcopy(state.baseline)
        for row in protected['recognition_admin_confirmations']:
            if row['token_hash'] == confirmation['token_sha256']:
                row['used'] = 1
        bodies = _rows(state.control, 'recognition_approvals', 'approval_id')
        bodies.append((body['approval_id'], reference['operation_id'], body['confirmation_sha256'], canonical(body), digest(body)))
        histories = _rows(state.control, 'recognition_approval_history', 'approval_id,sequence')
        histories.append((body['approval_id'], 1, 'APPROVED', canonical(history), digest(history)))
        head = a._audit_head(state.control)
        sequence, previous = (head['sequence'], head['body_sha256']) if head else (0, None)
        audits = []
        subjects = ((ceremony.CONSUME_ACTION, dict(format=ceremony.CONSUME_ACTION,
                        token_sha256=confirmation['token_sha256'], artifact_sha256=digest(confirmation))),
                    (ACTION, dict(approval_id=body['approval_id'], approval_sha256=digest(body), binding=body['binding'])))
        for action, subject in subjects:
            audit = dict(action=action, actor=body['actor_id'], at_utc=now, subject=subject, previous_sha256=previous)
            sequence += 1
            audits.append((sequence, canonical(audit), digest(audit)))
            previous = digest(audit)
        state.issuing = True
        state.control.set_authorizer(state.control_authorizer)
        try:
            cursor = state.control.execute('UPDATE recognition_admin_confirmations SET used=1 WHERE token_hash=? AND used=0',
                (confirmation['token_sha256'],))
            require(cursor.rowcount == 1, 'runtime_approval_confirmation_consumed')
            state.control.execute('INSERT INTO recognition_approvals VALUES(?,?,?,?,?)', bodies[-1])
            state.control.execute('INSERT INTO recognition_approval_history VALUES(?,?,?,?,?)', histories[-1])
            for action, subject in subjects:
                a._audit(state.control, action, body['actor_id'], now, subject)
        finally:
            state.issuing = False
            state.control.set_authorizer(state.control_authorizer)
        require(state.control.total_changes == state.control_changes+5, 'runtime_approval_write_count')
        state.control_changes += 5
        result = codec.read_current(state.view, body['approval_id'], session_token=session_token, primary_token=primary_token)
        state.pending_issuance = dict(approval_id=body['approval_id'], session=session_token, primary=primary_token,
            result=result, protected=protected, bodies=sorted(bodies), history=sorted(histories), audit=audits)
        return result
