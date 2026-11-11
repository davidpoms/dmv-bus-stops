"""Authority-specific consent DATA and live validation; no authority producer."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import secrets
from weakref import WeakKeyDictionary

from . import administration as a, admin_auth as auth, dependencies, events, execution
from . import runtime_authority_consent_transaction as owner
from . import runtime_activation_authority_schema as storage, runtime_approval_contract as approvals
from . import runtime_operation_contract as contract, runtime_proposal_records as records
from . import runtime_validation as v, runtime_claim_disposition as disposition, local_readiness as readiness
from .rules import canonical, digest
from .trust import fields, load, require


_results = WeakKeyDictionary()


def _subject(state):
    view = state.view
    actor = view.validate_session(state.session, primary_token=state.primary)
    approved = approvals.read_current(view, state.approval_id, session_token=state.session, primary_token=state.primary)
    require(approved['approval_sha256'] == state.approval_sha256
            and canonical(approved['approval']['binding']['reference']) == canonical(state.reference),
            'authority_consent_approval_mismatch')
    pair = records.read_approved_proposal(view, approved['approval'], session_token=state.session, primary_token=state.primary)
    op = pair['operation']
    require(state.control.execute("SELECT 1 FROM sqlite_master WHERE name=?", (storage.AUTHORITIES,)).fetchone(),
            'authority_consent_storage_required')
    require(not state.control.execute(f'SELECT 1 FROM {storage.AUTHORITIES} WHERE operation_id=? OR writer_manifest_sha256=?',
            (op['operation_id'], op['writer_manifest_sha256'])).fetchone(), 'authority_consent_authority_exists')
    require(not state.control.execute('SELECT 1 FROM recognition_runtime_execution_claims WHERE operation_id=?',
            (op['operation_id'],)).fetchone(), 'authority_consent_preactivation_claim')
    require(dependencies.recheck(state.target, op['event_id']) == dict(state='READY', reasons=[]),
            'authority_consent_dependencies_not_ready')
    frozen = events.get_event(state.target, op['event_id'])
    dep = frozen['preparation']['dependencies']
    require(op['dependencies_sha256'] == digest(dep), 'authority_consent_dependencies_mismatch')
    stop = execution._stop(state.control)
    require(stop['sequence'] > 0 and stop['active'] is False, 'emergency_stop')
    require(not state.control.execute('SELECT 1 FROM recognition_execution_blocks WHERE operation_id=?',
            (op['operation_id'],)).fetchone(), 'authority_consent_operation_blocked')
    binding, profile, head = v._history(state.control)
    inventory = disposition._inspect_reserved(state.control, binding, profile, head, state.clock)
    require(not any(row['blocks_readiness'] for row in inventory['claims']), 'authority_consent_claim_disposition_blocked')
    assessment = readiness._assess_authority_consent(view, state.session, state.primary)
    require(assessment['code_ready'] is True and assessment['rehearsal_evidence_present'] is True
            and assessment['activation_state'] == 'ACTIVATED', 'authority_consent_readiness_blocked')
    _, _, activation = owner._current(state)
    reference = {k:op[k] for k in ('operation_id', 'event_id', 'event_sha256', 'preparation_id',
                                 'preparation_sha256', 'writer_manifest_sha256', 'population_sha256')}
    reference.update(operation_sha256=digest(op), writer_family=op['family'], proposal_reference=pair['reference'])
    result = dict(operation_reference=reference, runtime_target=contract.build_target(view),
        physical_snapshot=dict(target=a.observe_target(state.target), control_identity=asdict(a.target_identity(state.control))),
        activation=dict(sequence=activation['sequence'], event_sha256=digest(activation)),
        approval=dict(approval_id=state.approval_id, approval_sha256=approved['approval_sha256'],
                      effective_history_sha256=digest(approved['history'][-1])),
        authentication=dict(actor_id=actor['actor_id'], primary_sha256=a.token_hash(state.primary), session_sha256=a.token_hash(state.session)),
        dependencies=dict(snapshot=dep, snapshot_sha256=digest(dep)),
        emergency_stop=dict(snapshot=stop, snapshot_sha256=digest(stop)),
        readiness=readiness._assessment_binding(assessment), reason=state.reason)
    fields(result, storage.SUBJECT_FIELDS); storage._json(result)
    owner._read_parts(state.context); owner._time(state)
    return contract._copy(result)


def _time(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _artifact(state, raw, kind):
    token = a.token_hash(raw)
    action = storage.STEP_ACTION if kind == storage.STEP else storage.CONFIRM_ACTION
    matches = [storage._record(row) for row in storage._rows(state.control, action)
               if storage._record(row)['subject'].get('token_sha256') == token]
    require(len(matches) == 1, 'authority_consent_artifact_missing_or_duplicate')
    return storage._artifact(state.control, digest(matches[0]['subject']), action, kind)


def _fresh(state, artifact):
    require(canonical(artifact['subject']) == canonical(state.subject)
            and artifact['subject_sha256'] == digest(state.subject)
            and type(artifact['actor_id']) is int and artifact['actor_id'] == state.snapshot['owner_id']
            and artifact['primary_sha256'] == a.token_hash(state.primary)
            and artifact['session_sha256'] == a.token_hash(state.session), 'authority_consent_artifact_scope')
    now = a.timestamp(v._utc_now())
    require(a.timestamp(artifact['issued_at_utc']) <= now < a.timestamp(artifact['expires_at_utc']),
            'authority_consent_expired')
    # Deadlines are manager-private, not caller-selected or renewable.
    state.auth_expiries.append((a.timestamp(artifact['expires_at_utc']), 'administrative_session_expired_or_revoked'))
    owner._time(state)


def _step_unused(state, artifact):
    require(not any(storage._record(row)['subject'].get('step_artifact_sha256') == digest(artifact)
                    for row in storage._rows(state.control, storage.CONFIRM_ACTION)), 'authority_consent_step_used')


def _confirmation(state, raw):
    artifact = _artifact(state, raw, storage.CONFIRMATION)
    _fresh(state, artifact)
    step = storage._artifact(state.control, artifact['step_artifact_sha256'], storage.STEP_ACTION, storage.STEP)
    _fresh(state, step)
    require(a.timestamp(step['issued_at_utc']) <= a.timestamp(artifact['issued_at_utc'])
            and artifact['expires_at_utc'] == step['expires_at_utc'], 'authority_consent_deadline_changed')
    confirmations = [storage._record(row)['subject'] for row in storage._rows(state.control, storage.CONFIRM_ACTION)
                     if storage._record(row)['subject'].get('step_artifact_sha256') == digest(step)]
    require(len(confirmations) == 1 and canonical(confirmations[0]) == canonical(artifact), 'authority_consent_step_replayed')
    require(not any(storage._record(row)['subject'].get('token_sha256') == artifact['token_sha256']
                    for row in storage._rows(state.control, storage.CONSUME_ACTION)), 'authority_consent_confirmation_consumed')
    row = state.control.execute('SELECT * FROM recognition_admin_confirmations WHERE token_hash=?', (artifact['token_sha256'],)).fetchone()
    require(row is not None and dict(row) == dict(token_hash=artifact['token_sha256'], session_hash=artifact['session_sha256'],
        actor=artifact['actor_id'], operation_id='runtime-authority:'+state.reference['operation_id'],
        operation_sha256=state.reference['operation_sha256'], state_sha256=digest(state.subject),
        generation=state.snapshot['generation'], expires=a.timestamp(artifact['expires_at_utc']), used=0),
        'authority_consent_confirmation_row')
    return artifact


def _final_mutations(state):
    pending = state.pending
    expected = state.baseline if pending is None else pending['expected']
    require(v._denial_baseline(state.control) == expected, 'authority_consent_protected_state_changed')
    rows = state.control.execute('SELECT * FROM recognition_admin_audit WHERE sequence>? ORDER BY sequence',
                                 (state.audit_sequence,)).fetchall()
    expected_audits = [] if pending is None else [pending['audit']]
    require(canonical([storage._record(row) for row in rows]) == canonical(expected_audits)
            and state.control.total_changes == state.control_changes, 'authority_consent_mutation_integrity')
    if pending is not None:
        _fresh(state, pending['artifact'])


def _append(state, artifact, expected, action, changes):
    storage._json(artifact)  # Bound the complete wrapper, not only its subject.
    head = a._audit_head(state.control)
    audit = dict(action=action, actor=artifact['actor_id'], at_utc=artifact['issued_at_utc'], subject=artifact,
                 previous_sha256=head['body_sha256'] if head else None)
    a._audit(state.control, action, artifact['actor_id'], artifact['issued_at_utc'], artifact)
    require(state.control.total_changes == state.control_changes+changes, 'authority_consent_write_count')
    state.control_changes += changes
    state.pending = dict(artifact=artifact, audit=audit, expected=expected)


def _mode(state, enabled):
    state.ceremony = enabled
    state.control.set_authorizer(state.control_authorizer)


def issue_step_up(config, session_token, code, approval_id, *, primary_token, approval_sha256, reference,
                  activation_sha256, reason):
    """Fresh protected TOTP -> authority-specific intent, never authority."""
    with owner.consent_transaction(config, session_token, approval_id, primary_token=primary_token,
            approval_sha256=approval_sha256, reference=reference, activation_sha256=activation_sha256, reason=reason) as context:
        state = owner._state(context)
        now = v._utc_now()
        proofs = [state.control.execute(f'SELECT expires FROM {table} WHERE token_hash=?', (a.token_hash(token),)).fetchone()[0]
                  for table, token in (('recognition_admin_primary', state.primary), ('recognition_admin_sessions', state.session))]
        expires = min(a.timestamp(now)+auth.RECENT_SECONDS, *proofs)
        require(expires > a.timestamp(now), 'authority_consent_expired')
        raw = secrets.token_urlsafe(32)
        artifact = dict(format=storage.STEP, token_sha256=a.token_hash(raw), subject=state.subject,
            subject_sha256=digest(state.subject), actor_id=state.snapshot['owner_id'],
            primary_sha256=a.token_hash(state.primary), session_sha256=a.token_hash(state.session),
            issued_at_utc=now, expires_at_utc=_time(expires))
        expected = deepcopy(state.baseline)
        mfa = state.control.execute('SELECT * FROM recognition_admin_mfa WHERE actor=?', (state.snapshot['owner_id'],)).fetchone()
        _mode(state, True)
        try:
            auth._code(state.kernel_control, config, {'installation_id':state.snapshot['installation_id']}, mfa, code, now)
            counter = state.control.execute('SELECT last_counter FROM recognition_admin_mfa WHERE actor=?', (state.snapshot['owner_id'],)).fetchone()[0]
            for row in expected['recognition_admin_mfa']:
                if row['actor'] == state.snapshot['owner_id']:
                    row['last_counter'] = counter
            _append(state, artifact, expected, storage.STEP_ACTION, 2)
        finally:
            _mode(state, False)
        result = dict(token=raw, artifact=contract._copy(artifact), artifact_sha256=digest(artifact))
    return result  # Publish only after commit AND connection cleanup.


def begin_confirmation(config, session_token, step_token, approval_id, serialized_intent, **scope):
    require(type(serialized_intent) is str and len(serialized_intent.encode('utf-8')) <= 8192, 'authority_consent_intent_limit')
    intent = load(serialized_intent); contract._json(intent); fields(intent, ('decision','reason','confirm'))
    require(canonical(intent) == serialized_intent and intent['decision'] == 'authorize_runtime_execution'
            and intent['confirm'] is True and intent['reason'] == scope.get('reason'), 'authority_consent_explicit_confirmation_required')
    with owner.consent_transaction(config, session_token, approval_id, **scope) as context:
        state = owner._state(context)
        step = _artifact(state, step_token, storage.STEP)
        _fresh(state, step); _step_unused(state, step)
        raw = secrets.token_urlsafe(32)
        artifact = dict(step, format=storage.CONFIRMATION, token_sha256=a.token_hash(raw),
            step_artifact_sha256=digest(step), decision=intent['decision'], issued_at_utc=v._utc_now())
        expected = deepcopy(state.baseline)
        row = dict(token_hash=artifact['token_sha256'], session_hash=artifact['session_sha256'], actor=artifact['actor_id'],
            operation_id='runtime-authority:'+state.reference['operation_id'], operation_sha256=state.reference['operation_sha256'],
            state_sha256=digest(state.subject), generation=state.snapshot['generation'], expires=a.timestamp(artifact['expires_at_utc']), used=0)
        expected['recognition_admin_confirmations'].append(row)
        expected['recognition_admin_confirmations'].sort(key=lambda x:x['token_hash'])
        _mode(state, True)
        try:
            state.control.execute('INSERT INTO recognition_admin_confirmations VALUES(?,?,?,?,?,?,?,?,?)', tuple(row.values()))
            _append(state, artifact, expected, storage.CONFIRM_ACTION, 2)
        finally:
            _mode(state, False)
        result = dict(token=raw, artifact=contract._copy(artifact), artifact_sha256=digest(artifact))
    return result


class RuntimeAuthorityConsent:
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('authority_consent_requires_validation')

    def __reduce_ex__(self, protocol):
        raise TypeError('authority_consent_cannot_be_restored')

    @property
    def snapshot(self):
        from .runtime_execution_admission import _freeze
        entry = _live(self)
        return _freeze(entry['binding'])

    def take_binding(self):
        """One-use DATA extraction only. Does NOT spend durable confirmation."""
        value = self.snapshot
        _results[self]['used'] = True
        return value


def _live(result):
    entry = _results.get(result) if type(result) is RuntimeAuthorityConsent else None
    require(entry is not None and not entry['used'], 'authority_consent_result_invalid')
    state = owner._state(entry['context'])
    require(canonical(_subject(state)) == canonical(state.subject), 'authority_consent_scope_changed')
    artifact = _confirmation(state, entry['token'])
    require(digest(artifact) == entry['binding']['confirmation_artifact_sha256'], 'authority_consent_result_scope')
    return entry


@contextmanager
def validate_consent(config, session_token, confirmation_token, approval_id, **scope):
    """Live validation only; no standalone durable confirmation consumption."""
    with owner.consent_transaction(config, session_token, approval_id, **scope) as context:
        state = owner._state(context)
        artifact = _confirmation(state, confirmation_token)
        result = object.__new__(RuntimeAuthorityConsent)
        _results[result] = dict(context=context, token=confirmation_token, used=False,
            binding=dict(subject=contract._copy(state.subject), subject_sha256=digest(state.subject),
                step_artifact_sha256=artifact['step_artifact_sha256'], confirmation_artifact_sha256=digest(artifact),
                confirmation_token_sha256=artifact['token_sha256'], issued_at_utc=artifact['issued_at_utc'],
                expires_at_utc=artifact['expires_at_utc']))
        try:
            yield result
        finally:
            _results.pop(result, None)
