"""Original-coordinator-owned target-entry metadata, never a family writer.

The only public operation takes a genuine live CreatedAttempt. No SQL, path,
replacement authority/scope or callback is accepted. No retry/adoption exists.
"""

from types import MappingProxyType
from weakref import WeakKeyDictionary
import os
import sqlite3
import threading

from . import administration as a, runtime_validation as v, runtime_scope_validation as shared
from . import runtime_proposal_transaction as p, runtime_admission_validation as admission
from . import runtime_execution_coordinator as coordinator, runtime_activation_authority_issuance as issuer
from . import runtime_execution_attempt_schema as attempts, runtime_activation_authority_schema as authority
from . import runtime_target_entry_storage as storage, runtime_enrollment_transition_schema as transitions
from . import runtime_activated_owner as activated
from .report_connection import _authorizers as report_authorizers
from .runtime_enrollment_transition import _data
from .rules import canonical,digest
from .trust import require,load
from . import runtime_history_validation as history_validation


_contexts=WeakKeyDictionary()
_spent=WeakKeyDictionary()
_results=WeakKeyDictionary()


class MetadataContext:
    __slots__=('__weakref__',)

    def __new__(cls):
        raise TypeError('metadata_requires_original_owner')

    def __reduce_ex__(self, protocol):
        raise TypeError('metadata_context_nonserializable')


class TargetEntry:
    """Immutable original-lifetime inspection only, not admission or a writer token."""
    __slots__=('__weakref__',)

    def __new__(cls):
        raise TypeError('target_entry_requires_confirmed_owner')

    def __reduce_ex__(self, protocol):
        raise TypeError('target_entry_nonserializable')

    @property
    def snapshot(self):
        entry=_results.get(self) if type(self) is TargetEntry else None
        require(entry is not None,'target_entry_result_invalid')
        coordinator._attempt_entry(entry['attempt'])
        require(entry['pid']==os.getpid() and entry['thread'] is threading.current_thread()
                and a.timestamp(v._utc_now())<a.timestamp(entry['expires']), 'target_entry_result_expired')
        from .runtime_execution_admission import _freeze
        return _freeze(load(entry['json']))


class _State(p._State):
    def __init__(self, result, original):
        super().__init__(original['outer'].config)
        self.result,self.outer=result,original['outer']
        self.source=self.outer.attempt_phase.attempt_pending
        require(self.source is not None,'metadata_attempt_source_missing')
        self.session,self.primary=self.outer.session,self.outer.primary
        self.approval_id,self.approval_sha256=self.outer.approval_id,self.outer.approval_sha256
        self.reference,self.activation_sha256=self.outer.reference,self.outer.activation_sha256
        self.reason,self.clock=self.outer.reason,self.outer.clock
        self.auth_expiries=self.outer.auth_expiries
        self.mode='READ_ONLY';self.insert_enabled=False
        self.context=self.view=self.admission_view=None
        self.phase_id=object();self.entry=None;self.entry_row=None
        self.subject=None;self.target_committed=False;self.cleaned=False

    def check(self):
        coordinator._attempt_entry(self.result)
        require(self.outer.current_phase is self and self.outer.phase=='IN_PHASE', 'metadata_original_owner_invalid')
        super().check()
        require(self.control is self.connections[0] and self.target is self.connections[1]
                and (self.control_reservation_epoch,self.target_reservation_epoch)==self.epochs
                and self.target.execute('PRAGMA query_only').fetchone()[0]==(1 if self.mode=='READ_ONLY' else 0),
                'metadata_reservation_invalid')
        require(self.mode in ('READ_ONLY','WRITE_READY'), 'metadata_mode_invalid')

    def reject(self):
        self.outer.poisoned=True
        super().reject()

    def authorize(self, target, action, first, second, database, trigger):
        history_validation.note(self,action,first,second)
        if target and action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
            if (action==sqlite3.SQLITE_INSERT and first==storage.TABLE and trigger is None
                    and self.insert_enabled and self.mode=='WRITE_READY'):
                return sqlite3.SQLITE_OK
            self.poisoned=True
            return sqlite3.SQLITE_DENY
        return super().authorize(target,action,first,second,database,trigger)


def _state(context):
    state=_contexts.get(context) if type(context) is MetadataContext else None
    require(type(state) is _State and state.context is context, 'metadata_context_invalid')
    state.check()
    return state


def _current(state):
    return issuer._current(state)


def _read_parts(context):
    state=_state(context)
    scope,binding,_=_current(state)
    require(scope==state.snapshot and shared._mfa(state.control,scope)==state.mfa_epoch, 'metadata_scope_changed')
    return state.kernel_control,state.body_target,binding,state.snapshot


def _require_auth_expiry(context, expires, code):
    state=_state(context);shared._validate_expiry(expires,code)
    a.need(a.timestamp(v._utc_now())<expires,code,401)
    state.auth_expiries.append((expires,code))


def _time(state):
    coordinator._require_outer(state.outer)
    activated._time(state)


def _invalidate(state):
    if state.view is not None:shared._metadata_views.pop(state.view,None)
    if state.admission_view is not None:admission._views.pop(state.admission_view,None)
    if state.context is not None:_contexts.pop(state.context,None)
    state.view=state.admission_view=state.context=None
    state.phase_id=object()


def _register(state):
    state.epochs=state.control_reservation_epoch,state.target_reservation_epoch
    context=object.__new__(MetadataContext)
    state.context=context;_contexts[context]=state
    state.view=shared._register_metadata_view(context)
    state.admission_view=admission.metadata_read_view(context)


def _mode(state, query_only):
    _invalidate(state)
    state.lifecycle=True
    try:state.target.execute('PRAGMA query_only='+('ON' if query_only else 'OFF'))
    finally:state.lifecycle=False
    state.mode='READ_ONLY' if query_only else 'WRITE_READY'
    state.target.set_authorizer(state.target_authorizer)  # invalidate statement cache
    _register(state)


def _finalized(state):
    binding,profile,_=v._history(state.control)
    require(transitions.present(state.control),'metadata_finalized_profile_required')
    rows=state.control.execute(f'SELECT h.plan_id FROM {transitions.HISTORY} h JOIN {transitions.PLANS} q ON q.plan_id=h.plan_id '
        'WHERE h.sequence=4 AND h.state=\'FINALIZED\' AND h.destination_generation=? AND h.destination_profile_sha256=? '
        'AND h.destination_binding_sha256=? AND q.source_generation+2=?',
        (binding['generation'],profile['profile_sha256'],digest(binding),binding['generation'])).fetchall()
    require(len(rows)==1,'metadata_finalized_profile_required')
    storage.check_schema(state.target)


def _attempt(state):
    original=coordinator._attempt_entry(state.result)
    require(original['outer'] is state.outer and state.outer.attempt_phase.attempt_pending is state.source,
            'metadata_attempt_provenance_changed')
    for table,expected in ((attempts.ATTEMPTS,state.source['row']),(attempts.HISTORY,state.source['history'])):
        rows=state.control.execute('SELECT * FROM '+table).fetchall()
        require(len(rows)==1 and dict(rows[0])==expected,'metadata_attempt_changed')
    row=state.control.execute('SELECT * FROM recognition_admin_audit WHERE sequence=?',(state.source['row']['audit_sequence'],)).fetchone()
    require(row is not None and canonical(authority._record(row))==canonical(state.source['audit']), 'metadata_creation_audit_changed')
    attempts.check_rows(state.control)
    attempts.validate_binding(state.control,state.source['body'],expected_scope={k:state.subject[k] for k in attempts.SCOPE_FIELDS})
    attempts.validate_expiry(state.source['body'],now=v._utc_now())


def _evaluate_kernel(state):
    state.check();_finalized(state)
    admission._collect(state.admission_view,state.session,state.primary,state.approval_id,state.approval_sha256,state.reference)
    state.subject=issuer._subject_for_owner(state.context)
    require(canonical(state.subject)==canonical(state.outer.subject),'metadata_authority_scope_changed')
    _attempt(state)
    row=state.control.execute(f'SELECT * FROM {authority.AUTHORITIES} WHERE authority_id=?',
        (load(state.outer.authority_json)['authority_id'],)).fetchone()
    require(row is not None and row['body_json']==state.outer.authority_json and row['body_sha256']==state.outer.authority_sha256,
            'metadata_authority_changed')
    authority.check_rows(state.control)
    body=authority.parse_authority(row['body_json'],authority_sha256=row['body_sha256'])
    artifact=authority._artifact(state.control,body['producer_ceremony']['confirmation_artifact_sha256'],authority.CONFIRM_ACTION,authority.CONFIRMATION)
    issuer.consent._fresh(state,artifact)
    step=authority._artifact(state.control,artifact['step_artifact_sha256'],authority.STEP_ACTION,authority.STEP)
    issuer.consent._fresh(state,step)
    require(a.timestamp(body['issued_at_utc'])<=a.timestamp(v._utc_now())<a.timestamp(body['expires_at_utc']), 'metadata_authority_expired')
    require(_data(state.control)==state.control_data and state.control.total_changes==state.control_changes, 'metadata_control_changed')
    require(_data(state.target,exclude=(storage.TABLE,))==state.target_data, 'metadata_business_data_changed')
    rows=state.target.execute(f'SELECT * FROM {storage.TABLE}').fetchall()
    if state.entry is None:
        require(not rows,'metadata_entry_already_exists')
    else:
        require(len(rows)==1 and tuple(rows[0])==state.entry_row, 'metadata_entry_changed')
        storage.check_rows(state.target,state.control)
    _read_parts(state.context);_time(state)
    return body


@history_validation.evaluate
def _evaluate(state):
    token=report_authorizers.set((*report_authorizers.get(),(state.target,state.target_authorizer)))
    try:return _evaluate_kernel(state)
    finally:report_authorizers.reset(token)


def _commit_target(state):
    _invalidate(state);state.lifecycle=True
    try:
        state.target.commit()
        require(not state.target.in_transaction and state.control.in_transaction,'metadata_commit_unconfirmed')
        state.target_committed=True
    finally:state.lifecycle=False


def _reacquire(state, target):
    # This is an explicit successful-commit phase, never reconnect-on-error.
    state.bind(state.control,target)
    target.execute('BEGIN IMMEDIATE');target.execute('PRAGMA query_only=ON')
    state.target_reservation_epoch+=1;state.mode='READ_ONLY'
    target.set_authorizer(state.target_authorizer)
    _register(state)


def create_target_entry(result):
    """Spend one genuine CreatedAttempt in its original coordinator lifetime."""
    original=coordinator._attempt_entry(result)
    require(result not in _spent,'metadata_attempt_already_spent')
    require(original['outer'].current_phase is None,'metadata_phase_already_active')
    _spent[result]=True  # failure/uncertainty never permits a second live attempt
    state=_State(result,original);outer=state.outer
    outer.current_phase,outer.phase=state,'IN_PHASE'
    try:
        with p._owned_connection(state.config.control,state) as control:
            try:
                control.execute('BEGIN IMMEDIATE');v._history(control)
                with p._owned_connection(state.config.target,state) as target:
                    try:
                        state.bind(control,target)
                        target.execute('BEGIN IMMEDIATE');target.execute('PRAGMA query_only=ON')
                        _,state.started_at=state.clock.read()
                        state.snapshot=MappingProxyType(_current(state)[0])
                        state.mfa_epoch=shared._mfa(control,state.snapshot)
                        state.control_data=_data(control);state.target_data=_data(target,exclude=(storage.TABLE,))
                        state.control_changes=control.total_changes
                        state.baseline=v._denial_baseline(control)
                        state.phase='ACTIVE'
                        control.set_authorizer(state.control_authorizer);target.set_authorizer(state.target_authorizer)
                        _register(state);body=_evaluate(state)
                        _mode(state,False);body=_evaluate(state)
                        event=load(state.source['history']['body_json'])
                        entered=v._utc_now()
                        entry=dict(format=storage.FORMAT,state='TARGET_ENTRY_CREATED',attempt_id=state.source['body']['attempt_id'],
                            attempt_sha256=state.source['row']['body_sha256'],creation_event_sha256=state.source['history']['body_sha256'],
                            authority_id=body['authority_id'],authority_sha256=state.outer.authority_sha256,
                            **{k:body[k] for k in storage.SCOPE_FIELDS},entered_at_utc=entered,expires_at_utc=body['expires_at_utc'])
                        serialized=storage.encode_entry(entry,authority_body=body,attempt=state.source['body'],creation_event=event)
                        row=(entry['attempt_id'],body['operation_reference']['operation_id'],entry['authority_sha256'],
                            body['operation_reference']['writer_manifest_sha256'],a.timestamp(entered),serialized,digest(entry))
                        changes=target.total_changes
                        state.insert_enabled=True;target.set_authorizer(state.target_authorizer)
                        try:target.execute(f'INSERT INTO {storage.TABLE} VALUES(?,?,?,?,?,?,?)',row)
                        finally:
                            state.insert_enabled=False;target.set_authorizer(state.target_authorizer)
                        require(target.total_changes==changes+1,'metadata_insert_count')
                        state.entry,state.entry_row=entry,row
                        _invalidate(state);state.target_reservation_epoch+=1;_register(state)
                        _evaluate(state)
                        _mode(state,True);_evaluate(state)
                        # No borrowed view survives integrity inspection/COMMIT.
                        _invalidate(state)
                        require([r[0] for r in target.execute('PRAGMA integrity_check')]==['ok']
                                and not target.execute('PRAGMA foreign_key_check').fetchone(),'metadata_integrity')
                        _time(state);_commit_target(state)
                        with p._owned_connection(state.config.target,state) as verified:
                            _reacquire(state,verified);_evaluate(state)
                            # Entry-only protocol performs NO control mutation/commit.
                            _invalidate(state);p._rollback(state,control)
                    except BaseException:
                        p._rollback(state,control)
                        raise
                    finally:
                        _invalidate(state);state.active=False
            except BaseException:
                if not state.control_resolved:p._rollback(state,control)
                raise
        state.cleaned=True
        require(state.target_committed and state.control_resolved,'metadata_cleanup_unconfirmed')
        answer=object.__new__(TargetEntry)
        _results[answer]=dict(attempt=result,pid=os.getpid(),thread=threading.current_thread(),expires=state.entry['expires_at_utc'],
            json=canonical(dict(state='TARGET_ENTRY_CREATED',entry=state.entry,entry_sha256=digest(state.entry),
                                historical_only=True,execution_authority=False,retry_authorized=False)))
        return answer
    except BaseException:
        outer.poisoned=True
        raise
    finally:
        _invalidate(state);state.active=False
        outer.current_phase=None
        outer.phase='POISONED' if outer.poisoned else 'CONTINUABLE'
