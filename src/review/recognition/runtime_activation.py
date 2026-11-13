"""Owner-only v3 activation lifecycle. No execution or target-write authority."""

from contextlib import contextmanager
import secrets
import sqlite3
from weakref import WeakKeyDictionary

from . import administration as a, admin_auth as auth, runtime_auth as ra
from . import runtime_validation as v, runtime_scope_validation as shared
from . import local_readiness as readiness
from .rules import digest
from .trust import load


_contexts = WeakKeyDictionary()


class _Connection(v._Connection):
    """Existing guarded facade with the inventory reader's cursor metadata."""
    __slots__ = ('_owner', '_target')

    def __init__(self, state, target=False):
        super().__init__(state, target=target)
        self._owner, self._target = state, target

    def execute(self, sql, parameters=()):
        from .runtime_proposal_transaction import _Cursor
        self._owner.check()
        connection = self._owner.target if self._target else self._owner.control
        return _Cursor(connection.execute(sql, parameters), self._owner)


class _Context:
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('activation_context_owned_by_manager')

    def __reduce_ex__(self, protocol):
        raise TypeError('activation_context_not_serializable')


class _State(v._TransactionState):
    def check(self):
        super().check()
        a.need(self.control is self.connections[0] and self.target is self.connections[1],
               'activation_reservation_changed', 503)

    def authorize(self, target, action, first, second, *rest):
        if not target and self.ceremony and action == sqlite3.SQLITE_INSERT and first in (
                'recognition_admin_stepups', 'recognition_admin_confirmations',
                'recognition_local_activation'):
            return sqlite3.SQLITE_OK
        return super().authorize(target, action, first, second, *rest)


def _state(context):
    state = _contexts.get(context) if type(context) is _Context else None
    a.need(state is not None, 'activation_context_invalid', 503)
    state.check()
    return state


def _read_parts(context):
    state = _state(context)
    a.need(v._identity_snapshot(state.config, state.control, state.target, v._utc_now()) == state.snapshot,
           'runtime_validation_changed', 503)
    a.need(readiness._state(state.control, state.binding) == state.activation,
           'activation_incarnation_changed', 503)
    return state.kernel_control, state.body_target, state.binding, state.snapshot


def _require_auth_expiry(context, expires, code):
    state = _state(context)
    shared._validate_expiry(expires, 'administrative_session_expired_or_revoked'
                            if code == 'recent_step_up_required' else code)
    a.need(a.timestamp(v._utc_now()) < expires, code, 401)
    state.auth_expiries.append((expires, code))


def _commit(state):
    # Denial reductions also commit through this owner; do not call check(),
    # which deliberately rejects a sealed denial context.
    a.need(state.pid == v.os.getpid() and state.thread is v.threading.current_thread()
           and state.ident == v.threading.get_ident() and state.active and not state.poisoned
           and state.control is state.connections[0] and state.target is state.connections[1]
           and state.control.in_transaction and state.target.in_transaction
           and state.target.execute('PRAGMA query_only').fetchone()[0] == 1,
           'activation_context_invalid', 503)
    state.lifecycle = True
    try:
        state.control.commit()
        a.need(not state.control.in_transaction, 'activation_commit_unconfirmed', 503)
    finally:
        state.lifecycle = False


@contextmanager
def _transaction(config):
    a.need(type(config) is a.LocalAdministration, 'local_administration_required', 503)
    config.paths()
    outcome = dict(committed=False)
    with v._owned_connection(config.control, outcome) as control:
        control.execute('BEGIN IMMEDIATE')
        v._history(control)
        with v._owned_connection(config.target, outcome) as target:
            target.execute('BEGIN IMMEDIATE')
            target.execute('PRAGMA query_only=ON')
            state = _State(control, target)
            state.connections = (control, target)
            state.required_mfa = None
            from .runtime_execution_claims import _Clock
            state.clock = _Clock()
            state.clock.read()
            state.config, state.ceremony = config, False
            state.started_at = a.timestamp(v._utc_now())
            state.snapshot = v._identity_snapshot(config, control, target, v._utc_now())
            state.binding = load(control.execute('SELECT body_json FROM recognition_admin_bindings '
                                                'ORDER BY generation DESC LIMIT 1').fetchone()[0])
            state.activation = readiness._state(control, state.binding)
            if state.activation['state'] == 'ACTIVATED':
                readiness.require_activated(control, state.binding)
            state.baseline = v._denial_baseline(control)
            head = a._audit_head(control)
            state.audit_sequence = head['sequence'] if head else 0
            state.kernel_control, state.body_target = _Connection(state), _Connection(state, target=True)
            changes = target.total_changes
            control.set_authorizer(lambda *args: state.authorize(False, *args))
            target.set_authorizer(lambda *args: state.authorize(True, *args))
            context = object.__new__(_Context)
            _contexts[context] = state
            try:
                yield context
                _read_parts(context)
                state.clock.read()
                now = a.timestamp(v._utc_now())
                a.need(now >= state.started_at, 'administrative_clock_rollback', 503)
                for expires, code in state.auth_expiries:
                    a.need(now < expires, code, 401)
                if state.required_mfa is not None:
                    a.need(shared._mfa(control, state.snapshot) == state.required_mfa,
                           'runtime_validation_changed', 503)
                a.need(target.total_changes == changes and target.execute('PRAGMA query_only').fetchone()[0] == 1,
                       'activation_target_write_forbidden', 503)
                _commit(state)  # Target reservation held through control resolution.
                outcome['committed'] = True
            except BaseException as error:
                if (state.denial is not None and type(error) is a.AdminError
                        and error.code == state.denial and not state.poisoned and v._denial_safe(state)):
                    a.need(v._identity_snapshot(config, control, target, v._utc_now()) == state.snapshot,
                           'runtime_validation_changed', 503)
                    _commit(state)
                else:
                    state.lifecycle = True
                    if control.in_transaction:
                        control.rollback()
                raise
            finally:
                state.active = False
                state.lifecycle = True
                _contexts.pop(context, None)


def _primary(context, token, *, recent=False):
    control, target, binding, scope = _read_parts(context)
    now = v._utc_now()
    primary = auth._primary(control, target, binding, token, now, recent=recent)
    ra._scope(control, scope, 'primary', primary, now)
    _require_auth_expiry(context, primary['expires'], 'primary_authentication_required')
    if recent:
        _require_auth_expiry(context, primary['created'] + auth.RECENT_SECONDS, 'recent_primary_authentication_required')
    return primary


def _scope(context, kind, raw, created_at):
    control, _, _, scope = _read_parts(context)
    control.execute(f'INSERT INTO {ra.r.AUTH} VALUES(?,?,?,?)',
                    (kind, a.token_hash(raw), scope['profile_sha256'], a.timestamp(created_at)))
    a._audit(control, 'runtime_authentication_scoped', scope['owner_id'], created_at,
             dict(token_kind=kind, token_hash=a.token_hash(raw), profile_sha256=scope['profile_sha256'],
                  generation=scope['generation'], installation_id=scope['installation_id'], target_id=scope['target_id']))


def _view(context):
    state = _state(context)
    view = object.__new__(shared.RuntimeReadView)
    epoch = shared._mfa(state.control, state.snapshot)
    if state.required_mfa is not None:
        a.need(epoch == state.required_mfa, 'runtime_validation_changed', 503)
    state.required_mfa = epoch
    shared._activation_views[view] = (context, epoch)
    return view


def record_primary_authentication(config, *, actor_id, reviewer_key, now=None):
    with _transaction(config) as context:
        control, target, binding, _ = _read_parts(context)
        fresh = v._utc_now()
        raw = auth._record_primary(control, target, binding, actor_id=actor_id, reviewer_key=reviewer_key, now=fresh)
        _scope(context, 'primary', raw, fresh)
        _primary(context, raw)
    return raw


def get_admin_identity(config, primary_token, *, now=None):
    with _transaction(config) as context:
        primary = _primary(context, primary_token)
        binding = _state(context).binding
        result = auth.AdminIdentity(primary['actor'], binding['installation_id'], binding['generation'])
    return result


def get_mfa_state(config, primary_token, *, now=None):
    """Owner UI status only; never return seed, URI, counters or credentials."""
    with _transaction(config) as context:
        primary = _primary(context, primary_token)
        control, _, _, _ = _read_parts(context)
        row = control.execute('SELECT state,pending_until FROM recognition_admin_mfa WHERE actor=?',
                              (primary['actor'],)).fetchone()
        a.need(row is not None and row['state'] in ('UNENROLLED', 'PENDING', 'ENROLLED'),
               'mfa_state_unavailable', 503)
        a.need(row['state'] != 'PENDING' or type(row['pending_until']) is int,
               'mfa_state_unavailable', 503)
        result = dict(state=row['state'], pending_expired=row['state'] == 'PENDING'
                      and row['pending_until'] <= a.timestamp(v._utc_now()))
    return result


def begin_enrollment(config, primary_token, *, now=None):
    with _transaction(config) as context:
        _primary(context, primary_token, recent=True)
        control, target, binding, _ = _read_parts(context)
        result = auth._begin_enrollment(control, target, binding, config, primary_token, now=v._utc_now())
    return result


def finish_enrollment(config, primary_token, code, *, now=None):
    with _transaction(config) as context:
        _primary(context, primary_token, recent=True)
        control, target, binding, _ = _read_parts(context)
        auth._finish_enrollment(control, target, binding, config, primary_token, code, now=v._utc_now())


def open_admin_session(config, primary_token, code, *, now=None):
    with _transaction(config) as context:
        _primary(context, primary_token, recent=True)
        control, target, binding, _ = _read_parts(context)
        fresh = v._utc_now()
        raw = auth._open_admin_session(control, target, binding, config, primary_token, code, now=fresh)
        _scope(context, 'session', raw, fresh)
        _view(context).validate_session(raw, primary_token=primary_token)
    return raw


def require_recognition_admin(config, session_token, *, primary_token, now=None):
    with _transaction(config) as context:
        session = _view(context).validate_session(session_token, primary_token=primary_token)
        binding = _state(context).binding
        result = auth.AdminIdentity(session['actor_id'], binding['installation_id'], binding['generation'])
    return result


def _assessment(context, session, primary):
    from . import runtime_claim_disposition as disposition
    state = _state(context)
    binding, profile, head = v._history(state.control)
    inventory = disposition._inspect_reserved(state.control, binding, profile, head, state.clock)
    a.need(not any(row['blocks_readiness'] for row in inventory['claims']),
           'activation_claim_disposition_blocked', 503)
    return readiness._assess_activation(_view(context), session, primary)


def inspect(config, session_token, *, primary_token):
    with _transaction(config) as context:
        _view(context).validate_session(session_token, primary_token=primary_token)
        state = _state(context)
        result = dict(installation_id=state.snapshot['installation_id'], generation=state.snapshot['generation'],
                      activation=dict(state.activation), execution_authority=False)
    return result


def assess(config, session_token, *, primary_token):
    with _transaction(config) as context:
        result = _assessment(context, session_token, primary_token)
    return result


def create_step_up(config, session_token, code, *, primary_token, action, installation_id, generation):
    a.need(type(action) is str and action in {'activate', 'suspend', 'deactivate'}, 'invalid_step_up_scope')
    with _transaction(config) as context:
        state = _state(context)
        a.need(type(generation) is int and installation_id == state.snapshot['installation_id']
               and generation == state.snapshot['generation'], 'activation_scope_mismatch')
        _view(context).validate_session(session_token, primary_token=primary_token)
        control, target, binding, _ = _read_parts(context)
        session, mfa = auth._session(control, target, binding, session_token, v._utc_now())
        auth._code(control, config, binding, mfa, code, v._utc_now())
        raw = secrets.token_urlsafe(32)
        expires = min(a.timestamp(v._utc_now()) + auth.RECENT_SECONDS, session['expires'])
        state.ceremony = True
        control.execute('INSERT INTO recognition_admin_stepups VALUES(?,?,?,?,?,?,?,?)',
                        (a.token_hash(raw), session['token_hash'], action, None, None, None, generation, expires))
        state.ceremony = False
        a._audit(control, 'administrative_step_up', session['actor'], v._utc_now(), dict(action=action, operation_id=None, operation_sha256=None))
    return raw


def _step(context, session_token, primary, step_token, action):
    _view(context).validate_session(session_token, primary_token=primary)
    control, target, binding, _ = _read_parts(context)
    session, _ = auth._session(control, target, binding, session_token, v._utc_now())
    step = auth._step(control, target, binding, session, step_token, action, None, v._utc_now())
    _require_auth_expiry(context, step['expires'], 'recent_step_up_required')
    return session, step


def begin_confirmation(config, session_token, step_token, *, primary_token):
    with _transaction(config) as context:
        state = _state(context)
        session, step = _step(context, session_token, primary_token, step_token, 'activate')
        a.need(state.activation['state'] == 'NOT_ACTIVATED', 'invalid_local_activation_transition')
        assessment = _assessment(context, session_token, primary_token)
        a.need(assessment['activation_ready'], 'local_activation_readiness_not_satisfied')
        raw = secrets.token_urlsafe(32)
        state.ceremony = True
        state.kernel_control.execute('INSERT INTO recognition_admin_confirmations VALUES(?,?,?,?,?,?,?,?,0)',
            (a.token_hash(raw), session['token_hash'], session['actor'], 'activation:'+state.binding['installation_id'],
             digest(readiness.production_operations.local_target(state.binding)),
             readiness._ceremony(state.binding, state.activation, assessment), state.binding['generation'], step['expires']))
        state.ceremony = False
        a._audit(state.kernel_control, 'activation_confirmation_begun', session['actor'], v._utc_now(),
                 dict(confirmation_sha256=a.token_hash(raw), readiness_sha256=digest(readiness._assessment_binding(assessment))))
        result = dict(confirmation_token=raw, readiness=assessment)
    return result


def change_state(config, session_token, step_token, *, primary_token, state, reason, confirmation_token=None):
    a.need(type(state) is str and state in {'ACTIVATED', 'SUSPENDED', 'DEACTIVATED'} and type(reason) is str
           and 1 <= len(reason.strip()) <= 2000, 'explicit_activation_action_required', 400)
    with _transaction(config) as context:
        owner = _state(context)
        session, step = _step(context, session_token, primary_token, step_token,
                           {'ACTIVATED':'activate', 'SUSPENDED':'suspend', 'DEACTIVATED':'deactivate'}[state])
        old = owner.activation
        a.need(state in readiness.TRANSITIONS[old['state']], 'invalid_local_activation_transition')
        confirmation, assessment = None, None
        if state == 'ACTIVATED':
            a.need(old['state'] == 'NOT_ACTIVATED', 'invalid_local_activation_transition')
            assessment = _assessment(context, session_token, primary_token)
            a.need(assessment['activation_ready'], 'local_activation_readiness_not_satisfied')
            confirmation = owner.control.execute('SELECT * FROM recognition_admin_confirmations WHERE token_hash=?',
                                                  (a.token_hash(confirmation_token),)).fetchone()
            a.need(confirmation is not None and not confirmation['used']
                   and confirmation['session_hash'] == session['token_hash'] and confirmation['actor'] == session['actor']
                   and confirmation['operation_id'] == 'activation:'+owner.binding['installation_id']
                   and confirmation['operation_sha256'] == digest(readiness.production_operations.local_target(owner.binding))
                   and confirmation['generation'] == owner.binding['generation']
                   and confirmation['state_sha256'] == readiness._ceremony(owner.binding, old, assessment)
                   and a.timestamp(v._utc_now()) < confirmation['expires'] <= step['expires'],
                   'invalid_or_stale_activation_confirmation')
            _require_auth_expiry(context, confirmation['expires'], 'recent_step_up_required')
            changed = owner.kernel_control.execute('UPDATE recognition_admin_confirmations SET used=1 WHERE token_hash=? AND used=0',
                                                   (confirmation['token_hash'],))
            a.need(changed.rowcount == 1, 'activation_confirmation_conflict', 409)
        # All scope/session/step/readiness checks precede the manager-only transition.
        owner.ceremony = True
        result = readiness._append(owner.kernel_control, owner.binding, state, session['actor'], reason, v._utc_now(),
            readiness=readiness._assessment_binding(assessment) if assessment else None,
            confirmation=confirmation, scope='trusted-local-production')
        a._invalidate(owner.kernel_control)  # Same commit: burn every old browser continuation.
        owner.ceremony = False
        owner.activation = result
        # Credentials are intentionally revoked now; finalization checks expiry/scope,
        # not continued use of those revoked credentials. Nothing executable escapes.
    return dict(result)
