"""One durable claim consumption; a scoped observation handoff, never a writer."""

from contextlib import contextmanager
import os
import threading
from weakref import WeakKeyDictionary

from . import administration as a, administration_schema
from . import runtime_execution_claims as claims, runtime_execution_claim_schema as schema
from . import runtime_execution_admission as admission, runtime_admission_validation as shared
from . import runtime_claim_validation as owner, runtime_approval_ceremony as ceremony
from .rules import canonical, digest
from .trust import load, require, fields


_handoffs = WeakKeyDictionary()


class ConsumptionCommitOutcome(a.AdminError):
    """No handoff published. Durable inspection is required, never blind retry."""

    def __init__(self, pending, committed):
        self.control_committed = committed
        self.inspection_reference = canonical(dict(claim=pending['body'],event=pending['event']))
        super().__init__('runtime_consumption_committed_without_handoff' if committed is True
                         else 'runtime_consumption_commit_outcome_unknown',503)


class ExecutionHandoff:
    """Scoped, opaque process/thread-local handoff; no SQL or writer methods."""

    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('runtime_handoff_requires_consumption')

    @property
    def snapshot(self):
        return admission._freeze(load(_handoff(self)['binding']))

    def __reduce_ex__(self, protocol):
        raise TypeError('runtime_handoff_cannot_be_restored')


def _handoff(token):
    value = _handoffs.get(token) if type(token) is ExecutionHandoff else None
    require(value is not None and value['pid'] == os.getpid()
            and value['thread'] is threading.current_thread() and not value['spent'],
            'runtime_handoff_invalid')
    now = claims._live_time(value)
    for expires,code in value['deadlines']:
        a.need(now < expires,code,401)
    return value


def take_handoff(token):
    """Spend this local handoff once; return immutable DATA, never authority.

    No existing writer accepts either this token or the returned historical data.
    A future execution boundary must independently revalidate before any writes.
    """
    value = _handoff(token)
    result = admission._freeze(load(value['binding']))
    value['spent'] = True
    return result


def _validate(state, pending=None):
    pending = state.pending_claim if pending is None else pending
    body = pending['body']
    observed = load(shared.validate(pending['view'],pending['snapshot'],pending['session'],
                                    primary_token=pending['primary']).canonical_json)
    reference = observed['reference']
    exact = dict(operation_id=observed['proposal']['operation_id'],operation_sha256=digest(observed['proposal']),
        proposal_sha256=digest(observed['proposal']),proposal_reference=reference,
        acknowledgement_sha256=reference['acknowledgement_sha256'],approval_id=observed['approval']['approval_id'],
        approval_sha256=observed['approval_sha256'],approval_history_sha256=observed['approval_history_sha256'],
        runtime_scope=observed['runtime_scope'],authentication=observed['authentication'],
        dependency_snapshot_sha256=digest(observed['dependency_snapshot']),target_snapshot=observed['target_snapshot'],
        target_snapshot_sha256=digest(observed['target_snapshot']),
        emergency_stop_snapshot_sha256=digest(observed['emergency_stop_snapshot']))
    require(all(body[key] == value for key,value in exact.items()),'runtime_consumption_claim_scope_mismatch')
    # Approval remains historical. Consumption adds its own recent-ceremony gate;
    # it never recreates the already spent approval step-up/confirmation.
    binding = observed['approval']['binding']
    matches = [load(row[0])['subject'] for row in state.control.execute(
        "SELECT body_json FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",
        (ceremony.STEP_ACTION,)) if digest(load(row[0])['subject']) == binding['step_up_sha256']]
    require(len(matches) == 1,'runtime_consumption_step_scope_missing')
    step = ceremony.validate_artifact(matches[0])
    confirmation = ceremony._artifact(state.control,observed['approval']['confirmation_sha256'],ceremony.CONFIRMATION)
    now = claims._live_time(pending)
    for artifact in (step,confirmation):
        require(a.timestamp(artifact['issued_at_utc']) <= now < a.timestamp(artifact['expires_at_utc']),
                'runtime_consumption_ceremony_expired')
        state.auth_expiries.append((a.timestamp(artifact['expires_at_utc']),'runtime_consumption_ceremony_expired'))
    require(now >= a.timestamp(observed['checked_at_utc']),'runtime_claim_clock_anomaly')
    return observed,now


def _insert(state):
    """Fixed control HISTORY + audit insertion, never issuance or target DML."""
    state.check()
    pending = state.pending_claim
    require(pending is not None and pending.get('kind') == 'consumption' and not pending['inserted'],
            'runtime_consumption_insert_invalid')
    state.claim_write = True
    state.control.set_authorizer(state.control_authorizer)
    try:
        state.control.execute('INSERT INTO '+schema.HISTORY+' VALUES(?,?,?,?,?,?,?)',pending['event_row'])
        a._audit(state.control,'runtime_execution_claim_state_changed',pending['body']['runtime_scope']['owner_id'],
                 pending['event']['at_utc'],pending['audit_subject'])
    finally:
        state.claim_write = False
        state.control.set_authorizer(state.control_authorizer)
    require(state.control.total_changes == state.control_changes+2,'runtime_consumption_write_integrity')
    state.control_changes += 2
    pending['inserted'] = True


def _final_check(state):
    pending = state.pending_claim
    require(pending['inserted'],'runtime_consumption_insert_incomplete')
    _validate(state)
    require(claims._protected(state.control) == pending['protected']
            and claims._rows(state.control,schema.CLAIMS) == pending['claims']
            and claims._rows(state.control,schema.HISTORY) == pending['history'],
            'runtime_consumption_write_integrity')
    require([tuple(row) for row in state.control.execute(
        'SELECT * FROM recognition_admin_audit WHERE sequence>? ORDER BY sequence',(state.audit_sequence,))]
        == [pending['audit']],'runtime_consumption_audit_integrity')
    administration_schema.check_control(state.control)
    a._audit_head(state.control)
    claims._live_time(pending)


@contextmanager
def consume(config, claim, operation_context, session_token, *, primary_token):
    """Spend a genuine claim once, then yield a non-writer scoped handoff.

    operation_context MUST be the original genuine 4d-0 object, with its exact
    digest durably bound by this claim. No replacement scope or detached object.
    Control commits before publication, while target is still reserved/query-only.
    """
    receipt = claims._receipt(claim)
    original = admission._data(operation_context)
    body = schema._body(receipt['json'],receipt['sha256'])
    require(body == receipt['body'],'runtime_consumption_claim_body_mismatch')
    require(config == original['config'] and original['sha256'] == body['admission_sha256'],
            'runtime_consumption_original_context_required')
    state,pending = None,None
    try:
        with owner.validation_transaction(config) as context:
            state = owner._state(context)
            pending = dict(kind='consumption',body=body,clock=receipt['clock'],view=shared.claim_read_view(context),
                snapshot=operation_context,session=session_token,primary=primary_token,inserted=False)
            observed,now = _validate(state,pending)
            row = state.control.execute('SELECT * FROM '+schema.CLAIMS+' WHERE claim_id=? OR operation_id=?',
                                       (body['claim_id'],body['operation_id'])).fetchall()
            require(len(row) == 1 and row[0]['body_json'] == receipt['json']
                    and row[0]['body_sha256'] == receipt['sha256']
                    and row[0]['claim_id'] == body['claim_id'] and row[0]['operation_id'] == body['operation_id'],
                    'runtime_consumption_durable_claim_mismatch')
            history = state.control.execute('SELECT * FROM '+schema.HISTORY+' WHERE claim_id=? ORDER BY sequence',
                                            (body['claim_id'],)).fetchall()
            require(len(history) == 1 and history[0]['state'] == 'ISSUED','runtime_claim_not_consumable')
            state.pending_claim = pending  # From here all failure/denial effects must roll back.
            at = pending['clock'].read()[0]
            require(a.timestamp(at) >= now,'runtime_claim_clock_anomaly')
            event = dict(format=schema.EVENT_FORMAT,claim_id=body['claim_id'],claim_sha256=receipt['sha256'],
                sequence=2,previous_sha256=history[0]['body_sha256'],state='CONSUMED',
                reason='Exact runtime claim consumed; no writer authority issued',at_utc=at)
            head = a._audit_head(state.control)
            sequence = head['sequence']+1
            subject = dict(claim_id=body['claim_id'],claim_sha256=receipt['sha256'],event_sequence=2,event_sha256=digest(event))
            audit = dict(action='runtime_execution_claim_state_changed',actor=body['runtime_scope']['owner_id'],
                at_utc=at,subject=subject,previous_sha256=head['body_sha256'])
            event_row = (body['claim_id'],2,'CONSUMED',a.timestamp(at),canonical(event),digest(event),sequence)
            pending.update(event=event,event_row=event_row,audit_subject=subject,
                audit=(sequence,canonical(audit),digest(audit)),protected=claims._protected(state.control),
                claims=claims._rows(state.control,schema.CLAIMS),
                history=sorted(claims._rows(state.control,schema.HISTORY)+[event_row],key=repr))
            # This immutable binding is historical eligibility, not live writer authority.
            binding = canonical(dict(claim=body,claim_sha256=receipt['sha256'],consumption=event,
                consumption_sha256=digest(event),operation=observed['proposal'],
                manifest_sha256=observed['proposal']['writer_manifest_sha256']))
            _insert(state)
    except BaseException:
        if (pending is not None and state is not None and state.pending_claim is pending
                and state.commit_attempted):
            raise ConsumptionCommitOutcome(pending,state.control_committed) from None
        raise
    try:
        require(state.control_committed is True and state.control_resolved and not state.active,
                'runtime_consumption_commit_not_confirmed')
        now = claims._live_time(pending)
        for expires,code in state.auth_expiries:
            a.need(now < expires,code,401)
    except BaseException:
        raise ConsumptionCommitOutcome(pending,state.control_committed) from None
    token = None
    try:
        token = object.__new__(ExecutionHandoff)
        _handoffs[token] = dict(pid=os.getpid(),thread=threading.current_thread(),spent=False,binding=binding,
                               body=body,clock=receipt['clock'],deadlines=tuple(state.auth_expiries))
    except BaseException:
        if token is not None:
            _handoffs.pop(token,None)
        raise ConsumptionCommitOutcome(pending,True) from None
    try:
        yield token
    finally:
        _handoffs.pop(token,None)


def inspect_consumption(config, inspection_reference):
    """Strict deployment-side read-only DATA inspection, never retry/adoption."""
    require(type(inspection_reference) is str and len(inspection_reference.encode('utf-8')) <= 131072,
            'runtime_consumption_inspection_invalid')
    expected = schema._body(inspection_reference,digest(load(inspection_reference)))
    fields(expected,('claim','event'))
    result = claims.inspect_acquisition(config,canonical(expected['claim']))
    if result['status'] != 'PRESENT_EXACT':
        return dict(result,status='UNKNOWN')
    from dataclasses import asdict
    from . import runtime_challenges
    try:
        with a.connect(config.control) as control:
            control.execute('BEGIN')
            administration_schema.check_control(control)
            a._audit_head(control)
            bound = runtime_challenges._deployment_binding(control)
            require(asdict(a.target_identity(control)) == bound['control_identity'],'control_identity_mismatch')
            row = control.execute('SELECT body_json,body_sha256 FROM '+schema.HISTORY+' WHERE claim_id=? AND sequence=2',
                                  (expected['claim']['claim_id'],)).fetchone()
            status = 'ABSENT_AT_SNAPSHOT' if row is None else (
                'PRESENT_EXACT' if row['body_json'] == canonical(expected['event'])
                and row['body_sha256'] == digest(expected['event']) and expected['event'].get('state') == 'CONSUMED'
                else 'PRESENT_CONFLICT')
            return dict(result,status=status)
    except (ValueError,OSError,a.sqlite3.Error,KeyError,TypeError):
        return dict(result,status='UNKNOWN')
