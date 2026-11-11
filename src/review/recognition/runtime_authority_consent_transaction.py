"""Dedicated activated consent owner; never authority issuance or target writes."""

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
from .trust import identity, load


_contexts = WeakKeyDictionary()


class ConsentContext:
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
        self.ceremony = False
        self.pending = None

    def authorize(self, target, action, first, second, *unused):
        if not target and self.ceremony:
            if action == sqlite3.SQLITE_INSERT and first in (
                    'recognition_admin_audit', 'recognition_admin_confirmations'):
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_UPDATE and first == 'recognition_admin_mfa' and second == 'last_counter':
                return sqlite3.SQLITE_OK
        return super().authorize(target, action, first, second, *unused)


def _state(context):
    state = _contexts.get(context) if type(context) is ConsentContext else None
    a.need(state is not None, 'authority_consent_context_invalid', 503)
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
           'authority_consent_context_invalid', 503)
    if state.denial is None:
        a.need(canonical(consent._subject(state)) == canonical(state.subject), 'authority_consent_scope_changed')
        consent._final_mutations(state)
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
def consent_transaction(config, session_token, approval_id, *, primary_token,
                        approval_sha256, reference, activation_sha256, reason):
    """Manager-only consent writes; target is reserved/query-only until commit."""
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
                    context = object.__new__(ConsentContext)
                    state.context, state.phase = context, 'ACTIVE'
                    _contexts[context] = state
                    state.view = shared._register_consent_view(context)
                    state.subject = consent._subject(state)
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
                        shared._consent_views.pop(state.view, None)
                    if context is not None:
                        _contexts.pop(context, None)
                    state.session = state.primary = state.context = None
        except BaseException:
            if not state.control_resolved:
                p._rollback(state, control)
            raise
