"""Independent approval owner; fixed internal ceremony/issuance, no target DML."""

from contextlib import contextmanager
import sqlite3
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import administration as a, runtime_validation as v, runtime_scope_validation as shared
from . import runtime_proposal_transaction as p
from .trust import load


_contexts = WeakKeyDictionary()


class RuntimeApprovalContext:
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('runtime_approval_context_requires_owner')

    @property
    def control(self):
        return _state(self).body_control

    @property
    def target(self):
        return _state(self).body_target

    def __getattr__(self, name):
        if name in p._LIFECYCLE or name in ('executemany', 'target_writer', 'approval_writer'):
            _state(self).reject()
        raise AttributeError(name)


class _State(p._State):
    def __init__(self, config):
        super().__init__(config)
        self.ceremony = False
        self.pending = None
        self.invalidation = False
        self.pending_invalidation = None
        self.issuing = False
        self.pending_issuance = None

    def authorize(self, target, action, first, second, *unused):
        if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
            if target:
                self.poisoned = True
                return sqlite3.SQLITE_DENY
            if self.issuing and ((action == sqlite3.SQLITE_INSERT and first in (
                    'recognition_approvals', 'recognition_approval_history', 'recognition_admin_audit'))
                    or (action == sqlite3.SQLITE_UPDATE and first == 'recognition_admin_confirmations'
                        and second == 'used')):
                return sqlite3.SQLITE_OK
            if self.invalidation and action == sqlite3.SQLITE_INSERT and first in ('recognition_approval_history', 'recognition_admin_audit'):
                return sqlite3.SQLITE_OK
            allowed = {sqlite3.SQLITE_INSERT: {'recognition_admin_audit', 'recognition_admin_stepups',
                        'recognition_admin_confirmations', 'recognition_admin_attempts'},
                       sqlite3.SQLITE_UPDATE: {'recognition_admin_confirmations', 'recognition_admin_attempts'},
                       sqlite3.SQLITE_DELETE: {'recognition_admin_stepups'}}
            if self.ceremony and (first in allowed[action] or action == sqlite3.SQLITE_UPDATE
                                 and first == 'recognition_admin_mfa' and second == 'last_counter'):
                return sqlite3.SQLITE_OK
        return super().authorize(target, action, first, second, *unused)


def _state(context):
    state = _contexts.get(context) if type(context) is RuntimeApprovalContext else None
    a.need(state is not None, 'runtime_approval_context_invalid', 503)
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


def read_view(context):
    return _state(context).view


def _finish(state):
    if state.denial is None and state.pending_issuance is not None:
        from . import runtime_approvals
        runtime_approvals._final_check(state)
    if state.denial is None and state.pending_invalidation is not None:
        from . import runtime_approval_contract as contract
        contract._final_invalidation(state)
    if state.denial is None and state.pending is not None:
        from . import runtime_approval_ceremony as ceremony
        ceremony._final_check(state)
    p._finish(state)  # Same final reservation/time/expiry checks, no persistence mode.


@contextmanager
def approval_transaction(config):
    """Control reservation then query-only target, held through control commit."""
    a.need(type(config) is a.LocalAdministration, 'local_administration_required', 503)
    config.paths()
    state, context = _State(config), None
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
                    context = object.__new__(RuntimeApprovalContext)
                    _contexts[context] = state
                    state.phase = 'ACTIVE'
                    state.view = shared._register_approval_view(context)
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
                    if state.view is not None:
                        shared._approval_views.pop(state.view, None)
                    if context is not None:
                        _contexts.pop(context, None)
        except BaseException:
            if not state.control_resolved:
                p._rollback(state, control)
            raise
