"""Detached v2 approval codec and read-only fences; NO approval issuer."""

from . import administration as a, runtime_approval_ceremony as ceremony
from . import runtime_operation_contract as contract, runtime_proposal_records as records
from .rules import canonical, digest
from .trust import fields, identity, load, require, utc


FORMAT = 'recognition-runtime-approval-v2'
HISTORY = 'recognition-runtime-approval-history-v2'
FIELDS = frozenset('format approval_id binding actor_id primary_sha256 session_sha256 confirmation_sha256 approved_at_utc state decision reason predecessor_sha256 execution_authority'.split())
BINDING = frozenset('reference local_target step_up_sha256 confirmation_artifact_sha256'.split())


def validate(value):
    contract._json(value)
    fields(value, FIELDS)
    require(value['format'] == FORMAT and value['state'] == 'APPROVED' and value['decision'] == 'approve'
            and value['execution_authority'] is False and value['predecessor_sha256'] is None,
            'runtime_approval_format_or_authority')
    identity(value['approval_id'])
    contract._positive(value['actor_id'])
    utc(value['approved_at_utc'])
    ceremony._reason(value['reason'])
    for key in ('primary_sha256', 'session_sha256', 'confirmation_sha256'):
        contract.profiles._check_sha(value[key])
    binding = value['binding']
    fields(binding, BINDING)
    ceremony._reference(binding['reference'])
    contract._shape(binding['local_target'])
    for key in ('step_up_sha256', 'confirmation_artifact_sha256'):
        contract.profiles._check_sha(binding[key])
    require(value['actor_id'] == binding['local_target']['owner_id'], 'runtime_approval_owner')
    require(len(canonical(value).encode('utf-8')) <= 16384, 'runtime_approval_size_limit')
    return contract._copy(value)


def parse(serialized, *, approval_sha256):
    require(type(serialized) is str and len(serialized.encode('utf-8')) <= 16384, 'runtime_approval_size_limit')
    value = validate(load(serialized))
    contract.profiles._check_sha(approval_sha256)
    require(canonical(value) == serialized and digest(value) == approval_sha256, 'runtime_approval_integrity')
    return value


def _history_body(body, history, state, actor, now, reason):
    return dict(format=HISTORY, approval_id=body['approval_id'], approval_sha256=digest(body), binding=body['binding'],
        confirmation_sha256=body['confirmation_sha256'], actor_id=actor, at_utc=now, reason=reason,
        prior_state=history[-1]['state'] if history else 'PENDING', state=state,
        sequence=len(history)+1, previous_sha256=digest(history[-1]) if history else None)


def _historical(control, approval_id):
    """Integrity/history only. NEVER current approval authority; used by invalidation."""
    identity(approval_id)
    row = control.execute('SELECT * FROM recognition_approvals WHERE approval_id=?', (approval_id,)).fetchone()
    require(row is not None, 'runtime_approval_missing')
    body = parse(row['body_json'], approval_sha256=row['body_sha256'])
    require(body['approval_id'] == approval_id and body['binding']['reference']['operation_id'] == row['operation_id']
            and body['confirmation_sha256'] == row['confirmation_sha256'], 'runtime_approval_row_mismatch')
    history = []
    for row in control.execute('SELECT * FROM recognition_approval_history WHERE approval_id=? ORDER BY sequence', (approval_id,)):
        item = records._record(row)
        expected = _history_body(body, history, row['state'], item['actor_id'], item['at_utc'], item['reason'])
        contract._json(item)
        contract._positive(item['sequence'])
        require(type(row['sequence']) is int and row['sequence'] == len(history)+1 and item == expected,
                'runtime_approval_history_integrity')
        utc(item['at_utc'])
        actor = item['actor_id']
        require((type(actor) is int and actor > 0) or (type(actor) is str and actor == actor.strip() and 1 <= len(actor) <= 200),
                'runtime_approval_history_actor')
        ceremony._reason(item['reason'])
        require((not history and row['state'] == 'APPROVED' and item['actor_id'] == body['actor_id']
                 and item['at_utc'] == body['approved_at_utc'] and item['reason'] == body['reason'])
                or (history and history[-1]['state'] == 'APPROVED' and row['state'] in ('INVALIDATED', 'SUPERSEDED')
                    and utc(item['at_utc']) >= utc(history[-1]['at_utc'])), 'runtime_approval_history_transition')
        history.append(item)
    require(bool(history), 'runtime_approval_history_missing')
    return dict(approval=body, approval_sha256=digest(body), history=history, state=history[-1]['state'],
                execution_pending=True, production_authorization='BLOCKED', production_execution='BLOCKED')


def append_invalidation(control, value, actor, now, reason):
    require(value['state'] == 'APPROVED', 'runtime_approval_terminal')
    require((type(actor) is int and actor > 0) or (type(actor) is str and actor == actor.strip() and 1 <= len(actor) <= 200 and '\0' not in actor),
            'runtime_approval_history_actor')
    ceremony._reason(reason)
    require(utc(now) >= utc(value['history'][-1]['at_utc']), 'runtime_approval_history_clock')
    body = value['approval']
    item = _history_body(body, value['history'], 'INVALIDATED', actor, now, reason)
    control.execute('INSERT INTO recognition_approval_history VALUES(?,?,?,?,?)',
        (body['approval_id'], item['sequence'], item['state'], canonical(item), digest(item)))


def _final_invalidation(state):
    from . import runtime_validation as runtime
    pending = state.pending_invalidation
    state.view.validate_session(pending['session'], primary_token=pending['primary'])
    require(runtime._denial_baseline(state.control) == state.baseline, 'runtime_approval_invalidation_protected_state')
    require([tuple(row) for row in state.control.execute('SELECT * FROM recognition_approvals ORDER BY approval_id')] == pending['bodies'],
            'runtime_approval_invalidation_body_changed')
    require([tuple(row) for row in state.control.execute('SELECT * FROM recognition_approval_history ORDER BY approval_id,sequence')] == pending['history'],
            'runtime_approval_invalidation_history_changed')
    require([tuple(row) for row in state.control.execute('SELECT * FROM recognition_admin_audit WHERE sequence>? ORDER BY sequence',
        (state.audit_sequence,))] == pending['audit'], 'runtime_approval_invalidation_audit_changed')
    for approval_id in pending['invalidated']:
        require(_historical(state.control, approval_id)['state'] == 'INVALIDATED', 'runtime_approval_invalidation_missing')


def invalidate_stale_scope(config, session_token, *, primary_token):
    """Append invalidation under freshly validated current owner scope; no repair.

    Invalid identity/history or missing current authentication fails closed.
    Restore/rebind hooks still use version-aware _invalidate_all atomically.
    """
    from . import runtime_approval_transaction as owner, runtime_validation as runtime
    with owner.approval_transaction(config) as context:
        state = owner._state(context)
        state.view.validate_session(session_token, primary_token=primary_token)
        current = contract.build_target(state.view)
        bodies = [tuple(row) for row in state.control.execute('SELECT * FROM recognition_approvals ORDER BY approval_id')]
        invalidated = []
        expected_audit = []
        state.invalidation = True
        state.control.set_authorizer(state.control_authorizer)
        try:
            for row in state.control.execute('SELECT * FROM recognition_approvals ORDER BY approval_id').fetchall():
                body = records._record(row)
                if body['format'] != FORMAT:
                    continue
                value = _historical(state.control, row['approval_id'])
                if value['state'] == 'APPROVED' and value['approval']['binding']['local_target'] != current:
                    now = runtime._utc_now()
                    append_invalidation(state.control, value, current['owner_id'], now, 'runtime-approval-scope-changed')
                    head = a._audit_head(state.control)
                    subject = dict(approval_id=row['approval_id'], approval_sha256=value['approval_sha256'], current_target=current)
                    audit = dict(action='runtime_approval_invalidated', actor=current['owner_id'], at_utc=now,
                        subject=subject, previous_sha256=head['body_sha256'] if head else None)
                    expected_audit.append(((head['sequence']+1) if head else 1, canonical(audit), digest(audit)))
                    a._audit(state.control, 'runtime_approval_invalidated', current['owner_id'], now,
                        subject)
                    invalidated.append(row['approval_id'])
        finally:
            state.invalidation = False
            state.control.set_authorizer(state.control_authorizer)
        require(state.control.total_changes == state.control_changes + 2*len(invalidated), 'runtime_approval_invalidation_write_count')
        state.control_changes += 2*len(invalidated)
        state.pending_invalidation = dict(session=session_token, primary=primary_token, bodies=bodies, invalidated=invalidated,
            history=[tuple(row) for row in state.control.execute('SELECT * FROM recognition_approval_history ORDER BY approval_id,sequence')],
            audit=expected_audit)
        return dict(invalidated=invalidated, approval_created=False)


def read_current(context, approval_id, *, session_token, primary_token):
    """Resolve durable approval -> artifacts -> exact ACK/proposal/current scope.

    No detached approval is a capability. This is observation data only, and no
    production writer or downstream admission receives a capability from it.
    """
    from . import runtime_scope_validation as shared
    require(type(context) is shared.RuntimeReadView, 'runtime_approval_read_view_required')
    context.validate_session(session_token, primary_token=primary_token)
    _, (control, _, _, _), _ = shared._view_parts(context)
    value = _historical(control, approval_id)
    require(value['state'] == 'APPROVED', 'runtime_approval_not_current')
    body, binding = value['approval'], value['approval']['binding']
    contract.validate_target(binding['local_target'], context=context)
    confirmation = ceremony._artifact(control, body['confirmation_sha256'], ceremony.CONFIRMATION)
    require(digest(confirmation) == binding['confirmation_artifact_sha256']
            and confirmation['step_up_sha256'] == binding['step_up_sha256']
            and confirmation['reference'] == binding['reference'] and confirmation['local_target'] == binding['local_target']
            and confirmation['actor_id'] == body['actor_id'] and confirmation['reason'] == body['reason']
            and all(confirmation[k] == body[k] for k in ('primary_sha256', 'session_sha256')),
            'runtime_approval_confirmation_mismatch')
    steps = []
    for row in control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence'):
        audit = records._record(row)
        if audit['action'] == ceremony.STEP_ACTION and digest(audit['subject']) == binding['step_up_sha256']:
            steps.append(ceremony._artifact(control, audit['subject']['token_sha256'], ceremony.STEP))
    require(len(steps) == 1, 'runtime_approval_step_mismatch')
    step = steps[0]
    confirmations = []
    for row in control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence'):
        audit = records._record(row)
        if audit['action'] == ceremony.CONFIRM_ACTION and audit['subject'].get('step_up_sha256') == binding['step_up_sha256']:
            confirmations.append(ceremony.validate_artifact(audit['subject']))
    require(confirmations == [confirmation] and control.execute('SELECT 1 FROM recognition_admin_stepups WHERE token_hash=?',
        (step['token_sha256'],)).fetchone() is None, 'runtime_approval_step_consumption')
    require(all(step[k] == confirmation[k] for k in ('reference', 'local_target', 'actor_id', 'primary_sha256', 'session_sha256'))
            and utc(step['issued_at_utc']) <= utc(confirmation['issued_at_utc']) <= utc(body['approved_at_utc'])
            < utc(confirmation['expires_at_utc']) <= utc(step['expires_at_utc']), 'runtime_approval_ceremony_mismatch')
    _, _, current, _ = contract._current(context)
    primary_created = None
    for kind in ('primary', 'session'):
        table = 'recognition_admin_primary' if kind == 'primary' else 'recognition_admin_sessions'
        proof = control.execute('SELECT * FROM '+table+' WHERE token_hash=?', (body[kind+'_sha256'],)).fetchone()
        ref = control.execute(f'SELECT * FROM {contract.profiles.AUTH} WHERE token_kind=? AND token_hash=?',
                              (kind, body[kind+'_sha256'])).fetchone()
        require(proof is not None and ref is not None and proof['actor'] == current['owner_id']
                and proof['generation'] == current['generation'] and ref['profile_sha256'] == current['profile_sha256']
                and ref['created_at'] == proof['created'] and proof['auth_epoch'] == current['auth_epoch']
                and proof['created'] <= a.timestamp(body['approved_at_utc']) < proof['expires'],
                'runtime_approval_authentication_scope')
        if kind == 'session':
            require(proof['mfa_epoch'] == binding['local_target']['mfa_epoch']
                    and proof['primary_hash'] == body['primary_sha256'] and proof['created'] >= primary_created,
                    'runtime_approval_mfa_scope')
        else:
            primary_created = proof['created']
            require(proof['key_hash'] == current['owner_key_sha256'], 'runtime_approval_primary_scope')
    consumed = []
    for row in control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence'):
        audit = records._record(row)
        if audit['action'] == ceremony.CONSUME_ACTION and audit['subject'].get('token_sha256') == body['confirmation_sha256']:
            consumed.append(audit)
    require(len(consumed) == 1 and consumed[0]['actor'] == body['actor_id'] and consumed[0]['at_utc'] == body['approved_at_utc']
            and consumed[0]['subject'] == dict(format=ceremony.CONSUME_ACTION, token_sha256=body['confirmation_sha256'],
                                             artifact_sha256=digest(confirmation)), 'runtime_approval_confirmation_consumption')
    confirmation_row = control.execute('SELECT * FROM recognition_admin_confirmations WHERE token_hash=?', (body['confirmation_sha256'],)).fetchone()
    require(confirmation_row is not None and confirmation_row['used'] == 1
            and confirmation_row['state_sha256'] == digest(confirmation)
            and confirmation_row['session_hash'] == body['session_sha256']
            and confirmation_row['actor'] == body['actor_id']
            and confirmation_row['operation_id'] == binding['reference']['operation_id']
            and confirmation_row['operation_sha256'] == binding['reference']['operation_sha256']
            and confirmation_row['generation'] == binding['local_target']['generation']
            and confirmation_row['expires'] == a.timestamp(confirmation['expires_at_utc']), 'runtime_approval_confirmation_row')
    pair = records.read_approved_proposal(context, body, session_token=session_token, primary_token=primary_token)
    require(pair['reference'] == binding['reference'], 'runtime_approval_acknowledgement_mismatch')
    return contract._copy(value)
