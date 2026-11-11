"""4e-6: separately owned activated observation, never execution authority.

Success is read-only. Existing authenticated denial reductions may commit on
control only, with the target reservation retained until control resolves.
Private reflection/host compromise is outside the existing integrity model.
"""

from contextlib import contextmanager
import os
import sqlite3
import threading
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import administration as a, runtime_validation as v, runtime_scope_validation as shared
from . import runtime_proposal_transaction as p, local_readiness as readiness
from . import runtime_approval_contract as approvals, runtime_operation_contract as contract
from . import runtime_claim_disposition as disposition, runtime_execution_claims as claims
from .report_connection import _authorizers as report_authorizers
from .rules import digest
from .trust import identity, load


_contexts = WeakKeyDictionary()


class ActivatedAdmission:
    """Opaque live evidence only. No handles, SQL, tokens or write methods."""

    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('activated_admission_requires_owner')

    @property
    def snapshot(self):
        from .runtime_execution_admission import _freeze
        state = _state(self)
        _read_parts(self)
        _time(state)
        return _freeze(state.result)

    def __reduce_ex__(self, protocol):
        raise TypeError('activated_admission_cannot_be_restored')

    def __getattr__(self, name):
        if name in p._LIFECYCLE or name in ('execute', 'executemany'):
            _state(self).reject()
        raise AttributeError(name)


class _State(p._State):
    def authorize(self, target, action, first, second, *unused):
        if (self.persistence is not None or self.persistence_write is not None
                or target and action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE)):
            self.poisoned = True
            return sqlite3.SQLITE_DENY
        return super().authorize(target, action, first, second, *unused)

    def check(self):
        if (self.control is not self.connections[0] or self.target is not self.connections[1]
                or (self.control_reservation_epoch, self.target_reservation_epoch) != self.epochs):
            self.reject()
        super().check()
        if self.target.execute('PRAGMA query_only').fetchone()[0] != 1:
            self.reject()


def _state(context):
    state = _contexts.get(context) if type(context) is ActivatedAdmission else None
    a.need(state is not None, 'activated_context_invalid', 503)
    state.check()
    return state


def _current(state):
    now = v._utc_now()
    scope = v._identity_snapshot(state.config, state.control, state.target, now)
    binding = load(state.control.execute('SELECT body_json FROM recognition_admin_bindings '
                                         'ORDER BY generation DESC LIMIT 1').fetchone()[0])
    activation = readiness.require_activated(state.control, binding)
    a.need(a.timestamp(now) >= a.timestamp(activation['at_utc']), 'administrative_clock_rollback', 503)
    a.need(digest(activation) == state.activation_sha256, 'activated_incarnation_mismatch', 503)
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
    _, now = state.clock.read()
    a.need(now >= state.started_at, 'administrative_clock_rollback', 503)
    for expires, code in state.auth_expiries:
        a.need(now < expires, code, 401)


def _evaluate(state):
    # All authentication and approval checks are the existing current readers.
    view = state.view
    view.validate_session(state.session, primary_token=state.primary)
    value = approvals.read_current(view, state.approval_id, session_token=state.session, primary_token=state.primary)
    a.need(value['approval_sha256'] == state.approval_sha256
           and value['approval']['binding']['reference'] == state.reference, 'activated_approval_mismatch')
    binding, profile, head = v._history(state.control)
    inventory = disposition._inspect_reserved(state.control, binding, profile, head, state.clock)
    a.need(not any(row['blocks_readiness'] for row in inventory['claims']), 'activated_claim_disposition_blocked', 503)
    assessment = readiness._assess_runtime(view, state.session, state.primary)
    a.need(assessment['code_ready'] and assessment['rehearsal_evidence_present']
           and assessment['activation_state'] == 'ACTIVATED', 'activated_readiness_blocked', 503)
    _read_parts(state.context)
    _time(state)
    activation = readiness.require_activated(state.control, binding)
    # No key-derived digest, seed/ciphertext, raw credential or SQL handle is
    # included. This record observes preactivation v2 facts; it does not promote
    # those facts to an activation-bound operation/execution contract.
    return dict(format='recognition-activated-admission-evidence-v1', execution_authority=False,
        activation_sequence=activation['sequence'], activation_sha256=digest(activation),
        runtime_target=contract.build_target(view), approval_sha256=value['approval_sha256'],
        reference=contract._copy(state.reference), readiness_state_sha256=assessment['admission_state_sha256'],
        claim_disposition=inventory['claims'])


def _finish(state):
    # Denial seals the body API, but its existing reductions must still commit
    # after independent final scope/ownership checks while BOTH locks are held.
    a.need(state.pid == os.getpid() and state.thread is threading.current_thread()
           and state.ident == threading.get_ident() and state.active and not state.poisoned
           and state.control is state.connections[0] and state.target is state.connections[1]
           and state.control.in_transaction and state.target.in_transaction
           and (state.control_reservation_epoch, state.target_reservation_epoch) == state.epochs,
           'activated_context_invalid', 503)
    if state.denial is None:
        a.need(_evaluate(state) == state.result, 'activated_validation_changed', 503)
        a.need(state.control.total_changes == state.control_changes, 'activated_success_write_forbidden', 503)
    else:
        a.need(v._denial_safe(state), 'activated_denial_integrity_failure', 503)
    scope, _, _ = _current(state)
    a.need(scope == state.snapshot and shared._mfa(state.control, scope) == state.mfa_epoch,
           'runtime_validation_changed', 503)
    a.need(state.target.total_changes == state.target_changes
           and state.target.execute('PRAGMA query_only').fetchone()[0] == 1,
           'activated_target_write_forbidden', 503)
    if state.denial is None:
        _time(state)  # Sample all deadlines last, before control commit.
    else:
        _, now = state.clock.read()
        a.need(now >= state.started_at, 'administrative_clock_rollback', 503)
    state.phase, state.lifecycle, state.commit_attempted = 'FINALIZING', True, True
    try:
        state.control.commit()  # Target reservation remains held until resolved.
        a.need(not state.control.in_transaction and state.target.in_transaction, 'activated_commit_unconfirmed', 503)
        state.control_committed, state.control_resolved, state.phase = True, True, 'COMMITTED'
    except BaseException:
        state.control_committed, state.phase = None, 'OUTCOME_UNKNOWN'
        raise
    finally:
        state.lifecycle = False


@contextmanager
def validation_transaction(config, session_token, approval_id, *, primary_token,
                           approval_sha256, reference, activation_sha256):
    """Fresh activated read boundary; accepts lookup data, never a handoff.

    No activation, issuance, consumption, writer, execution or readiness receipt
    is produced. On any commit/cleanup ambiguity, reject; never retry/adopt.
    """
    a.need(type(config) is a.LocalAdministration, 'local_administration_required', 503)
    config.paths()
    identity(approval_id)
    for value in (approval_sha256, activation_sha256):
        contract.profiles._check_sha(value)
    from .runtime_approval_ceremony import _reference
    _reference(reference)
    a.need(type(session_token) is str and type(primary_token) is str, 'activated_credentials_required')
    state = _State(config)
    state.session, state.primary = session_token, primary_token
    state.approval_id, state.approval_sha256 = approval_id, approval_sha256
    state.reference, state.activation_sha256 = contract._copy(reference), activation_sha256
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
                    context = object.__new__(ActivatedAdmission)
                    state.context, state.phase = context, 'ACTIVE'
                    _contexts[context] = state
                    state.view = shared._register_activated_view(context)
                    state.result = _evaluate(state)
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
                        shared._activated_views.pop(state.view, None)
                    if context is not None:
                        _contexts.pop(context, None)
                    state.session = state.primary = state.context = None
        except BaseException:
            if not state.control_resolved:
                p._rollback(state, control)
            raise
