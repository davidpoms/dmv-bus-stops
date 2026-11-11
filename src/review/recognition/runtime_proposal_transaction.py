"""Independent proposal ownership, with private fixed 4b-2 persistence phases.

Body facades remain read-only. Only runtime_proposals' fixed graph/ACK protocol
enters bounded INSERT phases; no downstream or authentication issuance exists.
Private reflection/host compromise is outside the existing in-process model.
"""

from contextlib import contextmanager
import os
import sqlite3
import threading
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import administration as a, runtime_scope_validation as shared
from . import runtime_validation as validation
from .trust import load


_contexts = WeakKeyDictionary()
_LIFECYCLE = frozenset(('commit', 'rollback', 'close', 'executescript', 'cursor',
    'set_authorizer', 'set_trace_callback', 'create_function', 'create_aggregate',
    'create_collation', 'enable_load_extension', 'load_extension', 'backup', 'serialize', 'deserialize'))


class ProposalCleanupError(a.AdminError):
    def __init__(self, committed):
        self.control_committed = committed  # True, False, or None (uncertain).
        code = ('proposal_cleanup_after_commit' if committed is True else
                'proposal_cleanup_after_rollback' if committed is False else 'proposal_cleanup_outcome_unknown')
        super().__init__(code, 503)


class ProposalTransactionContext:
    """Independent opaque ownership; guarded body views are read-only."""

    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('proposal_context_requires_transaction')

    @property
    def control(self):
        return _state(self).body_control

    @property
    def target(self):
        return _state(self).body_target

    def __getattr__(self, name):
        if name in _LIFECYCLE or name in ('target_writer', 'acknowledgement_writer'):
            _state(self).reject()
        raise AttributeError(name)


class _Cursor:
    __slots__ = ('__cursor', '__state')

    def __init__(self, cursor, state):
        self.__cursor, self.__state = cursor, state

    def fetchone(self):
        self.__state.check()
        return self.__cursor.fetchone()

    def fetchall(self):
        self.__state.check()
        return self.__cursor.fetchall()

    @property
    def rowcount(self):
        self.__state.check()
        return self.__cursor.rowcount

    @property
    def description(self):
        self.__state.check()
        return self.__cursor.description

    def __iter__(self):
        return self

    def __next__(self):
        self.__state.check()
        return next(self.__cursor)


class _ReadConnection:
    __slots__ = ('__state', '__target')

    def __init__(self, state, *, target=False):
        self.__state, self.__target = state, target

    def execute(self, sql, parameters=()):
        state = self.__state
        state.check()
        # Independent lexical read fence also prevents prepared-statement cache
        # reuse from turning a kernel-prepared denial UPDATE into a body write.
        if type(sql) is not str or not sql.strip() or sql.lstrip().split(None, 1)[0].upper() not in ('SELECT', 'PRAGMA'):
            state.reject()
        conn = state.target if self.__target else state.control
        return _Cursor(conn.execute(sql, parameters), state)

    def __getattr__(self, name):
        if name in _LIFECYCLE or name == 'executemany':
            self.__state.check()
            self.__state.reject()
        raise AttributeError(name)


class _DenialConnection:
    """Private auth-kernel adapter, never returned by the context/body API."""

    __slots__ = ('__state',)

    def __init__(self, state):
        self.__state = state

    def execute(self, sql, parameters=()):
        state = self.__state
        state.check()
        state.kernel_write = True
        try:
            # Reinstalling the same authorizer invalidates cached statements;
            # authorization is evaluated in this exact invocation's read/denial
            # mode. No caller can replace or disable the authorizer.
            state.control.set_authorizer(state.control_authorizer)
            return _Cursor(state.control.execute(sql, parameters), state)
        finally:
            state.kernel_write = False
            state.control.set_authorizer(state.control_authorizer)

    def commit(self):
        state = self.__state
        state.check()
        if not validation._denial_safe(state):
            state.reject()
        body = load(state.control.execute(
            'SELECT body_json FROM recognition_admin_audit ORDER BY sequence DESC LIMIT 1').fetchone()[0])
        state.denial = body['subject']['code']
        # Compatibility with existing _deny(): seal access and defer physical
        # COMMIT until the proposal owner repeats final validation with locks held.

    def __getattr__(self, name):
        if name in _LIFECYCLE or name == 'executemany':
            self.__state.check()
            self.__state.reject()
        raise AttributeError(name)


class _State:
    def __init__(self, config):
        self.config = config
        self.pid, self.thread, self.ident = os.getpid(), threading.current_thread(), threading.get_ident()
        self.phase = 'CREATED'
        self.active, self.poisoned, self.lifecycle, self.kernel_write = True, False, False, False
        self.denial, self.view, self.control_committed = None, None, False
        self.commit_attempted = False
        self.control_resolved = False
        self.auth_expiries = []
        # Observation only: invalidate borrowed admission views if this owner
        # releases/replaces a target reservation during its fixed protocol.
        self.target_reservation_epoch = 0
        self.control_reservation_epoch = 0
        self.persistence = None
        self.persistence_write = None
        self.target_access = 'VALIDATION_READ_ONLY'
        self.control_access = 'VALIDATION_AND_VERIFIED_DENIAL_ONLY'

    def bind(self, control, target):
        self.control, self.target = control, target
        self.connections = (control, target)
        self.body_control = _ReadConnection(self)
        self.body_target = _ReadConnection(self, target=True)
        self.kernel_control = _DenialConnection(self)
        self.control_authorizer = lambda *args: self.authorize(False, *args)
        self.target_authorizer = lambda *args: self.authorize(True, *args)

    def check(self):
        a.need(self.pid == os.getpid() and self.thread is threading.current_thread()
               and self.ident == threading.get_ident() and self.active and not self.poisoned
               and self.phase == 'ACTIVE' and self.denial is None
               and self.control is self.connections[0] and self.target is self.connections[1]
               and self.control.in_transaction and self.target.in_transaction,
               'proposal_context_invalid', 503)

    def reject(self):
        self.poisoned = True
        raise a.AdminError('proposal_transaction_owned_by_manager', 503)

    def authorize(self, target, action, first, second, *unused):
        if action in (sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT):
            if self.lifecycle:
                if action == sqlite3.SQLITE_TRANSACTION:
                    if target:
                        self.target_reservation_epoch += 1
                    else:
                        self.control_reservation_epoch += 1
                return sqlite3.SQLITE_OK
            self.poisoned = True
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_PRAGMA:
            if target and self.lifecycle and first.lower() == 'query_only':
                if second is not None:
                    self.target_reservation_epoch += 1
                return sqlite3.SQLITE_OK
            arguments = {'table_info', 'table_xinfo', 'index_list', 'index_info', 'index_xinfo',
                         'foreign_key_list', 'foreign_key_check', 'integrity_check', 'quick_check'}
            plain = {'query_only', 'database_list', 'foreign_keys', 'journal_mode', 'synchronous',
                     'application_id', 'user_version'}
            if first.lower() not in arguments and not (first.lower() in plain and second is None):
                self.poisoned = True
                return sqlite3.SQLITE_DENY
        if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
            graph_tables = {'recognition_preparations', 'recognition_frozen_events',
                            'recognition_event_history', 'recognition_operation_contracts',
                            'recognition_operation_decisions', 'recognition_operation_executions'}
            if action == sqlite3.SQLITE_INSERT and (
                    target and self.persistence_write == 'GRAPH' and first in graph_tables
                    or not target and self.persistence_write == 'ACK' and first == 'recognition_admin_audit'):
                return sqlite3.SQLITE_OK
            allowed = {
                sqlite3.SQLITE_INSERT: {'recognition_admin_audit', 'recognition_admin_attempts'},
                sqlite3.SQLITE_UPDATE: {'recognition_admin_primary', 'recognition_admin_sessions',
                                       'recognition_admin_confirmations', 'recognition_admin_attempts'},
                sqlite3.SQLITE_DELETE: {'recognition_admin_stepups'},
            }
            if not target and self.kernel_write and first in allowed[action]:
                return sqlite3.SQLITE_OK
            self.poisoned = True
            return sqlite3.SQLITE_DENY
        # Reuse the existing DDL/ATTACH deny list, never its issuance permissions.
        result = validation._authentication_writes(action, first, second, *unused)
        if result != sqlite3.SQLITE_OK:
            self.poisoned = True
        return result


def _state(context):
    state = _contexts.get(context) if type(context) is ProposalTransactionContext else None
    a.need(state is not None, 'proposal_context_invalid', 503)
    state.check()
    return state


def _read_parts(context):
    state = _state(context)
    current = validation._snapshot(state.config, state.control, state.target, validation._utc_now())
    a.need(current == state.snapshot and shared._mfa(state.control, current) == state.mfa_epoch,
           'runtime_validation_changed', 503)
    binding = load(state.control.execute(
        'SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
    return state.kernel_control, state.body_target, binding, state.snapshot


def read_view(context):
    """Explicit proposal adapter; shared.read_view() stays exclusively 3a."""
    state = _state(context)
    return state.view


def _require_auth_expiry(context, expires, code):
    state = _state(context)
    shared._validate_expiry(expires, code)
    a.need(a.timestamp(validation._utc_now()) < expires, code, 401)
    state.auth_expiries.append((expires, code))  # Never replace/extend earlier constraints.


def _persistence_mode(state, mode):
    """Private fixed-protocol SQL phase; never exposed on body/read views."""
    state.check()
    a.need(mode in (None, 'GRAPH', 'ACK'), 'proposal_context_invalid', 503)
    state.persistence_write = mode
    state.control.set_authorizer(state.control_authorizer)
    state.target.set_authorizer(state.target_authorizer)


def _target_query_only(state, enabled):
    state.check()
    # Explicit invalidation does not depend on SQLite reauthorizing a cached
    # PRAGMA statement on every execution.
    state.target_reservation_epoch += 1
    state.lifecycle = True
    try:
        state.target.execute('PRAGMA query_only=' + ('ON' if enabled else 'OFF'))
    finally:
        state.lifecycle = False


def _target_commit_and_reserve(state):
    state.check()
    state.target_reservation_epoch += 1
    # Target commit necessarily releases its SQLite writer reservation. No view
    # is valid in this gap; control remains reserved throughout. The fixed caller
    # must revalidate the durable graph and all scope before any ACK insertion.
    state.phase = 'TARGET_COMMITTING'
    state.lifecycle = True
    try:
        state.target.commit()
        state.phase = 'TARGET_DURABLE'
        state.target.execute('BEGIN IMMEDIATE')
        state.target.execute('PRAGMA query_only=ON')
    finally:
        state.lifecycle = False
    state.phase = 'ACTIVE'


def _finish(state):
    if state.persistence is not None:
        from . import runtime_proposals
        runtime_proposals._final_check(state)
    state.phase = 'FINALIZING'
    a.need(state.pid == os.getpid() and state.thread is threading.current_thread()
           and state.ident == threading.get_ident() and not state.poisoned,
           'proposal_context_invalid', 503)
    fresh = validation._utc_now()
    a.need(a.timestamp(fresh) >= state.started_at, 'administrative_clock_rollback', 503)
    a.need(state.control.in_transaction and state.target.in_transaction
           and state.control is state.connections[0] and state.target is state.connections[1],
           'proposal_context_invalid', 503)
    a.need(validation._snapshot(state.config, state.control, state.target, fresh) == state.snapshot
           and shared._mfa(state.control, state.snapshot) == state.mfa_epoch, 'runtime_validation_changed', 503)
    a.need(state.target.total_changes == state.target_changes, 'proposal_persistence_not_enabled', 503)
    if state.denial is None:
        a.need(state.control.total_changes == state.control_changes, 'proposal_persistence_not_enabled', 503)
        for expires, code in state.auth_expiries:
            a.need(a.timestamp(fresh) < expires, code, 401)
    else:
        a.need(validation._denial_safe(state), 'proposal_denial_integrity_failure', 503)
    state.lifecycle = True
    state.commit_attempted = True
    try:
        state.control.commit()  # Target reservation remains held through COMMIT.
        state.control_committed = True
        state.control_resolved = True
        state.phase = 'COMMITTED'
    except BaseException:
        state.control_committed = None
        state.phase = 'OUTCOME_UNKNOWN'
        raise
    finally:
        state.lifecycle = False


def _rollback(state, control):
    state.lifecycle = True
    try:
        if control.in_transaction:
            control.rollback()
        state.control_resolved = True
    except BaseException:
        control.close()  # Do not release target with an unresolved live control transaction.
        state.control_resolved = True
        raise
    finally:
        state.lifecycle = False
        if state.control_committed is not True and not state.commit_attempted:
            state.phase = 'ROLLED_BACK'


@contextmanager
def _owned_connection(path, state):
    manager = a.connect(path, write=True)
    conn = manager.__enter__()
    try:
        yield conn
    finally:
        state.lifecycle = True
        failure = None
        try:
            # The caller has already rolled back/committed control while target
            # was held. Target exit rolls back only; no target commit exists.
            manager.__exit__(None, None, None)
        except BaseException as error:
            failure = error
        finally:
            try:
                conn.close()
            except BaseException as error:
                failure = error
        if failure is not None:
            raise ProposalCleanupError(state.control_committed) from None


@contextmanager
def proposal_transaction(config):
    """Reservation owner; body API remains validation-only, never a SQL writer."""
    a.need(type(config) is a.LocalAdministration, 'local_administration_required', 503)
    config.paths()
    state = _State(config)
    context = None
    with _owned_connection(config.control, state) as control:
        try:
            control.execute('BEGIN IMMEDIATE')
            validation._history(control)
            with _owned_connection(config.target, state) as target:
                try:
                    state.bind(control, target)
                    target.execute('BEGIN IMMEDIATE')
                    state.phase = 'RESERVED'
                    target.execute('PRAGMA query_only=ON')
                    state.phase = 'VALIDATING'
                    state.started_at = a.timestamp(validation._utc_now())
                    state.snapshot = MappingProxyType(validation._snapshot(config, control, target, validation._utc_now()))
                    state.mfa_epoch = shared._mfa(control, state.snapshot)
                    state.baseline = validation._denial_baseline(control)
                    head = a._audit_head(control)
                    state.audit_sequence = head['sequence'] if head else 0
                    state.control_changes, state.target_changes = control.total_changes, target.total_changes
                    control.set_authorizer(state.control_authorizer)
                    target.set_authorizer(state.target_authorizer)
                    context = object.__new__(ProposalTransactionContext)
                    _contexts[context] = state
                    state.phase = 'ACTIVE'
                    state.view = shared._register_proposal_view(context)
                    yield context
                    state.check()
                    _finish(state)
                except BaseException as error:
                    try:
                        if (state.denial is not None and not state.poisoned and type(error) is a.AdminError
                                and error.code == state.denial and not state.commit_attempted
                                and validation._denial_safe(state)):
                            _finish(state)
                        elif state.control_committed is not True:
                            _rollback(state, control)
                    except BaseException:
                        if not state.control_resolved:
                            _rollback(state, control)
                        raise
                    raise
                finally:
                    state.active = False
                    if state.view is not None:
                        shared._proposal_views.pop(state.view, None)
                    if context is not None:
                        _contexts.pop(context, None)
        except BaseException:
            if not state.control_resolved:
                _rollback(state, control)
            raise
