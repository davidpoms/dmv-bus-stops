"""4e-15 control-only issuance. Inspection results are never execution authority."""

from contextlib import contextmanager
import os
import sqlite3
import threading
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import administration as a, runtime_validation as v, runtime_scope_validation as shared
from . import runtime_proposal_transaction as p, runtime_activated_owner as activated
from . import runtime_execution_claims as claims, runtime_operation_contract as contract
from . import local_readiness as readiness
from .report_connection import _authorizers as report_authorizers
from .rules import canonical, digest
from .trust import identity, load, require, fields
from . import runtime_authority_consent as consent, runtime_activation_authority_schema as storage
from . import runtime_approval_contract as approvals, runtime_proposal_records as records
from . import dependencies, events, execution, runtime_claim_disposition as disposition
from . import administration_schema, runtime_challenges
from dataclasses import asdict
from copy import deepcopy
from uuid import uuid4


_contexts = WeakKeyDictionary()


class IssuanceContext:
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('authority_consent_requires_owner')

    def __reduce_ex__(self, protocol):
        raise TypeError('authority_consent_context_cannot_be_restored')

    def __getattr__(self, name):
        if name in p._LIFECYCLE or name in ('execute', 'executemany'):
            _state(self).reject()
        raise AttributeError(name)


class _State(activated._State):
    def __init__(self, config):
        super().__init__(config)
        self.issuing = False
        self.pending = None

    def authorize(self, target, action, first, second, *unused):
        if not target and self.issuing:
            if action == sqlite3.SQLITE_INSERT and first in (
                    'recognition_admin_audit', storage.AUTHORITIES, storage.LIFECYCLE):
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_UPDATE and first == 'recognition_admin_confirmations' and second == 'used':
                return sqlite3.SQLITE_OK
        return super().authorize(target, action, first, second, *unused)


def _state(context):
    state = _contexts.get(context) if type(context) is IssuanceContext else None
    a.need(state is not None, 'authority_issuance_context_invalid', 503)
    state.check()
    return state


def _current(state):
    now = v._utc_now()
    scope = v._identity_snapshot(state.config, state.control, state.target, now)
    binding = load(state.control.execute('SELECT body_json FROM recognition_admin_bindings '
                                        'ORDER BY generation DESC LIMIT 1').fetchone()[0])
    activation = readiness.require_activated(state.control, binding)
    a.need(a.timestamp(now) >= a.timestamp(activation['at_utc']), 'administrative_clock_rollback', 503)
    a.need(digest(activation) == state.activation_sha256, 'authority_consent_activation_changed', 503)
    return scope, binding, activation


def _read_parts(context):
    state = _state(context)
    scope, binding, _ = _current(state)
    a.need(scope == state.snapshot and shared._mfa(state.control, scope) == state.mfa_epoch,
           'runtime_validation_changed', 503)
    return state.kernel_control, state.body_target, binding, state.snapshot


def _require_auth_expiry(context, expires, code):
    state = _state(context)
    shared._validate_expiry(expires, code)
    a.need(a.timestamp(v._utc_now()) < expires, code, 401)
    state.auth_expiries.append((expires, code))


def _time(state):
    activated._time(state)  # Pure deadline/clock checks; no owner registration.


def _finish(state):
    from . import runtime_authority_consent as consent
    a.need(state.pid == os.getpid() and state.thread is threading.current_thread()
           and state.ident == threading.get_ident() and state.active and not state.poisoned
           and state.control is state.connections[0] and state.target is state.connections[1]
           and state.control.in_transaction and state.target.in_transaction
           and (state.control_reservation_epoch, state.target_reservation_epoch) == state.epochs,
           'authority_issuance_context_invalid', 503)
    if state.denial is None:
        a.need(canonical(_subject(state)) == canonical(state.subject), 'authority_consent_scope_changed')
        _final_mutations(state)
    else:
        a.need(v._denial_safe(state), 'authority_consent_denial_integrity', 503)
    scope, _, _ = _current(state)
    a.need(scope == state.snapshot and shared._mfa(state.control, scope) == state.mfa_epoch,
           'runtime_validation_changed', 503)
    a.need(state.target.total_changes == state.target_changes
           and state.target.execute('PRAGMA query_only').fetchone()[0] == 1,
           'authority_consent_target_write_forbidden', 503)
    if state.denial is None:
        _time(state)
    else:
        _, now = state.clock.read()
        a.need(now >= state.started_at, 'administrative_clock_rollback', 503)
    state.phase, state.lifecycle, state.commit_attempted = 'FINALIZING', True, True
    try:
        state.control.commit()  # Target reservation retained through resolution.
        a.need(not state.control.in_transaction and state.target.in_transaction,
               'authority_consent_commit_unconfirmed', 503)
        state.control_committed, state.control_resolved, state.phase = True, True, 'COMMITTED'
    except BaseException:
        state.control_committed, state.phase = None, 'OUTCOME_UNKNOWN'
        raise
    finally:
        state.lifecycle = False


@contextmanager
def _transaction(config, session_token, approval_id, *, primary_token,
                        approval_sha256, reference, activation_sha256, reason):
    """Private issuance owner: control reservation then query-only target."""
    from . import runtime_authority_consent as consent
    from .runtime_approval_ceremony import _reference, _reason
    a.need(type(config) is a.LocalAdministration, 'local_administration_required', 503)
    config.paths(); identity(approval_id); _reference(reference); _reason(reason)
    for value in (approval_sha256, activation_sha256):
        contract.profiles._check_sha(value)
    a.need(type(session_token) is str and type(primary_token) is str, 'authority_consent_credentials_required')
    state = _State(config)
    state.session, state.primary, state.approval_id = session_token, primary_token, approval_id
    state.approval_sha256, state.activation_sha256 = approval_sha256, activation_sha256
    state.reference, state.reason = contract._copy(reference), reason
    state.clock = claims._Clock()
    context, report_token = None, None
    with p._owned_connection(config.control, state) as control:
        try:
            control.execute('BEGIN IMMEDIATE')
            v._history(control)
            with p._owned_connection(config.target, state) as target:
                try:
                    state.bind(control, target)
                    target.execute('BEGIN IMMEDIATE')
                    target.execute('PRAGMA query_only=ON')
                    _, state.started_at = state.clock.read()
                    state.snapshot = MappingProxyType(_current(state)[0])
                    state.mfa_epoch = shared._mfa(control, state.snapshot)
                    state.baseline = v._denial_baseline(control)
                    head = a._audit_head(control)
                    state.audit_sequence = head['sequence'] if head else 0
                    state.control_changes, state.target_changes = control.total_changes, target.total_changes
                    state.epochs = (state.control_reservation_epoch, state.target_reservation_epoch)
                    control.set_authorizer(state.control_authorizer)
                    target.set_authorizer(state.target_authorizer)
                    report_token = report_authorizers.set((*report_authorizers.get(), (target, state.target_authorizer)))
                    context = object.__new__(IssuanceContext)
                    state.context, state.phase = context, 'ACTIVE'
                    _contexts[context] = state
                    state.view = shared._register_issuance_view(context)
                    state.subject = _subject(state)
                    yield context
                    state.check()
                    _finish(state)
                except BaseException as error:
                    try:
                        if (state.denial is not None and not state.poisoned and type(error) is a.AdminError
                                and error.code == state.denial and not state.commit_attempted and v._denial_safe(state)):
                            _finish(state)
                        elif state.control_committed is not True:
                            p._rollback(state, control)
                    except BaseException:
                        if not state.control_resolved:
                            p._rollback(state, control)
                        raise
                    raise
                finally:
                    state.active = False
                    if report_token is not None:
                        report_authorizers.reset(report_token)
                    if state.view is not None:
                        shared._issuance_views.pop(state.view, None)
                    if context is not None:
                        _contexts.pop(context, None)
                    state.session = state.primary = state.context = None
        except BaseException:
            if not state.control_resolved:
                p._rollback(state, control)
            raise


def _subject(state):
    return _subject_for_owner(state.context)


from . import runtime_history_validation as history_validation


@history_validation.subject
def _subject_for_owner(context):
    """Fixed exact-owner dispatch; no supplied state/provider/validation callback."""
    from . import runtime_target_entry_owner as metadata
    from . import runtime_finalization as finalization
    if type(context) is IssuanceContext:
        state = _state(context)
    elif type(context) is metadata.MetadataContext:
        state = metadata._state(context)
    elif type(context) is finalization.FinalizationContext:
        state = finalization._state(context)
    else:
        from . import runtime_execution_coordinator as coordinator
        state = coordinator._state(context)
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
    require(not state.control.execute('SELECT 1 FROM recognition_runtime_execution_claims WHERE operation_id=?',
            (op['operation_id'],)).fetchone(), 'authority_consent_preactivation_claim')
    dependency = (finalization._dependencies(state,op['event_id']) if type(context) is finalization.FinalizationContext
                  else dependencies.recheck(state.target,op['event_id']))
    require(dependency == dict(state='READY', reasons=[]),
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
    if type(context) is IssuanceContext:
        assessment = readiness._assess_authority_issuance(view, state.session, state.primary)
    elif type(context) is metadata.MetadataContext:
        assessment = readiness._assess_metadata(view, state.session, state.primary)
    elif type(context) is finalization.FinalizationContext:
        assessment = finalization._readiness(state)
    else:
        assessment = load(readiness._assess_coordinator(view, state.session, state.primary).canonical_json)
    require(assessment['code_ready'] is True and assessment['rehearsal_evidence_present'] is True
            and assessment['activation_state'] == 'ACTIVATED', 'authority_consent_readiness_blocked')
    state.assessed_at_utc = assessment['assessment_at_utc']
    if type(context) is IssuanceContext:
        _, _, activation = _current(state)
    elif type(context) is metadata.MetadataContext:
        _, _, activation = metadata._current(state)
    elif type(context) is finalization.FinalizationContext:
        _, _, activation = finalization._current(state)
    else:
        _, _, activation = coordinator._current(state)
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
    if type(context) is IssuanceContext:
        _read_parts(context); _time(state)
    elif type(context) is metadata.MetadataContext:
        metadata._read_parts(context); metadata._time(state)
    elif type(context) is finalization.FinalizationContext:
        finalization._read_parts(context); finalization._time(state)
    else:
        coordinator._read_parts(context); coordinator._time(state)
    return contract._copy(result)


def _body(state, artifact):
    step = storage._artifact(state.control, artifact['step_artifact_sha256'], storage.STEP_ACTION, storage.STEP)
    consent._fresh(state, step)
    issued = v._utc_now()
    deadlines = [state.control.execute(f'SELECT expires FROM {table} WHERE token_hash=?',
                 (state.subject['authentication'][kind+'_sha256'],)).fetchone()[0]
                 for kind,table in (('primary','recognition_admin_primary'),('session','recognition_admin_sessions'))]
    expires = min(a.timestamp(issued)+120, a.timestamp(step['expires_at_utc']),
                  a.timestamp(artifact['expires_at_utc']), *deadlines)
    require(expires > a.timestamp(issued), 'authority_issuance_expired')
    result = {key:contract._copy(state.subject[key]) for key in storage.SUBJECT_FIELDS if key not in ('readiness','reason')}
    result.update(format=storage.FORMAT, authority_id=str(uuid4()),
        producer_ceremony=dict(step_artifact_sha256=digest(step), confirmation_artifact_sha256=digest(artifact),
            confirmation_token_sha256=artifact['token_sha256'], decision='authorize_runtime_execution', reason=state.reason),
        readiness=dict(assessment_sha256=digest(state.subject['readiness']), assessed_at_utc=state.assessed_at_utc, policy=storage.READINESS),
        issued_at_utc=issued, expires_at_utc=consent._time(expires), lifetime_policy=storage.LIFETIME)
    return storage.validate_authority(result)


def _authority_row(body, audit_sequence):
    scope, ref = body['runtime_target'], body['operation_reference']
    return dict(authority_id=body['authority_id'], operation_id=ref['operation_id'], operation_sha256=ref['operation_sha256'],
        writer_manifest_sha256=ref['writer_manifest_sha256'], installation_id=scope['installation_id'], target_id=scope['target_id'],
        generation=scope['generation'], profile_sha256=scope['runtime_profile_sha256'], owner_id=scope['owner_id'],
        auth_epoch=scope['auth_epoch'], mfa_epoch=scope['mfa_epoch'], activation_sequence=body['activation']['sequence'],
        activation_sha256=body['activation']['event_sha256'], approval_id=body['approval']['approval_id'],
        approval_sha256=body['approval']['approval_sha256'], confirmation_sha256=body['producer_ceremony']['confirmation_token_sha256'],
        issued_at=a.timestamp(body['issued_at_utc']), expires_at=a.timestamp(body['expires_at_utc']),
        body_json=canonical(body), body_sha256=digest(body), audit_sequence=audit_sequence)


def _genesis(body):
    ref = body['operation_reference']
    result = dict(format=storage.EVENT_FORMAT, authority_id=body['authority_id'], authority_sha256=digest(body),
        operation_id=ref['operation_id'], operation_sha256=ref['operation_sha256'], sequence=1, state='AUTHORIZED', kind='AUTHORIZE',
        at_utc=body['issued_at_utc'], previous_sha256=None, entry_sha256=None, seal_sha256=None, receipt_sha256=None,
        actor_id=body['runtime_target']['owner_id'], reason=body['producer_ceremony']['reason'],
        evidence=dict(format=storage.EVIDENCE_FORMAT, authority_id=body['authority_id'], authority_sha256=digest(body)))
    return storage.validate_genesis(result, authority=body)


def _insert(control, table, row):
    control.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", tuple(row.values()))


def _persist(state, artifact):
    """Fixed five-write protocol, never callable SQL from the body context."""
    sequence = state.audit_sequence+2
    expected = deepcopy(state.baseline)
    for row in expected['recognition_admin_confirmations']:
        if row['token_hash'] == artifact['token_sha256']:
            row['used'] = 1
    state.issuing = True
    state.control.set_authorizer(state.control_authorizer)
    try:
        changed = state.control.execute('UPDATE recognition_admin_confirmations SET used=1 WHERE token_hash=? AND used=0',
                                        (artifact['token_sha256'],))
        require(changed.rowcount == 1, 'authority_confirmation_already_consumed')
        body = _body(state, artifact)  # Construct only after the successful CAS.
        now, actor = body['issued_at_utc'], body['runtime_target']['owner_id']
        consumed = dict(format='recognition-runtime-authority-confirmation-consumption-v1', token_sha256=artifact['token_sha256'],
                        artifact_sha256=digest(artifact), subject_sha256=artifact['subject_sha256'])
        old = a._audit_head(state.control)
        first = dict(action=storage.CONSUME_ACTION, actor=actor, at_utc=now, subject=consumed,
                     previous_sha256=old['body_sha256'] if old else None)
        a._audit(state.control, storage.CONSUME_ACTION, actor, now, consumed)
        authority_row = _authority_row(body, sequence)
        _insert(state.control, storage.AUTHORITIES, authority_row)
        event = _genesis(body)  # Exact genesis follows authority insertion.
        event_row = dict(authority_id=body['authority_id'], sequence=1, state='AUTHORIZED', kind='AUTHORIZE',
            at=a.timestamp(body['issued_at_utc']), previous_sha256=None, entry_sha256=None, seal_sha256=None, receipt_sha256=None,
            body_json=canonical(event), body_sha256=digest(event), audit_sequence=sequence)
        _insert(state.control, storage.LIFECYCLE, event_row)
        issued = dict(authority_id=body['authority_id'], authority_sha256=digest(body), event_sequence=1, event_sha256=digest(event))
        second = dict(action=storage.ISSUE_ACTION, actor=actor, at_utc=now, subject=issued, previous_sha256=digest(first))
        a._audit(state.control, storage.ISSUE_ACTION, actor, now, issued)
        state.pending = dict(artifact=artifact, body=body, expected=expected, authority_row=authority_row, event_row=event_row,
                             audits=[first,second])
    finally:
        state.issuing = False
        state.control.set_authorizer(state.control_authorizer)
    state.auth_expiries.append((a.timestamp(body['expires_at_utc']), 'administrative_session_expired_or_revoked'))
    return body


def _final_mutations(state):
    pending = state.pending
    if pending is None:
        require(v._denial_baseline(state.control) == state.baseline
                and state.control.total_changes == state.control_changes, 'authority_inspection_write_forbidden')
        require(not state.control.execute('SELECT 1 FROM recognition_admin_audit WHERE sequence>?',
                                          (state.audit_sequence,)).fetchone(), 'authority_inspection_write_forbidden')
        return
    artifact = pending['artifact']
    consent._fresh(state, artifact)
    step = storage._artifact(state.control, artifact['step_artifact_sha256'], storage.STEP_ACTION, storage.STEP)
    consent._fresh(state, step)
    additional = 0
    if 'finalization_action' in pending:
        from . import runtime_finalization as finalization, runtime_execution_coordinator as coordinator
        coordinator._state(state.context)  # Only exact registered new original producer.
        require(state.outer.finalization_issuer == pending['finalization_action']['issuer_sha256'],
                'finalization_issuer_mismatch')
        finalization._validate_bound_source(state)
        additional = 1
    require(len(pending['audits']) == 2+additional
            and v._denial_baseline(state.control) == pending['expected']
            and state.control.total_changes == state.control_changes+5+additional, 'authority_issuance_protected_state_changed')
    audits = [storage._record(row) for row in state.control.execute('SELECT * FROM recognition_admin_audit WHERE sequence>? ORDER BY sequence',
                                                                  (state.audit_sequence,))]
    require(canonical(audits) == canonical(pending['audits']), 'authority_issuance_audit_mismatch')
    for table, expected in ((storage.AUTHORITIES,pending['authority_row']), (storage.LIFECYCLE,pending['event_row'])):
        rows = state.control.execute(f'SELECT * FROM {table} WHERE authority_id=?', (pending['body']['authority_id'],)).fetchall()
        require(len(rows) == 1 and dict(rows[0]) == expected, 'authority_issuance_graph_mismatch')
    administration_schema.check_control(state.control)  # Full canonical/FK/history/consumption graph.
    storage.validate_authority(pending['body'])


_issued = WeakKeyDictionary()


class IssuedAuthority:
    """Post-commit inspection only; no outer attempt or execution continuation."""
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('authority_requires_confirmed_issuance')

    def __reduce_ex__(self, protocol):
        raise TypeError('issued_authority_cannot_be_restored')

    @property
    def snapshot(self):
        from .runtime_execution_admission import _freeze
        return _freeze(load(_issued_data(self)['json']))

    @property
    def sha256(self):
        return _issued_data(self)['sha256']


def _issued_data(value):
    entry = _issued.get(value) if type(value) is IssuedAuthority else None
    require(entry is not None and entry['pid'] == os.getpid() and entry['thread'] is threading.current_thread(),
            'issued_authority_inspection_invalid')
    _, now = entry['clock'].read()
    require(now < entry['expires'], 'issued_authority_expired')
    return entry


def _existing(state, confirmation_token):
    rows = state.control.execute(f'SELECT * FROM {storage.AUTHORITIES} WHERE operation_id=? OR writer_manifest_sha256=?',
        (state.reference['operation_id'],state.subject['operation_reference']['writer_manifest_sha256'])).fetchall()
    if not rows:
        return None
    require(len(rows) == 1, 'authority_issuance_conflict')
    row = rows[0]
    body = storage.parse_authority(row['body_json'], authority_sha256=row['body_sha256'])
    require(row['operation_id'] == state.reference['operation_id'] and row['confirmation_sha256'] == a.token_hash(confirmation_token),
            'authority_issuance_conflict')
    expected = {key:body[key] for key in storage.SUBJECT_FIELDS if key not in ('readiness','reason')}
    # Resolve the immutable original subject, including normalized readiness.
    artifact = storage._artifact(state.control, body['producer_ceremony']['confirmation_artifact_sha256'], storage.CONFIRM_ACTION, storage.CONFIRMATION)
    expected.update(readiness=artifact['subject']['readiness'], reason=body['producer_ceremony']['reason'])
    require(canonical(expected) == canonical(state.subject), 'authority_issuance_conflict')
    storage.check_rows(state.control)
    return dict(status='PRESENT_EXACT', authority_id=row['authority_id'], authority_sha256=row['body_sha256'],
                operation_id=row['operation_id'], retry_authorized=False, execution_authority=False)


def issue(config, session_token, confirmation_token, approval_id, **scope):
    """Issue once. Identical duplicates return inspection DATA, never a new object."""
    with _transaction(config, session_token, approval_id, **scope) as context:
        state = _state(context)
        existing = _existing(state, confirmation_token)
        if existing is None:
            artifact = consent._confirmation(state, confirmation_token)
            body = _persist(state, artifact)
            serialized, sha256 = canonical(body), digest(body)
    # No publication before confirmed manager commit AND both cleanups.
    if existing is not None:
        return MappingProxyType(existing)
    result = object.__new__(IssuedAuthority)
    _issued[result] = dict(pid=os.getpid(), thread=threading.current_thread(), clock=state.clock,
                          expires=a.timestamp(body['expires_at_utc']), json=serialized, sha256=sha256)
    return result


def _issue_for_coordinator(context, confirmation_token):
    """Stage one original private issuance; manager commits and publishes later."""
    from . import runtime_execution_coordinator as coordinator
    state = coordinator._state(context)
    require(state.issuance_phase and state.pending is None and state.outer.notice is None,
            'coordinator_issuance_not_original')
    coordinator._evaluate(state)
    require(not state.control.execute(f'SELECT 1 FROM {storage.AUTHORITIES} WHERE operation_id=? OR writer_manifest_sha256=?',
        (state.reference['operation_id'], state.subject['operation_reference']['writer_manifest_sha256'])).fetchone(),
        'coordinator_authority_already_exists')
    artifact = consent._confirmation(state, confirmation_token)
    from . import runtime_issuance_schema_inventory as preparation
    preparation._mint(context, artifact)
    _persist(state, artifact)
    if state.outer.finalization_issuer is not None:
        from . import runtime_finalization as finalization
        finalization._bind_source(state)
    # The private pending state is never returned as a public inspection object.
    state.outer.notice = MappingProxyType(dict(state=state, phase_id=state.phase_id,
        connections=state.connections, epochs=state.epochs, authority_sha256=digest(state.pending['body'])))


def inspect_issuance(config, *, operation_id, operation_sha256, confirmation_sha256):
    """Trusted deployment-side mode=ro snapshot inspection; never retry/adopt."""
    require(type(config) is a.LocalAdministration, 'local_administration_required')
    config.paths(); identity(operation_id)
    for value in (operation_sha256,confirmation_sha256): contract.profiles._check_sha(value)
    result = dict(operation_id=operation_id, retry_authorized=False, execution_authority=False)
    try:
        with a.connect(config.control) as control:
            control.execute('BEGIN')
            administration_schema.check_control(control)
            binding = runtime_challenges._deployment_binding(control)
            require(asdict(a.target_identity(control)) == binding['control_identity'], 'control_identity_mismatch')
            require(str(config.target.resolve()) == binding['target']['observation']['database'], 'target_path_mismatch')
            rows = control.execute(f'SELECT * FROM {storage.AUTHORITIES} WHERE operation_id=? OR confirmation_sha256=?',
                                   (operation_id,confirmation_sha256)).fetchall()
            used = control.execute('SELECT used FROM recognition_admin_confirmations WHERE token_hash=?', (confirmation_sha256,)).fetchone()
            consumed = any(storage._record(row)['subject'].get('token_sha256') == confirmation_sha256
                           for row in storage._rows(control, storage.CONSUME_ACTION))
            if not rows:
                return dict(result,status='UNKNOWN' if consumed or used and used[0] else 'ABSENT_AT_SNAPSHOT')
            row = rows[0]
            exact = len(rows)==1 and row['operation_id']==operation_id and row['operation_sha256']==operation_sha256 and row['confirmation_sha256']==confirmation_sha256
            return dict(result,status='PRESENT_EXACT' if exact else 'PRESENT_CONFLICT',
                        authority_id=row['authority_id'],authority_sha256=row['body_sha256'])
    except (ValueError,OSError,sqlite3.Error,KeyError,TypeError):
        return dict(result,status='UNKNOWN')

