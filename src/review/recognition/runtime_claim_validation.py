"""Separate claim owner: read validation and fixed claim lifecycle INSERTs.

No target writes or writer authority. Ordinary validation remains read-only;
acquisition and consumption are finalized only by their fixed claim kernels.
"""

from contextlib import contextmanager
import sqlite3
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import administration as a, runtime_validation as v, runtime_scope_validation as shared
from . import runtime_proposal_transaction as p
from .report_connection import _authorizers as report_authorizers
from .trust import load


_contexts = WeakKeyDictionary()


class ClaimValidationContext:
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('claim_validation_requires_owner')


class _State(p._State):
    def __init__(self, config):
        super().__init__(config)
        self.claim_write = False
        self.pending_claim = None

    def authorize(self, target, action, first, second, *unused):
        # Target is unconditionally read-only, including in the private phase.
        if target and action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
            self.poisoned = True
            return sqlite3.SQLITE_DENY
        if self.persistence is not None or self.persistence_write is not None:
            self.poisoned = True
            return sqlite3.SQLITE_DENY
        if (not target and self.claim_write and self.pending_claim is not None
                and action == sqlite3.SQLITE_INSERT and first in (
                    'recognition_runtime_execution_claims', 'recognition_runtime_execution_claim_history',
                    'recognition_admin_audit')):
            if (self.pending_claim.get('kind') == 'consumption'
                    and first == 'recognition_runtime_execution_claims'):
                self.poisoned = True
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        return super().authorize(target, action, first, second, *unused)


def _state(context):
    state = _contexts.get(context) if type(context) is ClaimValidationContext else None
    a.need(state is not None, 'claim_validation_context_invalid', 503)
    state.check()
    return state


def _read_parts(context):
    state = _state(context)
    current = v._snapshot(state.config, state.control, state.target, v._utc_now())
    a.need(current == state.snapshot and shared._mfa(state.control, current) == state.mfa_epoch,
           'runtime_validation_changed', 503)
    binding = load(state.control.execute('SELECT body_json FROM recognition_admin_bindings '
                                        'ORDER BY generation DESC LIMIT 1').fetchone()[0])
    return state.kernel_control, state.body_target, binding, state.snapshot


def _require_auth_expiry(context, expires, code):
    state = _state(context)
    shared._validate_expiry(expires, code)
    a.need(a.timestamp(v._utc_now()) < expires, code, 401)
    state.auth_expiries.append((expires, code))


def _commit(state):
    """Manager-only commit; the target reservation is still held."""
    state.check()
    from . import runtime_execution_claims as claims
    now = claims._live_time(state.pending_claim)
    a.need(now >= state.started_at, 'administrative_clock_rollback', 503)
    for expires, code in state.auth_expiries:
        a.need(now < expires, code, 401)
    state.phase = 'FINALIZING'
    state.lifecycle = True
    state.commit_attempted = True
    try:
        state.control.commit()
        a.need(not state.control.in_transaction and state.target.in_transaction,
               'runtime_claim_commit_not_confirmed', 503)
        state.control_committed = True
        state.control_resolved = True
        state.phase = 'COMMITTED'
    except BaseException:
        state.control_committed = None
        state.phase = 'OUTCOME_UNKNOWN'
        raise
    finally:
        state.lifecycle = False


def _finish(state):
    if state.pending_claim is None:
        p._finish(state)  # Existing read/verified-denial finalization is unchanged.
        return
    if state.pending_claim.get('kind') == 'consumption':
        from . import runtime_claim_consumption
        runtime_claim_consumption._final_check(state)
    else:
        from . import runtime_execution_claims as claims
        claims._final_check(state)
    state.check()
    # Same authoritative scope/MFA and connection ownership checks as the
    # validation-only owner, with the claim clock/deadline sampled LAST.
    a.need(v._snapshot(state.config, state.control, state.target, v._utc_now()) == state.snapshot
           and shared._mfa(state.control, state.snapshot) == state.mfa_epoch,
           'runtime_validation_changed', 503)
    a.need(state.target.total_changes == state.target_changes
           and state.target.execute('PRAGMA query_only').fetchone()[0] == 1
           and state.control.total_changes == state.control_changes,
           'runtime_claim_write_integrity', 503)
    _commit(state)


@contextmanager
def validation_transaction(config):
    """Distinct owner, control first, query-only target held through commit.

    No callback/provider, raw handle or write facade is accepted or published.
    Fixed acquisition inserts claim/history/audit; consumption inserts history/
    audit only. There is no public SQL facade or writer phase.
    """
    a.need(type(config) is a.LocalAdministration, 'local_administration_required', 503)
    config.paths()
    state, context, report_token = _State(config), None, None
    with p._owned_connection(config.control, state) as control:
        try:
            control.execute('BEGIN IMMEDIATE')
            v._history(control)
            with p._owned_connection(config.target, state) as target:
                try:
                    state.bind(control, target)
                    target.execute('BEGIN IMMEDIATE')
                    target.execute('PRAGMA query_only=ON')
                    state.started_at = a.timestamp(v._utc_now())
                    state.snapshot = MappingProxyType(v._snapshot(config, control, target, v._utc_now()))
                    state.mfa_epoch = shared._mfa(control, state.snapshot)
                    state.baseline = v._denial_baseline(control)
                    head = a._audit_head(control)
                    state.audit_sequence = head['sequence'] if head else 0
                    state.control_changes, state.target_changes = control.total_changes, target.total_changes
                    control.set_authorizer(state.control_authorizer)
                    target.set_authorizer(state.target_authorizer)
                    # Existing report readers temporarily replace the callback.
                    # Register THIS owner's fixed guard so nested report exit
                    # restores it rather than clearing the connection's guard.
                    report_token = report_authorizers.set((*report_authorizers.get(),
                        (target, state.target_authorizer)))
                    context = object.__new__(ClaimValidationContext)
                    _contexts[context] = state
                    state.phase = 'ACTIVE'
                    state.view = shared._register_claim_view(context)
                    yield context
                    state.check()
                    _finish(state)
                except BaseException as error:
                    try:
                        if (state.pending_claim is None and state.denial is not None and not state.poisoned and type(error) is a.AdminError
                                and error.code == state.denial and not state.commit_attempted and v._denial_safe(state)):
                            p._finish(state)
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
                        shared._claim_views.pop(state.view, None)
                    if context is not None:
                        _contexts.pop(context, None)
                    if state.pending_claim is not None:
                        # Do not retain credentials or create a weak-registry
                        # value -> state -> borrowed-view strong-reference cycle.
                        for key in ('session', 'primary', 'snapshot', 'view'):
                            state.pending_claim.pop(key, None)
        except BaseException:
            if not state.control_resolved:
                p._rollback(state, control)
            raise
