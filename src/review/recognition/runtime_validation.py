"""Slice 3a: enrolled runtime validation, never authentication or authority.

Deployment observations are retained unchanged. Host access/deployed code remain
trusted; an observation digest is not remote attestation or a credential.
"""

from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import os
import sqlite3
import sys
import threading
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import administration as a, administration_schema as schema
from . import runtime_enrollment as enrollment, runtime_profile_schema as r
from .rules import canonical, digest
from .trust import fields, identity, load


_contexts = WeakKeyDictionary()
_states = WeakKeyDictionary()


class RuntimeCleanupError(a.AdminError):
    """Cleanup failure with explicit durable outcome; never blindly retry."""

    def __init__(self, committed):
        self.control_committed = committed
        super().__init__('runtime_cleanup_after_commit' if committed else 'runtime_cleanup_before_commit', 503)


class RuntimeValidationContext:
    """Opaque, connection/PID/lifetime-bound validation; no capability methods."""

    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('runtime_validation_context_requires_transaction')


def _utc_now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _physical(value):
    fields(value, ('hostname', 'database', 'device', 'inode'))
    enrollment._text(value['hostname'], 255)
    enrollment._path(value['database'])
    for key in ('device', 'inode'):
        a.need(type(value[key]) is int, 'runtime_identity_integer_required', 503)
        r._check_decimal(str(value[key]), inode=key == 'inode')


def _binding(value):
    names = {'format', 'installation_id', 'target_id', 'owner_id', 'generation',
             'target', 'control_identity', 'production_state', 'at_utc', 'previous_sha256'}
    a.need(value.get('format') in ('recognition-local-control-v2', r.V3),
           'runtime_binding_format_invalid', 503)
    fields(value, names | ({'runtime_profile_sha256'} if value['format'] == r.V3 else set()))
    for key in ('installation_id', 'target_id'):
        identity(value[key])
    for key in ('generation', 'owner_id'):
        enrollment._integer(value[key], 1, 9223372036854775807)
    a.timestamp(value['at_utc'])
    a.need(value['production_state'] == 'NOT_ACTIVATED', 'runtime_requires_not_activated', 503)
    if value['previous_sha256'] is not None:
        r._check_sha(value['previous_sha256'])
    if value['format'] == r.V3 and value['runtime_profile_sha256'] is not None:
        r._check_sha(value['runtime_profile_sha256'])
    fields(value['target'], ('observation', 'schema_sha256'))
    r._check_sha(value['target']['schema_sha256'])
    _physical(value['target']['observation'])
    _physical(value['control_identity'])


def _history(control):
    from . import runtime_history_validation as history
    saved=history.read(control)
    if saved is not None:return saved
    value=_history_fresh(control)
    history.remember(control,value)
    return value


def _history_fresh(control):
    schema.check_control(control)
    head = a._audit_head(control)
    bindings, previous = [], None
    for generation, row in enumerate(control.execute(
            'SELECT * FROM recognition_admin_bindings ORDER BY generation'), 1):
        body = load(row['body_json'])
        _binding(body)
        a.need(row['generation'] == generation == body['generation']
               and body['previous_sha256'] == previous and digest(body) == row['body_sha256'],
               'installation_history_integrity_failure', 503)
        previous = row['body_sha256']
        bindings.append(body)
    a.need(bindings and bindings[-1]['format'] == r.V3, 'runtime_requires_v3', 503)
    current = bindings[-1]
    a.need(current['runtime_profile_sha256'] is not None, 'runtime_profile_not_enrolled', 503)
    rows = control.execute(f'SELECT * FROM {r.PROFILES} WHERE profile_sha256=?',
                           (current['runtime_profile_sha256'],)).fetchall()
    a.need(len(rows) == 1, 'runtime_profile_not_enrolled', 503)
    profile = dict(rows[0])
    a.need(profile['format'] == 'recognition-runtime-profile-v1' and profile['role'] == 'runtime'
           and all(profile[k] == current[k] for k in ('generation', 'installation_id', 'target_id', 'owner_id')),
           'runtime_profile_scope_mismatch', 503)
    a.need(profile['generation'] >= 2, 'runtime_profile_scope_mismatch', 503)
    source = bindings[profile['generation'] - 2]
    a.need(source['format'] == r.V3 and source['runtime_profile_sha256'] is None,
           'runtime_profile_source_invalid', 503)
    row = control.execute(f'SELECT * FROM {r.CHALLENGES} WHERE challenge_id=?',
                          (profile['challenge_id'],)).fetchone()
    a.need(row is not None, 'runtime_profile_challenge_invalid', 503)
    challenge = dict(row)
    for key in ('source_generation', 'owner_id', 'audit_sequence'):
        enrollment._integer(challenge[key], 1, 9223372036854775807)
    for key in ('issued_at', 'expires_at'):
        enrollment._integer(challenge[key])
    for key, maximum in (('operator', 200), ('reason', 2000)):
        enrollment._text(challenge[key], maximum)
    a.need(challenge['format'] == 'recognition-runtime-enrollment-challenge-v1'
           and challenge['role'] == 'runtime' and challenge['expires_at'] == challenge['issued_at'] + 600
           and challenge['source_generation'] == profile['generation'] - 1
           and challenge['source_binding_sha256'] == digest(source)
           and all(challenge[k] == profile[k] for k in ('installation_id', 'target_id', 'owner_id')),
           'runtime_profile_challenge_invalid', 503)
    row = control.execute('SELECT body_json FROM recognition_admin_audit WHERE sequence=?',
                          (profile['audit_sequence'],)).fetchone()
    a.need(row is not None, 'runtime_profile_enrollment_invalid', 503)
    audit = load(row[0])
    subject = audit['subject']
    fields(subject, ('reason', 'previous_generation', 'generation', 'source_binding_sha256',
                    'binding_sha256', 'challenge_sha256', 'profile_sha256', 'observation_sha256',
                    'review_sha256', 'private_log_review_confirmed', 'enrollment_confirmed', 'review'))
    a.need(audit['action'] == 'runtime_profile_enrolled' and audit['actor'] == profile['operator']
           and subject['reason'] == profile['reason']
           and subject['private_log_review_confirmed'] is True and subject['enrollment_confirmed'] is True
           and type(subject['generation']) is int and subject['generation'] == profile['generation']
           and type(subject['previous_generation']) is int and subject['previous_generation'] == source['generation']
           and subject['source_binding_sha256'] == digest(source)
           and subject['binding_sha256'] == digest(current)
           and subject['profile_sha256'] == profile['profile_sha256']
           and subject['challenge_sha256'] == challenge['challenge_sha256']
           and subject['observation_sha256'] == profile['observation_sha256']
           and subject['review_sha256'] == digest(subject['review']),
           'runtime_profile_enrollment_invalid', 503)
    review = enrollment.parse_review(canonical(subject['review']))
    a.need(review['selected_observation_sha256'] == profile['observation_sha256'],
           'runtime_profile_observation_invalid', 503)
    selected = next(x['observation'] for x in review['observations']
                    if x['observation_sha256'] == profile['observation_sha256'])
    enrollment.validate_review_scope(review, challenge, source, audit['at_utc'])
    for key in ('observed_at', 'created_at'):
        enrollment._integer(profile[key])
    enrollment._integer(profile['audit_sequence'], 1, 9223372036854775807)
    a.need(all(profile[k] == selected[k] for k in enrollment.PHYSICAL_FIELDS)
           and profile['observed_at'] == selected['observed_at']
           and profile['evidence_channel'] == selected['evidence_channel']
           and profile['created_at'] == a.timestamp(audit['at_utc']),
           'runtime_profile_observation_invalid', 503)
    expected = dict(source, generation=profile['generation'], previous_sha256=digest(source),
                    at_utc=audit['at_utc'], runtime_profile_sha256=profile['profile_sha256'])
    a.need(current == expected, 'runtime_profile_deployment_relationship_invalid', 503)
    row = control.execute('SELECT body_json FROM recognition_admin_audit WHERE sequence=?',
                          (challenge['audit_sequence'],)).fetchone()
    issued = load(row[0]) if row else {}
    a.need(issued.get('action') == 'runtime_enrollment_challenge_issued'
           and issued.get('actor') == challenge['operator']
           and issued.get('subject') == dict(challenge_sha256=challenge['challenge_sha256'], reason=challenge['reason'])
           and challenge['audit_sequence'] < profile['audit_sequence'],
           'runtime_profile_challenge_invalid', 503)
    return current, profile, head


def _identity_snapshot(config, control, target, now):
    """Shared strict physical/history observations, without a lifecycle gate."""
    from .runtime_enrollment_transition_schema import require_no_pending
    require_no_pending(control)
    binding, profile, head = _history(control)
    moment = a.timestamp(now)
    a.need(moment >= profile['created_at'] and (head is None or moment >= a.timestamp(load(head['body_json'])['at_utc'])),
           'administrative_clock_rollback', 503)
    schema.check_target(target)
    observed = a.observe_target(target)
    actual_control = asdict(a.target_identity(control))
    for prefix, path, actual in (('target', config.target, observed['observation']),
                                 ('control', config.control, actual_control)):
        _physical(actual)
        a.need(actual == asdict(a.target_identity(path)), 'runtime_identity_changed', 503)
        expected = dict(hostname=profile['hostname'], database=profile[prefix + '_path'],
                        device=profile[prefix + '_device'], inode=profile[prefix + '_inode'])
        actual = dict(actual, device=str(actual['device']), inode=str(actual['inode']))
        a.need(actual == expected, 'runtime_profile_identity_mismatch', 503)
    a.need(observed['schema_sha256'] == profile['target_schema_sha256'] == binding['target']['schema_sha256'],
           'runtime_profile_schema_mismatch', 503)
    metadata = target.execute(f'SELECT * FROM {schema.TARGET_TABLE}').fetchall()
    a.need(len(metadata) == 1 and all(metadata[0][k] == binding[k] for k in ('installation_id', 'target_id', 'owner_id')),
           'runtime_profile_scope_mismatch', 503)
    from src.review.admin_dashboard import owner_access
    owner = target.execute('SELECT reviewer_key FROM community_reviewers WHERE id=?', (binding['owner_id'],)).fetchone()
    a.need(owner is not None and owner_access(target, binding['owner_id'], owner[0])[0], 'recognition_owner_required')
    epoch = metadata[0]['auth_epoch']
    enrollment._integer(epoch, 1, 9223372036854775807)
    return dict(binding_sha256=digest(binding), profile_sha256=profile['profile_sha256'],
                installation_id=binding['installation_id'], target_id=binding['target_id'],
                generation=binding['generation'], owner_id=binding['owner_id'], auth_epoch=epoch,
                owner_key_sha256=hashlib.sha256(owner[0].encode()).hexdigest())


def _snapshot(config, control, target, now):
    snapshot = _identity_snapshot(config, control, target, now)
    if control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_local_activation'").fetchone():
        from .local_readiness import _state
        binding = load(control.execute('SELECT body_json FROM recognition_admin_bindings '
                                       'ORDER BY generation DESC LIMIT 1').fetchone()[0])
        a.need(_state(control, binding)['state'] == 'NOT_ACTIVATED', 'runtime_requires_not_activated', 503)
    return snapshot


def _context_data(context, control, target):
    data = _contexts.get(context) if type(context) is RuntimeValidationContext else None
    state = _states.get(context) if data is not None else None
    a.need(state is not None, 'runtime_context_invalid', 503)
    state.check()
    a.need(data['control'] is control and data['target'] is target, 'runtime_context_invalid', 503)
    return data


# SQLite action numbers are process constants, not observations or allow
# decisions. Constructing this identical deny set for every column authorizer
# callback adds work to fresh validation without changing its policy.
_AUTHENTICATION_DDL_DENY = frozenset(getattr(sqlite3, 'SQLITE_' + name) for name in (
    'CREATE_INDEX', 'CREATE_TABLE', 'CREATE_TEMP_INDEX', 'CREATE_TEMP_TABLE',
    'CREATE_TEMP_TRIGGER', 'CREATE_TEMP_VIEW', 'CREATE_TRIGGER', 'CREATE_VIEW',
    'CREATE_VTABLE', 'DROP_INDEX', 'DROP_TABLE', 'DROP_TEMP_INDEX', 'DROP_TEMP_TABLE',
    'DROP_TEMP_TRIGGER', 'DROP_TEMP_VIEW', 'DROP_TRIGGER', 'DROP_VIEW', 'DROP_VTABLE',
    'ALTER_TABLE', 'ATTACH', 'DETACH'))


def _authentication_writes(action, table, *unused):
    """SQL scope restriction, not a caller/provider-supplied authority hook."""
    if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
        allowed = {'recognition_admin_primary', 'recognition_admin_sessions',
                   'recognition_admin_mfa', 'recognition_admin_attempts',
                   'recognition_admin_audit', r.AUTH}
        # Existing owner-denial revocation also deletes step-ups and consumes
        # confirmations. Permit those invalidations, never their issuance.
        if action == sqlite3.SQLITE_DELETE:
            allowed.add('recognition_admin_stepups')
        if action == sqlite3.SQLITE_UPDATE:
            allowed.add('recognition_admin_confirmations')
        return sqlite3.SQLITE_OK if table in allowed else sqlite3.SQLITE_DENY
    if action in _AUTHENTICATION_DDL_DENY:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


_DENIAL_TABLES = ('recognition_admin_primary', 'recognition_admin_sessions', r.AUTH,
                 'recognition_admin_mfa', 'recognition_admin_stepups',
                 'recognition_admin_confirmations', 'recognition_admin_attempts')


def _denial_baseline(control):
    return {name: [dict(row) for row in control.execute(f'SELECT * FROM {name} ORDER BY 1')]
            for name in _DENIAL_TABLES}


def _denial_safe(state):
    """Allow only existing denial effects, never issuance or credential changes."""
    before, after = state.baseline, _denial_baseline(state.control)
    for table, column in (('recognition_admin_primary', 'revoked'),
                          ('recognition_admin_sessions', 'revoked'),
                          ('recognition_admin_confirmations', 'used')):
        old, new = before[table], after[table]
        if len(old) != len(new):
            return False
        for left, right in zip(old, new):
            if (right[column] not in (left[column], 1)
                    or {k:v for k,v in left.items() if k != column}
                    != {k:v for k,v in right.items() if k != column}):
                return False
    if before[r.AUTH] != after[r.AUTH] or before['recognition_admin_mfa'] != after['recognition_admin_mfa']:
        return False
    if any(row not in before['recognition_admin_stepups'] for row in after['recognition_admin_stepups']):
        return False
    old = {row['actor']:row for row in before['recognition_admin_attempts']}
    new = {row['actor']:row for row in after['recognition_admin_attempts']}
    if not set(old) <= set(new) or set(new) - set(old) - {state.snapshot['owner_id']}:
        return False
    moment = a.timestamp(_utc_now())
    for actor, row in new.items():
        prior = old.get(actor)
        if row == prior:
            continue
        if actor != state.snapshot['owner_id'] or type(row['failures']) is not int:
            return False
        if (prior and prior['window_start'] <= moment
                and prior['window_start'] + 900 > state.started_at
                and row == dict(prior, failures=prior['failures'] + 1)):
            continue
        earliest = max(state.started_at, prior['window_start'] + 900) if prior else state.started_at
        if (type(row['window_start']) is not int
                or not earliest <= row['window_start'] <= moment
                or row != dict(actor=actor, window_start=row['window_start'], failures=1)):
            return False
    rows = state.control.execute('SELECT * FROM recognition_admin_audit WHERE sequence>?',
                                 (state.audit_sequence,)).fetchall()
    if len(rows) != 1:
        return False
    body = load(rows[0]['body_json'])
    return (body['action'] == 'administration_denied'
            and body['actor'] in (None, state.snapshot['owner_id'])
            and type(body['subject']) is dict and set(body['subject']) == {'code'}
            and type(body['subject']['code']) is str and bool(body['subject']['code']))


class _TransactionState:
    """Private manager-owned handles; never returned by the context API."""

    def __init__(self, control, target):
        self.control, self.target = control, target
        self.pid = os.getpid()
        self.thread = threading.current_thread()
        self.ident = threading.get_ident()
        self.active, self.poisoned, self.lifecycle = True, False, False
        self.denial = None
        self.auth_expiries = []

    def check(self):
        a.need(self.pid == os.getpid() and self.thread is threading.current_thread()
               and self.ident == threading.get_ident() and self.active
               and not self.poisoned and self.denial is None
               and self.control.in_transaction and self.target.in_transaction,
               'runtime_context_invalid', 503)

    def reject(self):
        self.poisoned = True
        raise a.AdminError('runtime_transaction_owned_by_manager', 503)

    def authorize(self, target, action, first, second, *unused):
        if action in (sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT):
            if self.lifecycle:
                return sqlite3.SQLITE_OK
            self.poisoned = True
            return sqlite3.SQLITE_DENY
        read_arguments = {'table_info', 'table_xinfo', 'index_list', 'index_info',
                          'index_xinfo', 'foreign_key_list', 'integrity_check', 'quick_check'}
        if action == sqlite3.SQLITE_PRAGMA and second is not None and first.lower() not in read_arguments:
            self.poisoned = True
            return sqlite3.SQLITE_DENY
        if target and action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
            return sqlite3.SQLITE_DENY
        return _authentication_writes(action, first, second, *unused)


class _Cursor:
    """Do not leak sqlite3.Cursor.connection or an unchecked iterator."""

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

    def __iter__(self):
        return self

    def __next__(self):
        self.__state.check()
        return next(self.__cursor)


class _Connection:
    """Body SQL facade. It owns neither the connection nor its lifecycle."""

    __slots__ = ('__state', '__target')

    def __init__(self, state, target=False):
        self.__state, self.__target = state, target

    def execute(self, sql, parameters=()):
        self.__state.check()
        conn = self.__state.target if self.__target else self.__state.control
        return _Cursor(conn.execute(sql, parameters), self.__state)

    def executemany(self, sql, parameters):
        self.__state.check()
        conn = self.__state.target if self.__target else self.__state.control
        return _Cursor(conn.executemany(sql, parameters), self.__state)

    def commit(self):
        state = self.__state
        state.check()
        if self.__target or not _denial_safe(state):
            state.reject()
        # Existing admin_auth._deny() calls commit(), then raises AdminError.
        # Seal access now, but defer the real COMMIT to manager final validation.
        row = state.control.execute('SELECT body_json FROM recognition_admin_audit ORDER BY sequence DESC LIMIT 1').fetchone()
        state.denial = load(row[0])['subject']['code']

    def __getattr__(self, name):
        if name in {'rollback', 'close', 'executescript', 'cursor', 'set_authorizer',
                    'set_trace_callback', 'create_function', 'create_aggregate', 'backup'}:
            self.__state.check()
            self.__state.reject()
        raise AttributeError(name)


def _finish(state, config, initial_time, snapshot):
    now = _utc_now()
    a.need(not state.poisoned and state.pid == os.getpid()
           and state.thread is threading.current_thread() and state.ident == threading.get_ident(),
           'runtime_context_invalid', 503)
    a.need(a.timestamp(now) >= a.timestamp(initial_time), 'administrative_clock_rollback', 503)
    if state.denial is None:
        for expires, code in state.auth_expiries:
            a.need(a.timestamp(now) < expires, code, 401)
    a.need(_snapshot(config, state.control, state.target, now) == snapshot, 'runtime_validation_changed', 503)
    state.lifecycle = True
    try:
        state.control.commit()  # The one physical commit path; target stays held.
        state.outcome['committed'] = True
    finally:
        state.lifecycle = False


def _require_auth_expiry(context, expires, code):
    """Data-only final expiry constraint; cannot extend or grant authority."""
    data = _contexts.get(context) if type(context) is RuntimeValidationContext else None
    a.need(data is not None, 'runtime_context_invalid', 503)
    _context_data(context, data['control'], data['target'])
    from .runtime_scope_validation import _validate_expiry
    _validate_expiry(expires, code)
    _states[context].auth_expiries.append((expires, code))


@contextmanager
def _owned_connection(path, outcome):
    """Use existing setup; still close if its rollback/exit itself raises."""
    manager = a.connect(path, write=True)
    conn = manager.__enter__()
    try:
        yield conn
    finally:
        failure = None
        try:
            manager.__exit__(*sys.exc_info())
        except BaseException as error:
            failure = error
        finally:
            try:
                conn.close()
            except BaseException as error:
                failure = error
        if failure is not None:
            # A target cleanup failure after COMMIT cannot undo that COMMIT.
            # Distinguish this outcome from a rolled-back issuance failure.
            raise RuntimeCleanupError(outcome['committed']) from None


@contextmanager
def authentication_transaction(config):
    """Manager-owned validation/authentication SQL boundary, not issuance API.

    This may later persist scoped authentication. Validation alone creates none.
    Python reflection/host compromise is outside this in-process integrity model.
    """
    a.need(type(config) is a.LocalAdministration, 'local_administration_required', 503)
    config.paths()
    outcome = dict(committed=False)
    with _owned_connection(config.control, outcome) as control:
        control.execute('BEGIN IMMEDIATE')
        _history(control)
        with _owned_connection(config.target, outcome) as target:
            context = None
            state = None
            try:
                target.execute('BEGIN IMMEDIATE')
                target.execute('PRAGMA query_only=ON')
                initial_time = _utc_now()
                snapshot = _snapshot(config, control, target, initial_time)
                state = _TransactionState(control, target)
                state.config = config
                state.started_at = a.timestamp(initial_time)
                state.outcome = outcome
                state.snapshot = snapshot
                state.baseline = _denial_baseline(control)
                head = a._audit_head(control)
                state.audit_sequence = head['sequence'] if head else 0
                control.set_authorizer(lambda *args: state.authorize(False, *args))
                target.set_authorizer(lambda *args: state.authorize(True, *args))
                context = object.__new__(RuntimeValidationContext)
                _states[context] = state
                _contexts[context] = MappingProxyType(dict(pid=state.pid, control=_Connection(state),
                    target=_Connection(state, target=True), snapshot=MappingProxyType(dict(snapshot))))
                yield context
                state.check()
                _finish(state, config, initial_time, snapshot)
            except BaseException as error:
                try:
                    if (state is not None and state.denial is not None and not state.poisoned
                            and type(error) is a.AdminError and error.code == state.denial
                            and _denial_safe(state)):
                        _finish(state, config, initial_time, snapshot)
                    elif control.in_transaction:
                        if state is not None:
                            state.lifecycle = True
                        control.rollback()  # Target reservation is still held.
                except BaseException:
                    if state is not None:
                        state.lifecycle = True
                    try:
                        if control.in_transaction:
                            control.rollback()
                    except BaseException:
                        # A failed ROLLBACK cannot leave control alive while
                        # target cleanup releases its reservation.
                        control.close()
                        raise
                    raise
                raise
            finally:
                if state is not None:
                    state.active = False
                    state.lifecycle = True  # Only manager/connection cleanup remains.
                if context is not None:
                    _contexts.pop(context, None)
                    _states.pop(context, None)


def validate_runtime_snapshot(config):
    """Observe and validate without a token, key read, or authentication write.

    The returned copy is historical validation data, not a reusable credential.
    """
    with authentication_transaction(config) as context:
        snapshot = dict(_contexts[context]['snapshot'])
    return snapshot
