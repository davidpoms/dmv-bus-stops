"""Private Z6 M observation: control definitions, never row/admission results.

The ContextVar routes reads only; facts belong to one original coordinator state.
No standalone reader, issuance phase or later metadata owner obtains continuity.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass

from . import administration as a
from .rules import canonical, digest
from .trust import require


_SQL = "SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
_active = ContextVar('recognition_attempt_schema_manifest_owner', default=None)


class _Observation:
    __slots__ = ()

    def __new__(cls):
        raise TypeError('coordinator_owned_schema_observation')

    def __reduce_ex__(self, protocol):
        raise TypeError('schema_observation_not_serializable')


@dataclass(frozen=True)
class _Facts:
    observation: _Observation
    owner: tuple
    phase: object
    connections: tuple
    epochs: tuple
    snapshot_json: str
    subject_json: str
    authority_json: str
    objects: tuple
    manifest_sha256: str
    physical: tuple
    control_changes: int
    target_changes: int
    obtained_at_utc: str
    credential_scope_sha256: str
    definition_code: tuple


def _definition_code():
    from . import administration_schema as base, execution_schema, approval_schema, local_readiness
    from . import runtime_profile_schema as profiles, runtime_execution_claim_schema as claims
    from . import runtime_activation_authority_schema as authorities, runtime_execution_attempt_schema as attempts
    from . import runtime_enrollment_transition_schema as transitions
    functions=(base.definitions,execution_schema.control_definitions,approval_schema.definitions,
        local_readiness.definitions,profiles.definitions,claims.definitions,authorities.definitions,
        attempts.definitions,transitions.definitions,profiles.sha,profiles.uuid,profiles.integer,
        profiles.text,profiles.decimal,profiles.path,profiles.column)
    return tuple((fn,getattr(fn,'__code__',None),getattr(fn,'__defaults__',None)) for fn in functions)


def _credential_scope(state):
    return digest(dict(session=state.session, primary=state.primary, approval_id=state.approval_id,
        approval_sha256=state.approval_sha256, reference=state.reference,
        activation_sha256=state.activation_sha256, outer_activation_sha256=state.outer.activation_sha256,
        mfa_epoch=state.mfa_epoch))


def _physical(state):
    # Filesystem identity is independently mutable; it is not cached evidence.
    return (a.target_identity(state.config.control), a.target_identity(state.config.target))


def _mint(state):
    """Called only after the original attempt's complete pre-insert evaluation."""
    from . import runtime_execution_coordinator as c
    c._attempt_state(state)
    require(state.schema_observation is None and state.attempt_pending is None
            and state.pending is None and not state.attempt_writing
            and state.control.total_changes == state.control_changes
            and state.target.total_changes == state.target_changes,
            'attempt_schema_observation_source_invalid')
    c._continuation_entry(state.outer)
    objects = tuple(tuple(row) for row in state.control.execute(_SQL))
    physical = _physical(state)
    require(asdict(physical[0]) == state.subject['physical_snapshot']['control_identity']
            and asdict(physical[1]) == state.subject['physical_snapshot']['target']['observation'],
            'attempt_schema_observation_source_invalid')
    obtained, _ = state.clock.read()
    observation = object.__new__(_Observation)
    state.schema_observation = observation
    state.schema_facts = _Facts(observation, (state.pid,state.thread,state.ident,state.outer), state.phase_id, state.connections,
        state.epochs, canonical(dict(state.snapshot)), canonical(state.subject),
        state.outer.authority_json, objects,
        digest({name:' '.join(sql.split()) for name,sql in objects}),
        physical, state.control.total_changes, state.target.total_changes, obtained, _credential_scope(state), _definition_code())


def _check(state):
    from . import runtime_execution_coordinator as c
    c._attempt_state(state)  # Original registry, process/thread, lifetime and time.
    facts = state.schema_facts
    require(type(facts) is _Facts and state.schema_observation is facts.observation
            and (state.pid,state.thread,state.ident,state.outer) == facts.owner
            and state.phase_id is facts.phase
            and state.control is facts.connections[0] and state.target is facts.connections[1]
            and state.connections == facts.connections
            and (state.control_reservation_epoch,state.target_reservation_epoch) == facts.epochs
            and canonical(dict(state.snapshot)) == facts.snapshot_json
            and canonical(state.subject) == facts.subject_json
            and state.outer.authority_json == facts.authority_json
            and _credential_scope(state) == facts.credential_scope_sha256
            and _definition_code() == facts.definition_code
            and state.attempt_pending is not None and not state.attempt_writing
            and state.pending is None and state.denial is None
            and state.control.total_changes == facts.control_changes+3
            and state.target.total_changes == facts.target_changes
            and _physical(state) == facts.physical,
            'attempt_schema_observation_invalid')
    return facts


def _write_proof(state):
    """Exact fixed rows and one audit suffix, not just total_changes+3.

    This is not graph/history validation. The existing complete validators and
    global FK checks still run in _finish, including _final_attempt.
    """
    from . import runtime_execution_coordinator as c, runtime_validation as v
    facts = _check(state)
    pending = state.attempt_pending
    for table,key in ((c.attempts.ATTEMPTS,'row'),(c.attempts.HISTORY,'history')):
        rows = state.control.execute(f'SELECT * FROM {table}').fetchall()
        require(len(rows) == 1 and dict(rows[0]) == pending[key], 'attempt_schema_write_proof_invalid')
    rows = state.control.execute('SELECT * FROM recognition_admin_audit WHERE sequence>? ORDER BY sequence',
                                 (state.audit_sequence,)).fetchall()
    require(len(rows) == 1 and canonical(c.storage._record(rows[0])) == canonical(pending['audit'])
            and v._denial_baseline(state.control) == state.baseline,
            'attempt_schema_write_proof_invalid')
    # Reobserve definitions and isolation once at the continuity boundary. Fixed
    # installed guards plus the manager's authorizer forbid DDL/ATTACH thereafter.
    actual = tuple(tuple(row) for row in state.control.execute(_SQL))
    require(actual == facts.objects
            and digest({name:' '.join(sql.split()) for name,sql in actual}) == facts.manifest_sha256
            and len(state.control.execute('PRAGMA database_list').fetchall()) == 1,
            'attempt_schema_manifest_changed')


@contextmanager
def _final_validation(state):
    if state.schema_observation is None or state.denial is not None:
        # Auth-kernel denial reductions retain their original manager-owned
        # finalization. They never receive schema continuity across those writes.
        state.schema_observation = state.schema_facts = None
        yield
        return
    try:
        _write_proof(state)
        token = _active.set(state)
        try:
            yield
        finally:
            _active.reset(token)
    except BaseException:
        state.outer.poisoned = True
        raise
    finally:
        # Neither commit/cleanup nor another finalization can reuse this token.
        state.schema_observation = state.schema_facts = None


def _objects(conn):
    state = _active.get()
    if state is None or state.schema_observation is None or not (
            conn is state.control or conn is state.kernel_control or conn is state.body_control):
        return tuple(tuple(row) for row in conn.execute(_SQL))
    try:
        return _check(state).objects
    except BaseException:
        state.outer.poisoned = True
        state.schema_observation = state.schema_facts = None
        raise


def _names(conn):
    state = _active.get()
    if state is not None and state.schema_observation is not None and (
            conn is state.control or conn is state.kernel_control or conn is state.body_control):
        return tuple(name for name, _ in _objects(conn))
    return tuple(row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
