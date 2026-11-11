"""Reservation-bound admission validation only; no claim or writer authority.

The input is an opaque read capability from an exact registered owner, never a
connection, SQL interface, provider or detached scope. Existing fixed readers
use the owner's private connections internally; none escape the capability.
"""

from dataclasses import asdict
from weakref import WeakKeyDictionary

from . import administration as a, dependencies, events, execution as journal, execution_schema
from . import local_execution, permanent, runtime_approval_contract as approvals
from . import runtime_operation_contract as contract, runtime_proposal_records as records
from . import runtime_validation as runtime
from .rules import canonical, digest
from .trust import identity, load, require


FORMAT = 'recognition-runtime-execution-admission-v1'
_views = WeakKeyDictionary()
_results = WeakKeyDictionary()


class AdmissionReadView:
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('admission_read_view_requires_owner')

    def __reduce_ex__(self, protocol):
        raise TypeError('admission_read_view_cannot_be_restored')


class BoundAdmission:
    """Live validation data only, invalid outside its original reservation."""

    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('bound_admission_requires_validation')

    @property
    def canonical_json(self):
        return _result(self)['json']

    @property
    def sha256(self):
        return _result(self)['sha256']

    @property
    def snapshot(self):
        from .runtime_execution_admission import _freeze
        return _freeze(load(self.canonical_json))

    def __reduce_ex__(self, protocol):
        raise TypeError('bound_admission_cannot_be_restored')


def _owner(context, kind):
    if kind == 'proposal':
        from . import runtime_proposal_transaction as owner
    elif kind == 'coordinator':
        from . import runtime_execution_coordinator as owner
    elif kind == 'metadata':
        from . import runtime_target_entry_owner as owner
    elif kind == 'finalization':
        from . import runtime_finalization as owner
    else:
        require(kind == 'claim', 'runtime_admission_read_view_invalid')
        from . import runtime_claim_validation as owner
    # Each owner enforces its own exact context type and private registration.
    state = owner._state(context)
    owner._read_parts(context)
    return state


def _register(context, kind):
    state = _owner(context, kind)
    require((kind in ('metadata', 'finalization') or state.target.execute('PRAGMA query_only').fetchone()[0] == 1)
            and state.persistence is None and state.persistence_write is None,
            'runtime_admission_reservation_invalid')
    view = object.__new__(AdmissionReadView)
    _views[view] = dict(context=context, kind=kind, state=state,
        connections=state.connections, epoch=state.target_reservation_epoch,
        control_epoch=state.control_reservation_epoch,
        target_changes=state.target.total_changes)
    return view


def proposal_read_view(context):
    return _register(context, 'proposal')


def claim_read_view(context):
    return _register(context, 'claim')


def coordinator_read_view(context):
    return _register(context, 'coordinator')


def metadata_read_view(context):
    # Exact separately registered owner checks its fixed mode, connection and
    # epoch in _owner(). No existing query-only owner gains a mode exception.
    return _register(context, 'metadata')


def _resolve(view):
    entry = _views.get(view) if type(view) is AdmissionReadView else None
    require(entry is not None, 'runtime_admission_read_view_invalid')
    state = _owner(entry['context'], entry['kind'])
    require(state is entry['state'] and state.control is entry['connections'][0]
            and state.target is entry['connections'][1]
            and state.target_reservation_epoch == entry['epoch']
            and state.control_reservation_epoch == entry['control_epoch']
            and state.target.total_changes == entry['target_changes']
            and (entry['kind'] in ('metadata', 'finalization') or state.target.execute('PRAGMA query_only').fetchone()[0] == 1)
            and state.persistence is None and state.persistence_write is None,
            'runtime_admission_reservation_invalid')
    # Ownership checks include PID, Thread object/identifier, lifetime, exact
    # connections, poison/denial state and manager-only lifecycle authorization.
    now = a.timestamp(runtime._utc_now())
    a.need(now >= state.started_at, 'administrative_clock_rollback', 503)
    for expires, code in state.auth_expiries:
        a.need(now < expires, code, 401)
    return state, state.view


def _result(result):
    entry = _results.get(result) if type(result) is BoundAdmission else None
    require(entry is not None, 'runtime_bound_admission_invalid')
    _resolve(entry['view'])
    require(a.timestamp(runtime._utc_now()) >= entry['checked_at'], 'runtime_admission_clock_rollback')
    return entry


def _compare(current, expected):
    """Original 4d-0 comparison: only the fresh observation time may advance."""
    require(a.timestamp(current['checked_at_utc']) >= a.timestamp(expected['checked_at_utc'])
            and {key:value for key,value in current.items() if key != 'checked_at_utc'}
            == {key:value for key,value in expected.items() if key != 'checked_at_utc'},
            'runtime_admission_snapshot_stale')


def _collect(read_view, session_token, primary_token, approval_id, approval_sha256, reference):
    state, view = _resolve(read_view)
    value = approvals.read_current(view, approval_id, session_token=session_token, primary_token=primary_token)
    require(value['approval_sha256'] == approval_sha256
            and value['approval']['binding']['reference'] == reference, 'runtime_admission_approval_mismatch')
    pair = records.read_approved_proposal(view, value['approval'], session_token=session_token, primary_token=primary_token)
    operation = pair['operation']
    target = state.target
    execution_schema.check_schema(target)
    frozen = events.get_event(target, operation['event_id'])
    preparation = frozen['preparation']
    dependency = preparation['dependencies']
    require(operation['dependencies_sha256'] == digest(dependency), 'runtime_admission_dependency_mismatch')
    require(dependencies.recheck(target, operation['event_id']) == dict(state='READY', reasons=[]),
            'runtime_admission_dependencies_not_ready')
    require(operation['family'] in local_execution.SUPPORTED and operation['action'] == 'finalize'
            and operation['accounting_policy'] == local_execution.POLICY, 'runtime_admission_unsupported_writer_policy')
    manifest = preparation['manifest']
    # Same read-only whole-population regeneration used by the real coordinator.
    fresh = permanent._prepare(target, operation['family'], manifest['inputs'],
        manifest['evaluation_at_utc'], manifest['authorization_reference'])
    require(fresh == manifest, 'runtime_admission_writer_preconditions_changed')
    stop = journal._stop(state.control)
    require(not stop['active'], 'emergency_stop')
    require(state.control.execute('SELECT 1 FROM recognition_execution_blocks WHERE operation_id=?',
                                  (operation['operation_id'],)).fetchone() is None, 'runtime_admission_execution_blocked')
    # Graph reader already rejects receipts/claims/seals/execution audit for this
    # proposal. No claim/coordinator/projection/writer API is called here.
    observed = a.observe_target(target)
    control_identity = asdict(a.target_identity(state.control))
    actor = view.validate_session(session_token, primary_token=primary_token)
    scope = contract.build_target(view)
    checked = runtime._utc_now()
    require(a.timestamp(checked) >= a.timestamp(value['approval']['approved_at_utc']), 'runtime_admission_clock_rollback')
    result = dict(format=FORMAT, eligibility='ELIGIBLE_CANDIDATE', execution_authority=False,
        checked_at_utc=checked, reference=pair['reference'], proposal=operation,
        acknowledgement=pair['acknowledgement'], approval=value['approval'], approval_sha256=value['approval_sha256'],
        approval_history_sha256=digest(value['history'][-1]), runtime_scope=scope,
        authentication=dict(actor_id=actor['actor_id'], primary_sha256=a.token_hash(primary_token),
                            session_sha256=a.token_hash(session_token)),
        dependency_snapshot=dependency, target_snapshot=dict(target=observed, control_identity=control_identity),
        emergency_stop_snapshot=stop)
    contract._json(result)
    # Fresh authentication/scope/deadlines are checked again by the existing
    # owner before control commit, while target remains reserved. No locks escape.
    return result


def _assess(view, session_token, approval_id, approval_sha256, reference, primary_token, *, expected=None):
    _resolve(view)
    identity(approval_id)
    contract.profiles._check_sha(approval_sha256)
    from .runtime_approval_ceremony import _reference
    _reference(reference)
    reference = contract._copy(reference)
    body = _collect(view, session_token, primary_token, approval_id, approval_sha256, reference)
    if expected is not None:
        _compare(body, expected)
    _resolve(view)
    result = object.__new__(BoundAdmission)
    _results[result] = dict(view=view, json=canonical(body), sha256=digest(body),
                           checked_at=a.timestamp(body['checked_at_utc']))
    return result


def validate(view, snapshot, session_token, *, primary_token):
    """Repeat ALL checks under this reservation; never refresh the input snapshot.

    The result and its accessors remain bound to this exact live reservation.
    No transaction opens, commits or releases here; the manager owns finalization.
    """
    from . import runtime_execution_admission as admission
    old = admission._data(snapshot)
    state, _ = _resolve(view)
    require(state.config == old['config'], 'runtime_admission_configuration_mismatch')
    expected = load(old['json'])
    return _assess(view, session_token, expected['approval']['approval_id'],
        expected['approval_sha256'], expected['reference'], primary_token, expected=expected)
