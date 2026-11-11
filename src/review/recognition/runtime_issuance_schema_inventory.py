"""Z14/Z15-C: original issuance inventory only, never migration validity."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass

from . import administration as a
from .rules import canonical
from .trust import require
from . import runtime_attempt_schema_manifest_observation as inventory


_active = ContextVar('recognition_issuance_schema_inventory', default=None)


class _Preparation:
    __slots__ = ()

    def __new__(cls):
        raise TypeError('issuance_inventory_requires_original_owner')

    def __reduce_ex__(self, protocol):
        raise TypeError('issuance_inventory_not_serializable')


@dataclass(frozen=True)
class _Facts:
    preparation: _Preparation
    owner: tuple
    context: object
    phase: object
    connections: tuple
    epochs: tuple
    snapshot_json: str
    subject_json: str
    credential_scope: str
    consent_json: str
    objects: tuple
    physical: tuple
    definition_code: tuple
    control_changes: int
    target_changes: int


def _discard(state):
    state.issuance_inventory = None


def _mint(context, artifact):
    """Only the private issuer calls this after its full fresh evaluation."""
    from . import runtime_execution_coordinator as c, runtime_enrollment_transition_schema as transition
    state = c._state(context)
    require(state.issuance_phase and state.pending is None and state.outer.notice is None
            and state.issuance_inventory is None and state.attempt_pending is None
            and not state.issuing and state.denial is None
            and state.control.total_changes == state.control_changes
            and state.target.total_changes == state.target_changes,
            'issuance_inventory_source_invalid')
    # Older installations keep their complete fresh path. Only a freshly
    # validated finalized G+2 installation is eligible for this observation.
    names = tuple(row[0] for row in state.control.execute(
        "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
    if transition.HISTORY not in names:
        return
    scope = state.subject['runtime_target']
    final = state.control.execute(f'SELECT 1 FROM {transition.HISTORY} '
        "WHERE state='FINALIZED' AND destination_generation=? AND destination_profile_sha256=?",
        (scope['generation'], scope['runtime_profile_sha256'])).fetchall()
    if not final:
        return  # Valid earlier scopes retain existing full fresh validation.
    require(len(final) == 1, 'issuance_inventory_finalized_profile_required')
    step = c.storage._artifact(state.control, artifact['step_artifact_sha256'],
                              c.storage.STEP_ACTION, c.storage.STEP)
    c.issuer.consent._fresh(state, artifact)
    c.issuer.consent._fresh(state, step)
    physical = inventory._physical(state)
    require(asdict(physical[0]) == state.subject['physical_snapshot']['control_identity']
            and asdict(physical[1]) == state.subject['physical_snapshot']['target']['observation'],
            'issuance_inventory_source_invalid')
    facts = _Facts(object.__new__(_Preparation),
        (state.pid, state.thread, state.ident, state.outer), context, state.phase_id,
        state.connections, state.epochs, canonical(dict(state.snapshot)), canonical(state.subject),
        inventory._credential_scope(state), canonical(artifact),
        tuple(tuple(row) for row in state.control.execute(inventory._SQL)), physical,
        inventory._definition_code(), state.control.total_changes, state.target.total_changes)
    # Publish internally only after every construction read/check succeeded.
    state.issuance_inventory = facts


def _check(context, preparation):
    from . import runtime_execution_coordinator as c
    state = c._state(context)
    facts = state.issuance_inventory
    require(type(facts) is _Facts and type(preparation) is _Preparation
            and facts.preparation is preparation and facts.context is context
            and state.issuance_phase and state.outer.notice is not None
            and state.pending is not None and not state.issuing and state.denial is None
            and facts.owner == (state.pid, state.thread, state.ident, state.outer)
            and state.phase_id is facts.phase and state.connections == facts.connections
            and state.control is facts.connections[0] and state.target is facts.connections[1]
            and state.epochs == facts.epochs
            and (state.control_reservation_epoch, state.target_reservation_epoch) == facts.epochs
            and canonical(dict(state.snapshot)) == facts.snapshot_json
            and canonical(state.subject) == facts.subject_json
            and inventory._credential_scope(state) == facts.credential_scope
            and inventory._definition_code() == facts.definition_code
            and state.control.total_changes == facts.control_changes+5
            and state.target.total_changes == facts.target_changes
            and inventory._physical(state) == facts.physical,
            'issuance_inventory_invalid')
    artifact = state.pending['artifact']
    require(canonical(artifact) == facts.consent_json,
            'issuance_inventory_consent_changed')
    # This is only the exact source-artifact binding, not consent validity.
    # Existing _evaluate/_final_mutations still perform every fresh durable
    # artifact and deadline check. Repeating those kernels per inventory lookup
    # adds new work; inventory must never claim to validate authentication.
    return facts.objects


def _write_proof(state):
    from . import runtime_execution_coordinator as c, runtime_validation as v
    facts = state.issuance_inventory
    _check(state.context, facts.preparation)
    pending = state.pending
    require(v._denial_baseline(state.control) == pending['expected'], 'issuance_inventory_write_proof')
    rows = state.control.execute('SELECT * FROM recognition_admin_audit WHERE sequence>? ORDER BY sequence',
                                 (state.audit_sequence,)).fetchall()
    require(canonical([c.storage._record(row) for row in rows]) == canonical(pending['audits']),
            'issuance_inventory_write_proof')
    for table, expected in ((c.storage.AUTHORITIES, pending['authority_row']),
                            (c.storage.LIFECYCLE, pending['event_row'])):
        rows = state.control.execute(f'SELECT * FROM {table} WHERE authority_id=?',
                                     (pending['body']['authority_id'],)).fetchall()
        require(len(rows) == 1 and dict(rows[0]) == expected, 'issuance_inventory_write_proof')
    actual = tuple(tuple(row) for row in state.control.execute(inventory._SQL))
    require(actual == facts.objects and len(state.control.execute('PRAGMA database_list').fetchall()) == 1,
            'issuance_inventory_schema_changed')


@contextmanager
def _final_validation(state):
    if state.issuance_inventory is None or state.denial is not None:
        _discard(state)
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
        _discard(state)


def _objects(conn):
    state = _active.get()
    if state is None or not any(conn is value for value in (state.control, state.kernel_control, state.body_control)):
        return inventory._objects(conn)
    try:
        facts = state.issuance_inventory
        require(type(facts) is _Facts, 'issuance_inventory_invalid')
        return _check(state.context, facts.preparation)
    except BaseException:
        state.outer.poisoned = True
        _discard(state)
        raise


def _names(conn):
    if _active.get() is None:
        return inventory._names(conn)
    return tuple(name for name, _ in _objects(conn))
