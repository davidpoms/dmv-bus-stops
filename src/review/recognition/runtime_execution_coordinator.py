"""Original private issuance and inert attempt creation. No writer authority.

Outer provenance survives expected manager cleanup, never a borrowed SQL phase.
Admission/creation repeat current checks under fresh ordered reservations.
Created-attempt snapshots are historical inspection, not current admission.
"""

from contextlib import contextmanager
import os
import sqlite3
import threading
from types import MappingProxyType
from weakref import WeakKeyDictionary
from uuid import uuid4

from . import administration as a, runtime_validation as v, runtime_scope_validation as shared
from . import runtime_proposal_transaction as p, runtime_activated_owner as activated
from . import runtime_admission_validation as admission, runtime_activation_authority_issuance as issuer
from . import runtime_activation_authority_schema as storage, runtime_execution_attempt_schema as attempts
from . import runtime_execution_claims as claims, runtime_operation_contract as contract
from .report_connection import _authorizers as report_authorizers
from .rules import canonical, digest
from .trust import identity, load, require
from . import runtime_attempt_schema_manifest_observation as schema_observation
from . import runtime_issuance_schema_inventory as issuance_inventory
from . import runtime_history_validation as history_validation


_coordinators = WeakKeyDictionary()
_admission_contexts = WeakKeyDictionary()
_continuations = WeakKeyDictionary()
_attempt_results = WeakKeyDictionary()
_FORBIDDEN = p._LIFECYCLE | frozenset(('control', 'target', 'execute', 'executemany',
    'writer', 'execute_operation', 'activate', 'take_handoff', 'continuation'))


class CoordinatorContext:
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('coordinator_requires_original_owner')

    def __reduce_ex__(self, protocol):
        raise TypeError('coordinator_cannot_be_restored')

    def create_attempt(self):
        """Spend original provenance once; return no execution/write authority."""
        return _create_attempt(self)

    def __getattr__(self, name):
        if name in _FORBIDDEN:
            _outer(self).reject()
        raise AttributeError(name)

    @property
    def snapshot(self):
        """Freshly checked immutable inspection DATA, never a continuation export."""
        outer = _outer(self)
        try:
            _continuation_entry(outer)
            with _phase(outer, issuance=False):
                pass
            from .runtime_execution_admission import _freeze
            return _freeze(dict(authority=load(outer.authority_json), authority_sha256=outer.authority_sha256,
                                execution_authority=False, retry_authorized=False))
        except BaseException:
            outer.poisoned = True
            raise


class CoordinatorAdmissionContext:
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('coordinator_admission_requires_owner')

    def __reduce_ex__(self, protocol):
        raise TypeError('coordinator_admission_cannot_be_restored')

    def __getattr__(self, name):
        if name in _FORBIDDEN:
            _state(self).reject()
        raise AttributeError(name)


class _Continuation:
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('continuation_requires_original_issuance')

    def __reduce_ex__(self, protocol):
        raise TypeError('continuation_cannot_be_restored')


class CreatedAttempt:
    """Opaque original-owner result, not a writer or a resumable credential."""
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('attempt_requires_confirmed_coordinator_creation')

    def __reduce_ex__(self, protocol):
        raise TypeError('attempt_result_cannot_be_restored')

    def __getattr__(self, name):
        if name in _FORBIDDEN:
            _attempt_entry(self)['outer'].reject()
        raise AttributeError(name)

    @property
    def snapshot(self):
        from .runtime_execution_admission import _freeze
        return _freeze(load(_attempt_entry(self)['inspection_json']))


def _attempt_entry(result):
    entry = _attempt_results.get(result) if type(result) is CreatedAttempt else None
    require(entry is not None, 'coordinator_attempt_result_invalid')
    outer = entry['outer']
    _require_outer(outer)
    require(outer.attempt_result is result and outer.attempt_started
            and entry['context'] is outer.context and entry['continuation'] is outer.continuation
            and entry['authority_json'] == outer.authority_json
            and entry['authority_sha256'] == outer.authority_sha256, 'coordinator_attempt_result_invalid')
    _continuation_entry(outer)
    return entry


class _Outer:
    def __init__(self, context, config, session, primary, approval_id, scope):
        self.context, self.config = context, config
        self.pid, self.thread, self.ident = os.getpid(), threading.current_thread(), threading.get_ident()
        self.session, self.primary, self.approval_id = session, primary, approval_id
        self.approval_sha256, self.reference = scope['approval_sha256'], contract._copy(scope['reference'])
        self.activation_sha256, self.reason = scope['activation_sha256'], scope['reason']
        self.clock = claims._Clock()
        _, self.started_at = self.clock.read()
        self.auth_expiries = []
        self.active, self.poisoned, self.phase = True, False, 'STARTING'
        self.current_phase = self.notice = self.continuation = self.subject = None
        self.origin_phase = None
        self.authority_json = self.authority_sha256 = None
        self.attempt_started, self.attempt_result, self.attempt_phase = False, None, None

    def check(self, *, deadlines=True):
        valid = (self.active and not self.poisoned and self.pid == os.getpid()
                 and self.thread is threading.current_thread() and self.ident == threading.get_ident()
                 and _coordinators.get(self.context) is self
                 and self.phase in ('STARTING', 'IN_PHASE', 'CONTINUABLE'))
        if not valid:
            self.reject()
        try:
            _, now = self.clock.read()
            require(now >= self.started_at, 'administrative_clock_rollback')
            if deadlines:
                for expires, code in self.auth_expiries:
                    a.need(now < expires, code, 401)
        except BaseException:
            self.poisoned = True
            raise

    def reject(self):
        self.poisoned = True
        raise a.AdminError('coordinator_context_invalid', 503)


class _State(activated._State):
    def __init__(self, outer, issuance):
        super().__init__(outer.config)
        self.outer, self.issuance_phase = outer, issuance
        self.phase_id = object()
        self.session, self.primary, self.approval_id = outer.session, outer.primary, outer.approval_id
        self.approval_sha256, self.reference = outer.approval_sha256, contract._copy(outer.reference)
        self.activation_sha256, self.reason = outer.activation_sha256, outer.reason
        self.clock, self.auth_expiries = outer.clock, outer.auth_expiries
        self.issuing, self.pending, self.cleaned = False, None, False
        self.admission_view = None
        self.attempt_writing, self.attempt_pending = False, None
        self.schema_observation = self.schema_facts = None
        self.issuance_inventory = None
        self.finalization_writing = False

    def check(self):
        _require_outer(self.outer)
        if self.outer.current_phase is not self or self.outer.phase != 'IN_PHASE':
            self.reject()
        super().check()

    def reject(self):
        self.outer.poisoned = True
        super().reject()

    def authorize(self, target, action, first, second, *unused):
        history_validation.note(self,action,first,second)
        if (not target and self.finalization_writing and self.issuance_phase
                and self.outer.finalization_issuer is not None
                and action == sqlite3.SQLITE_INSERT and first == 'recognition_admin_audit'):
            # Z15's observation proves the original five-write protocol only.
            # A new prospective eligibility audit requires the unchanged full
            # fresh path, not a relaxed observation mutation count.
            issuance_inventory._discard(self)
            return sqlite3.SQLITE_OK
        if self.issuance_inventory is not None:
            fixed = (not target and self.issuing and self.issuance_phase and (
                action == sqlite3.SQLITE_INSERT and first in ('recognition_admin_audit', storage.AUTHORITIES, storage.LIFECYCLE)
                or action == sqlite3.SQLITE_UPDATE and first == 'recognition_admin_confirmations' and second == 'used'))
            if ((action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE) and not fixed)
                    or action in (sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT)
                    or action == sqlite3.SQLITE_PRAGMA and second is not None and first.lower() in (
                        'query_only', 'foreign_keys', 'journal_mode', 'synchronous', 'application_id', 'user_version')):
                issuance_inventory._discard(self)
        if self.schema_observation is not None:
            fixed_insert = (not target and self.attempt_writing and not self.issuance_phase
                            and action == sqlite3.SQLITE_INSERT
                            and first in (attempts.ATTEMPTS,attempts.HISTORY,'recognition_admin_audit'))
            if ((action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) and not fixed_insert)
                    or action in (sqlite3.SQLITE_TRANSACTION,sqlite3.SQLITE_SAVEPOINT)
                    or (action == sqlite3.SQLITE_PRAGMA and second is not None
                        and first.lower() in ('query_only','foreign_keys','journal_mode','synchronous',
                                              'application_id','user_version'))):
                # Even a zero-row denial UPDATE invalidates continuity. Keep the
                # existing authorization decision and fresh denial path intact.
                self.schema_observation = self.schema_facts = None
        if (not target and self.attempt_writing and not self.issuance_phase
                and action == sqlite3.SQLITE_INSERT
                and first in (attempts.ATTEMPTS, attempts.HISTORY, 'recognition_admin_audit')):
            return sqlite3.SQLITE_OK
        if not target and self.issuing and self.issuance_phase:
            if action == sqlite3.SQLITE_INSERT and first in ('recognition_admin_audit', storage.AUTHORITIES, storage.LIFECYCLE):
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_UPDATE and first == 'recognition_admin_confirmations' and second == 'used':
                return sqlite3.SQLITE_OK
        return super().authorize(target, action, first, second, *unused)


def _require_outer(outer, *, deadlines=True):
    """Never invoke an incoming object's supplied ownership/check callback."""
    require(type(outer) is _Outer, 'coordinator_context_invalid')
    context = getattr(outer, 'context', None)
    if type(context) is not CoordinatorContext or _coordinators.get(context) is not outer:
        outer.poisoned = True
        raise a.AdminError('coordinator_context_invalid', 503)
    _Outer.check(outer, deadlines=deadlines)


def _outer(context):
    outer = _coordinators.get(context) if type(context) is CoordinatorContext else None
    a.need(outer is not None, 'coordinator_context_invalid', 503)
    try:
        _require_outer(outer)
    except BaseException:
        outer.poisoned = True
        raise
    return outer


def _state(context):
    state = _admission_contexts.get(context) if type(context) is CoordinatorAdmissionContext else None
    a.need(type(state) is _State, 'coordinator_admission_context_invalid', 503)
    _State.check(state)
    return state


def _current(state):
    # Existing pure identity/activation kernel, no issuer registration.
    return issuer._current(state)


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
    _require_outer(state.outer)
    activated._time(state)


def _continuation_entry(outer):
    _require_outer(outer)
    entry = _continuations.get(outer.continuation) if type(outer.continuation) is _Continuation else None
    require(entry is not None and entry['outer'] is outer and entry['context'] is outer.context
            and entry['issuance_phase'] is outer.origin_phase and outer.origin_phase is not None
            and entry['authority_json'] == outer.authority_json
            and entry['authority_sha256'] == outer.authority_sha256, 'coordinator_continuation_invalid')
    return entry


@history_validation.evaluate
def _evaluate(state):
    state.check()
    # Existing admission kernel regenerates the whole manifest; no copied validators.
    admission._collect(state.admission_view, state.session, state.primary, state.approval_id,
                       state.approval_sha256, state.reference)
    subject = issuer._subject_for_owner(state.context)
    if state.outer.subject is None:
        state.outer.subject = contract._copy(subject)
    require(canonical(subject) == canonical(state.outer.subject), 'coordinator_scope_changed')
    state.subject = contract._copy(subject)
    if attempts.present(state.control):
        # Exact schema/row validation is already enforced by _history(). No adoption.
        if state.attempt_pending is None:
            require(not state.control.execute(f'SELECT 1 FROM {attempts.ATTEMPTS}').fetchone(),
                    'coordinator_incomplete_attempt_exists')
        else:
            _check_attempt_graph(state)
    if not state.issuance_phase:
        _continuation_entry(state.outer)
        body = load(state.outer.authority_json)
        row = state.control.execute(f'SELECT * FROM {storage.AUTHORITIES} WHERE authority_id=?', (body['authority_id'],)).fetchone()
        require(row is not None and row['body_json'] == state.outer.authority_json
                and row['body_sha256'] == state.outer.authority_sha256, 'coordinator_authority_changed')
        storage.check_rows(state.control)
        artifact = storage._artifact(state.control, body['producer_ceremony']['confirmation_artifact_sha256'],
                                     storage.CONFIRM_ACTION, storage.CONFIRMATION)
        issuer.consent._fresh(state, artifact)
        step = storage._artifact(state.control, artifact['step_artifact_sha256'], storage.STEP_ACTION, storage.STEP)
        issuer.consent._fresh(state, step)
        require(canonical({key:body[key] for key in attempts.SCOPE_FIELDS})
                == canonical({key:subject[key] for key in attempts.SCOPE_FIELDS}), 'coordinator_authority_scope_changed')
        require(a.timestamp(body['issued_at_utc']) <= a.timestamp(v._utc_now()) < a.timestamp(body['expires_at_utc']),
                'coordinator_authority_expired')
    _read_parts(state.context)
    _time(state)


def _finish(state):
    with issuance_inventory._final_validation(state), schema_observation._final_validation(state):
        _finish_reserved(state)


def _finish_reserved(state):
    # Denials seal body access; their established safe reductions still finalize.
    _require_outer(state.outer, deadlines=state.denial is None)
    require(state.active and not state.poisoned and state.pid == os.getpid()
            and state.thread is threading.current_thread() and state.ident == threading.get_ident()
            and state.control is state.connections[0] and state.target is state.connections[1]
            and state.control.in_transaction and state.target.in_transaction
            and (state.control_reservation_epoch, state.target_reservation_epoch) == state.epochs,
            'coordinator_reservation_invalid')
    if state.denial is None:
        _evaluate(state)
        if state.attempt_pending is None:
            issuer._final_mutations(state)
        else:
            _final_attempt(state)
    else:
        require(v._denial_safe(state), 'coordinator_denial_integrity')
    scope, _, _ = _current(state)
    require(scope == state.snapshot and shared._mfa(state.control, scope) == state.mfa_epoch,
            'runtime_validation_changed')
    require(state.target.total_changes == state.target_changes and state.target.execute('PRAGMA query_only').fetchone()[0] == 1,
            'coordinator_target_write_forbidden')
    if state.denial is None:
        _time(state)
    else:
        _, now = state.clock.read()
        require(now >= state.started_at, 'administrative_clock_rollback')
    state.phase, state.lifecycle, state.commit_attempted = 'FINALIZING', True, True
    state.control_reservation_epoch += 1  # Explicit invalidation, including cached SQL.
    try:
        state.control.commit()
        require(not state.control.in_transaction and state.target.in_transaction, 'coordinator_commit_unconfirmed')
        state.control_committed, state.control_resolved, state.phase = True, True, 'COMMITTED'
    except BaseException:
        state.control_committed, state.phase = None, 'OUTCOME_UNKNOWN'
        raise
    finally:
        state.lifecycle = False


@contextmanager
def _phase(outer, *, issuance):
    _require_outer(outer)
    require(outer.current_phase is None, 'coordinator_phase_already_active')
    if not issuance:
        _continuation_entry(outer)
    state = _State(outer, issuance)
    outer.current_phase, outer.phase = state, 'IN_PHASE'
    context, report_token = None, None
    try:
        with p._owned_connection(outer.config.control, state) as control:
            try:
                control.execute('BEGIN IMMEDIATE')
                v._history(control)
                with p._owned_connection(outer.config.target, state) as target:
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
                        state.epochs = state.control_reservation_epoch, state.target_reservation_epoch
                        control.set_authorizer(state.control_authorizer)
                        target.set_authorizer(state.target_authorizer)
                        report_token = report_authorizers.set((*report_authorizers.get(), (target, state.target_authorizer)))
                        context = object.__new__(CoordinatorAdmissionContext)
                        state.context, state.phase = context, 'ACTIVE'
                        _admission_contexts[context] = state
                        state.view = shared._register_coordinator_view(context)
                        state.admission_view = admission.coordinator_read_view(context)
                        _evaluate(state)
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
                        issuance_inventory._discard(state)
                        state.schema_observation = state.schema_facts = None
                        state.active = False
                        state.control_reservation_epoch += 1
                        state.target_reservation_epoch += 1
                        if report_token is not None:
                            report_authorizers.reset(report_token)
                        if state.view is not None:
                            shared._coordinator_views.pop(state.view, None)
                        if state.admission_view is not None:
                            admission._views.pop(state.admission_view, None)
                        if context is not None:
                            _admission_contexts.pop(context, None)
                        state.session = state.primary = state.context = None
            except BaseException:
                if not state.control_resolved:
                    p._rollback(state, control)
                raise
        state.cleaned = True
        state.cleanup_epochs = state.control_reservation_epoch, state.target_reservation_epoch
    except BaseException:
        outer.poisoned = True
        raise
    finally:
        outer.current_phase = None
        outer.phase = 'CONTINUABLE' if not outer.poisoned else 'POISONED'


def _promote(outer):
    """One original notice, after confirmed commit AND both connection cleanups."""
    _require_outer(outer)
    notice = outer.notice
    require(type(notice) is MappingProxyType, 'coordinator_issuance_unconfirmed')
    state = notice['state']
    require(state.outer is outer and state.issuance_phase and state.cleaned
            and state.control_committed is True and state.control_resolved and not state.active
            and state.phase == 'COMMITTED' and state.phase_id is notice['phase_id']
            and state.control is notice['connections'][0] and state.target is notice['connections'][1]
            and state.epochs == notice['epochs']
            and state.cleanup_epochs == (state.control_reservation_epoch, state.target_reservation_epoch)
            and state.pending is not None and outer.continuation is None, 'coordinator_issuance_unconfirmed')
    body = state.pending['body']
    require(digest(body) == notice['authority_sha256'], 'coordinator_authority_changed')
    outer.authority_json, outer.authority_sha256 = canonical(body), digest(body)
    require(canonical(state.subject) == canonical(outer.subject), 'coordinator_scope_changed')
    result = object.__new__(_Continuation)
    outer.origin_phase = state.phase_id
    _continuations[result] = dict(outer=outer, context=outer.context, authority_json=outer.authority_json,
                                 authority_sha256=outer.authority_sha256, issuance_phase=state.phase_id)
    outer.continuation, outer.notice = result, None


def _check_attempt_graph(state):
    """Only this phase's exact three-write graph, never a selected-row skip."""
    _attempt_state(state)
    pending = state.attempt_pending
    require(pending is not None and state.pending is None and not state.issuance_phase,
            'coordinator_attempt_phase_invalid')
    for table, expected in ((attempts.ATTEMPTS, pending['row']), (attempts.HISTORY, pending['history'])):
        rows = state.control.execute(f'SELECT * FROM {table}').fetchall()
        require(len(rows) == 1 and dict(rows[0]) == expected, 'coordinator_attempt_graph_changed')
    attempts.check_rows(state.control)
    attempts.validate_binding(state.control, pending['body'],
        expected_scope={key:state.subject[key] for key in attempts.SCOPE_FIELDS})
    attempts.validate_expiry(pending['body'], now=v._utc_now())


def _final_attempt(state):
    _check_attempt_graph(state)
    require(v._denial_baseline(state.control) == state.baseline
            and state.control.total_changes == state.control_changes+3, 'coordinator_attempt_protected_state_changed')
    rows = state.control.execute('SELECT * FROM recognition_admin_audit WHERE sequence>? ORDER BY sequence',
                                 (state.audit_sequence,)).fetchall()
    require(len(rows) == 1 and canonical(storage._record(rows[0])) == canonical(state.attempt_pending['audit']),
            'coordinator_attempt_audit_changed')
    v._history(state.control)


def _attempt_state(state):
    require(type(state) is _State, 'coordinator_attempt_phase_invalid')
    require(_state(state.context) is state and state.outer.attempt_phase is state
            and state.outer.attempt_started and not state.issuance_phase, 'coordinator_attempt_phase_invalid')


def _persist_attempt(state):
    """Fixed inserts only, under the original manager's fresh reservations."""
    _attempt_state(state)
    require(not state.issuance_phase and state.attempt_pending is None and state.pending is None,
            'coordinator_attempt_phase_invalid')
    require(attempts.present(state.control), 'runtime_attempt_storage_not_installed')
    _continuation_entry(state.outer)
    _evaluate(state)
    schema_observation._mint(state)
    authority = load(state.outer.authority_json)
    body = attempts.validate_attempt(dict(format=attempts.FORMAT, attempt_id=str(uuid4()),
        authority_id=authority['authority_id'], authority_sha256=state.outer.authority_sha256,
        created_at_utc=v._utc_now(), expires_at_utc=authority['expires_at_utc']))
    attempts.validate_binding(state.control, body,
        expected_scope={key:state.subject[key] for key in attempts.SCOPE_FIELDS})
    attempts.validate_expiry(body, now=v._utc_now())
    sequence = state.audit_sequence+1
    row = dict(attempt_id=body['attempt_id'], authority_id=body['authority_id'], authority_sha256=body['authority_sha256'],
        created_at=a.timestamp(body['created_at_utc']), expires_at=a.timestamp(body['expires_at_utc']),
        body_json=canonical(body), body_sha256=digest(body), audit_sequence=sequence)
    event = attempts.validate_created(state.control, dict(format=attempts.EVENT_FORMAT, attempt_id=body['attempt_id'],
        attempt_sha256=digest(body), sequence=1, state='ATTEMPT_CREATED', at_utc=body['created_at_utc'],
        previous_sha256=None, actor_id=authority['runtime_target']['owner_id'],
        reason=authority['producer_ceremony']['reason']), attempt=body)
    history = dict(attempt_id=body['attempt_id'], sequence=1, state='ATTEMPT_CREATED', at=row['created_at'],
        previous_sha256=None, body_json=canonical(event), body_sha256=digest(event), audit_sequence=sequence)
    subject = dict(attempt_id=body['attempt_id'], attempt_sha256=digest(body), event_sequence=1, event_sha256=digest(event))
    head = a._audit_head(state.control)
    audit = dict(action=attempts.CREATE_ACTION, actor=event['actor_id'], at_utc=body['created_at_utc'],
        subject=subject, previous_sha256=head['body_sha256'] if head else None)
    state.attempt_writing = True
    state.control.set_authorizer(state.control_authorizer)
    try:
        issuer._insert(state.control, attempts.ATTEMPTS, row)
        issuer._insert(state.control, attempts.HISTORY, history)
        a._audit(state.control, attempts.CREATE_ACTION, event['actor_id'], body['created_at_utc'], subject)
        state.attempt_pending = dict(body=body, row=row, history=history, audit=audit)
    finally:
        state.attempt_writing = False
        state.control.set_authorizer(state.control_authorizer)


def _publish_attempt(outer, state):
    _require_outer(outer)
    _continuation_entry(outer)
    require(type(state) is _State and state.outer is outer and not state.issuance_phase
            and outer.attempt_phase is state
            and state.cleaned and state.control_committed is True and state.control_resolved
            and not state.active and state.phase == 'COMMITTED' and state.attempt_pending is not None
            and outer.attempt_result is None and outer.attempt_started
            and state.control is state.connections[0] and state.target is state.connections[1]
            and state.cleanup_epochs == (state.control_reservation_epoch, state.target_reservation_epoch),
            'coordinator_attempt_commit_unconfirmed')
    pending = state.attempt_pending
    require(pending['body']['authority_sha256'] == outer.authority_sha256
            and pending['body']['authority_id'] == load(outer.authority_json)['authority_id']
            and digest(pending['body']) == pending['row']['body_sha256'], 'coordinator_attempt_scope_changed')
    inspection = dict(state='ATTEMPT_CREATED', historical_only=True, attempt=pending['body'],
        attempt_sha256=pending['row']['body_sha256'], event_sha256=pending['history']['body_sha256'],
        execution_authority=False, retry_authorized=False)
    result = object.__new__(CreatedAttempt)
    outer.attempt_result = result
    _attempt_results[result] = dict(outer=outer, context=outer.context, continuation=outer.continuation,
        authority_json=outer.authority_json, authority_sha256=outer.authority_sha256,
        inspection_json=canonical(inspection))
    return result


def _create_attempt(context):
    outer = _outer(context)
    try:
        _continuation_entry(outer)
        require(not outer.attempt_started, 'coordinator_continuation_already_spent')
        outer.attempt_started = True  # Failed/uncertain use cannot be retried.
        with _phase(outer, issuance=False) as phase:
            state = _state(phase)
            outer.attempt_phase = state
            _persist_attempt(state)
        return _publish_attempt(outer, state)
    except BaseException:
        outer.poisoned = True
        if outer.attempt_result is not None:
            _attempt_results.pop(outer.attempt_result, None)
            outer.attempt_result = None
        raise


@contextmanager
def coordinator(config, session_token, confirmation_token, approval_id, *, primary_token,
                approval_sha256, reference, activation_sha256, reason, finalization_issuer=None):
    """Fresh private issuance within its original owner; optional inert attempt.

    No authority lookup/import/adoption input. No writer API is present.
    Publication/cleanup uncertainty poisons the lifetime; inspect durable state.
    """
    from .runtime_approval_ceremony import _reference, _reason
    require(type(config) is a.LocalAdministration, 'local_administration_required')
    config.paths(); identity(approval_id); _reference(reference); _reason(reason)
    for value in (approval_sha256, activation_sha256):
        contract.profiles._check_sha(value)
    require(all(type(token) is str for token in (session_token, primary_token, confirmation_token)),
            'coordinator_credentials_required')
    context = object.__new__(CoordinatorContext)
    outer = _Outer(context, config, session_token, primary_token, approval_id,
                   dict(approval_sha256=approval_sha256, reference=reference, activation_sha256=activation_sha256, reason=reason))
    if finalization_issuer is not None:
        contract.profiles._check_sha(finalization_issuer)
        from . import runtime_finalization as finalization
        finalization._require_entitlement_owner(config,finalization_issuer,session_token,primary_token)
    outer.finalization_issuer = finalization_issuer
    _coordinators[context] = outer  # Original owner exists before any issuance.
    continuation = None
    try:
        if finalization_issuer is not None:
            finalization._claim_issuer(outer,confirmation_token)
        with _phase(outer, issuance=True) as phase:
            issuer._issue_for_coordinator(phase, confirmation_token)
        _promote(outer)
        continuation = outer.continuation
        yield context
        _outer(context)
    except BaseException:
        outer.poisoned = True
        raise
    finally:
        outer.active, outer.phase = False, 'CLOSED'
        if continuation is not None:
            _continuations.pop(continuation, None)
        if outer.continuation is not None:
            _continuations.pop(outer.continuation, None)
        outer.notice = outer.continuation = outer.session = outer.primary = None
        if outer.attempt_result is not None:
            _attempt_results.pop(outer.attempt_result, None)
        outer.attempt_result = None
        outer.attempt_phase = None
        _coordinators.pop(context, None)
