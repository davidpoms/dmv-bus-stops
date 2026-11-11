"""4c-0 profile/ACK-scoped intent data only, never approval issuance."""

from copy import deepcopy
from datetime import datetime, timezone
import secrets

from . import administration as a, admin_auth as auth, dependencies
from . import runtime_approval_transaction as owner, runtime_operation_contract as contract
from . import runtime_proposal_records as records, runtime_scope_validation as shared, runtime_validation as v
from .rules import canonical, digest
from .trust import fields, identity, load, require, utc


STEP = 'recognition-runtime-approval-step-up-v1'
CONFIRMATION = 'recognition-runtime-approval-confirmation-v1'
STEP_ACTION = 'runtime_approval_step_up_issued'
CONFIRM_ACTION = 'runtime_approval_confirmation_issued'
CONSUME_ACTION = 'runtime_approval_confirmation_consumed'
BASE_FIELDS = frozenset('format token_sha256 reference local_target actor_id primary_sha256 session_sha256 issued_at_utc expires_at_utc'.split())


def _time(value):
    return datetime.fromtimestamp(value, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _reference(value):
    fields(value, records.REFERENCE_FIELDS)
    require(value['format'] == records.REFERENCE_FORMAT, 'runtime_approval_reference_format')
    identity(value['operation_id'])
    for key in ('operation_sha256', 'acknowledgement_sha256'):
        contract.profiles._check_sha(value[key])
    contract._positive(value['acknowledgement_sequence'])


def _reason(value):
    require(type(value) is str and value == value.strip() and 1 <= len(value) <= 2000 and '\0' not in value,
            'runtime_approval_reason_required')


def validate_artifact(body):
    contract._json(body)
    require(type(body) is dict, 'runtime_approval_artifact')
    kind = body.get('format')
    require(kind in (STEP, CONFIRMATION), 'runtime_approval_artifact_format')
    fields(body, BASE_FIELDS | ({'step_up_sha256', 'decision', 'reason'} if kind == CONFIRMATION else set()))
    _reference(body['reference'])
    contract._shape(body['local_target'])
    contract._positive(body['actor_id'])
    require(body['actor_id'] == body['local_target']['owner_id'], 'runtime_approval_owner')
    for key in ('token_sha256', 'primary_sha256', 'session_sha256'):
        contract.profiles._check_sha(body[key])
    require(0 < a.timestamp(body['expires_at_utc']) - a.timestamp(body['issued_at_utc']) <= auth.RECENT_SECONDS,
            'runtime_approval_artifact_expiry')
    utc(body['issued_at_utc']); utc(body['expires_at_utc'])
    if kind == CONFIRMATION:
        contract.profiles._check_sha(body['step_up_sha256'])
        require(body['decision'] == 'approve', 'runtime_approval_explicit_decision_required')
        _reason(body['reason'])
    require(len(canonical(body).encode('utf-8')) <= 16384, 'runtime_approval_artifact_limit')
    return contract._copy(body)


def _artifact(control, token_sha256, kind):
    contract.profiles._check_sha(token_sha256)
    action = STEP_ACTION if kind == STEP else CONFIRM_ACTION
    a._audit_head(control)
    matches = []
    for row in control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence'):
        body = records._record(row)
        if body['action'] == action and body['subject'].get('token_sha256') == token_sha256:
            artifact = validate_artifact(body['subject'])
            require(artifact['format'] == kind and body['actor'] == artifact['actor_id']
                    and body['at_utc'] == artifact['issued_at_utc'], 'runtime_approval_artifact_audit')
            matches.append(artifact)
    require(len(matches) == 1, 'runtime_approval_artifact_missing_or_duplicate')
    return matches[0]


def _current(state, session, primary, reference):
    _reference(reference)
    actor = state.view.validate_session(session, primary_token=primary)
    pair = records.read_proposal_reference(state.view, reference, session_token=session, primary_token=primary)
    require(dependencies.recheck(state.target, pair['operation']['event_id']) == dict(state='READY', reasons=[]),
            'runtime_approval_dependencies_not_ready')
    return actor, pair


def _check_scope(state, artifact, session, primary, reference):
    validate_artifact(artifact)
    require(artifact['reference'] == reference and artifact['local_target'] == contract.build_target(state.view)
            and artifact['session_sha256'] == a.token_hash(session)
            and artifact['primary_sha256'] == a.token_hash(primary), 'runtime_approval_artifact_scope')
    require(a.timestamp(artifact['issued_at_utc']) <= a.timestamp(v._utc_now()) < a.timestamp(artifact['expires_at_utc']),
            'runtime_approval_artifact_expired')
    state.auth_expiries.append((a.timestamp(artifact['expires_at_utc']), 'administrative_session_expired_or_revoked'))


def _row(state, artifact, kind):
    table = 'recognition_admin_stepups' if kind == STEP else 'recognition_admin_confirmations'
    row = state.control.execute('SELECT * FROM '+table+' WHERE token_hash=?', (artifact['token_sha256'],)).fetchone()
    require(row is not None and row['session_hash'] == artifact['session_sha256']
            and row['operation_id'] == artifact['reference']['operation_id']
            and row['operation_sha256'] == artifact['reference']['operation_sha256']
            and row['state_sha256'] == digest(artifact)
            and row['generation'] == artifact['local_target']['generation']
            and row['expires'] == a.timestamp(artifact['expires_at_utc']), 'runtime_approval_artifact_row')
    if kind == STEP:
        require(row['action'] == 'runtime_approve', 'runtime_approval_step_action')
    else:
        require(row['actor'] == artifact['actor_id'] and row['used'] == 0, 'runtime_approval_confirmation_consumed')
    return dict(row)


def _unused(control, artifact):
    """Immutable consumption history also fences accidentally resurrected rows."""
    a._audit_head(control)
    for row in control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence'):
        audit = records._record(row)
        if artifact['format'] == STEP and audit['action'] == CONFIRM_ACTION:
            require(audit['subject'].get('step_up_sha256') != digest(artifact), 'runtime_approval_step_consumed')
        if artifact['format'] == CONFIRMATION and audit['action'] == CONSUME_ACTION:
            require(audit['subject'].get('token_sha256') != artifact['token_sha256'], 'runtime_approval_confirmation_consumed')


def _mode(state, enabled):
    state.check()
    state.ceremony = enabled
    state.control.set_authorizer(state.control_authorizer)


def _final_check(state):
    pending = state.pending
    _current(state, pending['session'], pending['primary'], pending['artifact']['reference'])
    _check_scope(state, pending['artifact'], pending['session'], pending['primary'], pending['artifact']['reference'])
    require(v._denial_baseline(state.control) == pending['expected'], 'runtime_approval_ceremony_write_integrity')
    rows = state.control.execute('SELECT * FROM recognition_admin_audit WHERE sequence>? ORDER BY sequence',
                                  (state.audit_sequence,)).fetchall()
    require(len(rows) == 1 and records._record(rows[0]) == pending['audit'], 'runtime_approval_ceremony_audit_integrity')


def _complete(state, artifact, expected, action, session, primary, changes):
    head = a._audit_head(state.control)
    now = artifact['issued_at_utc'] if action != CONSUME_ACTION else v._utc_now()
    subject = artifact if action != CONSUME_ACTION else dict(format=CONSUME_ACTION,
        token_sha256=artifact['token_sha256'], artifact_sha256=digest(artifact))
    audit = dict(action=action, actor=artifact['actor_id'], at_utc=now, subject=subject,
                 previous_sha256=head['body_sha256'] if head else None)
    a._audit(state.control, action, artifact['actor_id'], now, subject)
    require(state.control.total_changes == state.control_changes + changes, 'runtime_approval_ceremony_write_count')
    state.pending = dict(artifact=artifact, expected=expected, audit=audit, session=session, primary=primary)
    state.control_changes += changes


def issue_step_up(config, session_token, code, reference, *, primary_token):
    """Fresh existing TOTP verification; only hashes/typed scope are persisted."""
    with owner.approval_transaction(config) as context:
        state = owner._state(context)
        actor, _ = _current(state, session_token, primary_token, reference)
        now = v._utc_now()
        session = state.control.execute('SELECT * FROM recognition_admin_sessions WHERE token_hash=?',
                                       (a.token_hash(session_token),)).fetchone()
        expires = min(a.timestamp(now)+auth.RECENT_SECONDS, session['expires'])
        raw = secrets.token_urlsafe(32)
        artifact = dict(format=STEP, token_sha256=a.token_hash(raw), reference=contract._copy(reference),
            local_target=contract.build_target(state.view), actor_id=actor['actor_id'],
            primary_sha256=a.token_hash(primary_token), session_sha256=a.token_hash(session_token),
            issued_at_utc=now, expires_at_utc=_time(expires))
        validate_artifact(artifact)
        expected = deepcopy(state.baseline)
        mfa = state.control.execute('SELECT * FROM recognition_admin_mfa WHERE actor=?', (actor['actor_id'],)).fetchone()
        _mode(state, True)
        try:
            # Use the existing verifier, throttle and counter-replay semantics.
            # Its denial commit is sealed/deferred by the private kernel facade.
            auth._code(state.kernel_control, config, {'installation_id': state.snapshot['installation_id']}, mfa, code, now)
            counter = state.control.execute('SELECT last_counter FROM recognition_admin_mfa WHERE actor=?', (actor['actor_id'],)).fetchone()[0]
            for row in expected['recognition_admin_mfa']:
                if row['actor'] == actor['actor_id']: row['last_counter'] = counter
            values = dict(token_hash=artifact['token_sha256'], session_hash=session['token_hash'], action='runtime_approve',
                operation_id=reference['operation_id'], operation_sha256=reference['operation_sha256'],
                state_sha256=digest(artifact), generation=state.snapshot['generation'], expires=expires)
            state.control.execute('INSERT INTO recognition_admin_stepups VALUES(?,?,?,?,?,?,?,?)', tuple(values.values()))
            expected['recognition_admin_stepups'].append(values)
            expected['recognition_admin_stepups'].sort(key=lambda row: row['token_hash'])
            _complete(state, artifact, expected, STEP_ACTION, session_token, primary_token, 3)
        finally:
            # Denial seals the state; cleanup must not mask its original error.
            state.ceremony = False
            state.control.set_authorizer(state.control_authorizer)
        return dict(token=raw, artifact=artifact, artifact_sha256=digest(artifact))


def begin_confirmation(config, session_token, step_token, reference, serialized_intent, *, primary_token):
    require(type(serialized_intent) is str and len(serialized_intent.encode('utf-8')) <= 8192, 'runtime_approval_intent_limit')
    intent = load(serialized_intent)
    contract._json(intent)
    fields(intent, ('decision', 'reason', 'confirm'))
    require(canonical(intent) == serialized_intent and intent['decision'] == 'approve' and intent['confirm'] is True,
            'runtime_approval_explicit_confirmation_required')
    _reason(intent['reason'])
    with owner.approval_transaction(config) as context:
        state = owner._state(context)
        _current(state, session_token, primary_token, reference)
        step = _artifact(state.control, a.token_hash(step_token), STEP)
        _check_scope(state, step, session_token, primary_token, reference)
        _row(state, step, STEP)
        _unused(state.control, step)
        raw = secrets.token_urlsafe(32)
        now = v._utc_now()
        artifact = dict(step, format=CONFIRMATION, token_sha256=a.token_hash(raw), issued_at_utc=now,
            step_up_sha256=digest(step), decision=intent['decision'], reason=intent['reason'])
        validate_artifact(artifact)
        expected = deepcopy(state.baseline)
        expected['recognition_admin_stepups'] = [r for r in expected['recognition_admin_stepups'] if r['token_hash'] != step['token_sha256']]
        row = dict(token_hash=artifact['token_sha256'], session_hash=artifact['session_sha256'], actor=artifact['actor_id'],
            operation_id=reference['operation_id'], operation_sha256=reference['operation_sha256'], state_sha256=digest(artifact),
            generation=state.snapshot['generation'], expires=a.timestamp(artifact['expires_at_utc']), used=0)
        expected['recognition_admin_confirmations'].append(row)
        expected['recognition_admin_confirmations'].sort(key=lambda r: r['token_hash'])
        _mode(state, True)
        try:
            state.control.execute('DELETE FROM recognition_admin_stepups WHERE token_hash=?', (step['token_sha256'],))
            state.control.execute('INSERT INTO recognition_admin_confirmations VALUES(?,?,?,?,?,?,?,?,?)', tuple(row.values()))
            _complete(state, artifact, expected, CONFIRM_ACTION, session_token, primary_token, 3)
        finally:
            state.ceremony = False
            state.control.set_authorizer(state.control_authorizer)
        return dict(token=raw, artifact=artifact, artifact_sha256=digest(artifact))


def consume_confirmation(config, session_token, confirmation_token, reference, *, primary_token):
    """Consume intent DATA only. A future approval must consume atomically itself."""
    with owner.approval_transaction(config) as context:
        state = owner._state(context)
        _current(state, session_token, primary_token, reference)
        artifact = _artifact(state.control, a.token_hash(confirmation_token), CONFIRMATION)
        _check_scope(state, artifact, session_token, primary_token, reference)
        _row(state, artifact, CONFIRMATION)
        _unused(state.control, artifact)
        expected = deepcopy(state.baseline)
        for row in expected['recognition_admin_confirmations']:
            if row['token_hash'] == artifact['token_sha256']: row['used'] = 1
        _mode(state, True)
        try:
            state.control.execute('UPDATE recognition_admin_confirmations SET used=1 WHERE token_hash=? AND used=0',
                                  (artifact['token_sha256'],))
            _complete(state, artifact, expected, CONSUME_ACTION, session_token, primary_token, 2)
        finally:
            state.ceremony = False
            state.control.set_authorizer(state.control_authorizer)
        return dict(artifact_sha256=digest(artifact), consumed=True, approval_created=False)
