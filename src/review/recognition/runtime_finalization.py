"""Original-holder finalization with exact signed-owner or disposable provisioning.

No arbitrary SQL, replacement source authority or retry API exists.
Private Python reflection/host compromise is outside the capability boundary.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
import os
import sqlite3
import threading
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import administration as a, administration_schema as schema, admin_auth as auth
from . import authorization, runtime_validation as v, runtime_scope_validation as shared
from . import runtime_proposal_transaction as p, runtime_execution_claims as clocks
from . import runtime_execution_coordinator as coordinator, runtime_activation_authority_issuance as issuer
from . import runtime_activation_authority_schema as source, runtime_target_entry_owner as metadata
from . import runtime_finalization_contract as contract, runtime_finalization_effects as effects
from . import runtime_finalization_storage as storage, runtime_decision_outcome_journal_schema as journal
from . import runtime_admission_validation as admission, local_readiness as readiness
from . import permanent, events, dependencies, runtime_operation_contract as operation
from .runtime_enrollment_transition import _data
from .report_connection import _authorizers as report_authorizers
from .rules import canonical, digest
from .trust import load, require
from pathlib import Path
from . import runtime_history_validation as history_validation


AUTHORIZE = 'runtime_finalization_issuer_authorized'
ELIGIBILITY = 'runtime_finalization_source_bound'
ISSUER_STARTED = 'runtime_finalization_issuer_started'
REVOKE = 'runtime_finalization_issuer_revoked'
_contexts = WeakKeyDictionary()
_spent = WeakKeyDictionary()
_entitlements = {}


def _isolated_config(config, approval):
    require(type(config) is a.LocalAdministration and approval.environment in ('disposable','production'),
            'finalization_disposable_only')
    config.paths()
    root = Path(approval.target.database).parent
    for path in (config.target,config.control,config.key_file):
        require(path.parent == root and path.resolve() == path and not path.is_symlink(),
                'finalization_disposable_scope')


def _require_entitlement_owner(config, issuer_sha256, session, primary):
    entry = _entitlements.get(issuer_sha256)
    require(entry is not None and entry['config'] == config and entry['pid'] == os.getpid()
            and entry['thread'] is threading.current_thread()
            and entry['session'] == a.token_hash(session) and entry['primary'] == a.token_hash(primary),
            'finalization_original_issuer_required')
    _isolated_config(config,entry['approval'])
    authorization.verify(config.target,entry['approval'],entry['authority'],
                         family='runtime_finalization',permission='governance',action='authorize_issuer')


class FinalizationContext:
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('finalization_requires_protected_owner')

    def __reduce_ex__(self, protocol):
        raise TypeError('finalization_nonserializable')


class _State(p._State):
    def __init__(self, config, session, primary, *, outer=None):
        super().__init__(config)
        self.session, self.primary, self.outer = session, primary, outer
        self.clock = outer.clock if outer is not None else clocks._Clock()
        self.auth_expiries = outer.auth_expiries if outer is not None else []
        self.mode = 'READ_ONLY'; self.writes = None; self.context = self.view = self.admission_view = None
        self.phase_id = object(); self.target_committed = False; self.control_mutations = 0
        self.original_control = self.original_target = None
        if outer is not None:
            for key in ('approval_id','approval_sha256','reference','activation_sha256','reason'):
                setattr(self, key, getattr(outer, key))

    def check(self):
        super().check()
        require(self.pid == os.getpid() and self.thread is threading.current_thread()
                and self.epochs == (self.control_reservation_epoch, self.target_reservation_epoch)
                and self.target.execute('PRAGMA query_only').fetchone()[0] == (1 if self.mode == 'READ_ONLY' else 0),
                'finalization_reservation_invalid')
        if self.outer is not None:
            coordinator._require_outer(self.outer)
            require(self.outer.current_phase is self, 'finalization_original_owner_invalid')

    def authorize(self, target, action, first, second, database, trigger):
        history_validation.note(self,action,first,second)
        if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
            if trigger is None and action == sqlite3.SQLITE_INSERT:
                if self.writes == 'AUDIT' and not target and first == 'recognition_admin_audit':
                    return sqlite3.SQLITE_OK
                if self.writes == 'JOURNAL' and not target and first in (journal.DECISIONS, journal.HISTORY, 'recognition_admin_audit'):
                    return sqlite3.SQLITE_OK
                if self.writes == 'EFFECT' and target and self.mode == 'WRITE_READY' and first in (*effects.TABLES, journal.WITNESSES):
                    return sqlite3.SQLITE_OK
            if not target and self.writes == 'MFA' and action == sqlite3.SQLITE_UPDATE and first == 'recognition_admin_mfa' and second == 'last_counter':
                return sqlite3.SQLITE_OK
        return super().authorize(target, action, first, second, database, trigger)


def _state(context):
    state = _contexts.get(context) if type(context) is FinalizationContext else None
    require(type(state) is _State and state.context is context, 'finalization_context_invalid')
    state.check()
    return state


def _read_parts(context):
    state = _state(context)
    current = v._identity_snapshot(state.config, state.control, state.target, v._utc_now())
    require(current == state.snapshot and shared._mfa(state.control, current) == state.mfa_epoch,
            'finalization_scope_changed')
    binding = load(state.control.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
    return state.kernel_control, state.body_target, binding, state.snapshot


def _require_auth_expiry(context, expires, code):
    state = _state(context); shared._validate_expiry(expires, code)
    require(a.timestamp(v._utc_now()) < expires, code)
    state.auth_expiries.append((expires, code))


def _time(state):
    _, now = state.clock.read()
    require(now >= state.started_at, 'administrative_clock_rollback')
    for expiry, code in state.auth_expiries:
        a.need(now < expiry, code, 401)


def _invalidate(state):
    if state.view is not None: shared._finalization_views.pop(state.view, None)
    if state.admission_view is not None: admission._views.pop(state.admission_view, None)
    if state.context is not None: _contexts.pop(state.context, None)
    state.context = state.view = state.admission_view = None


def _register(state):
    _invalidate(state)
    state.epochs = state.control_reservation_epoch, state.target_reservation_epoch
    state.phase_id = object(); state.context = object.__new__(FinalizationContext)
    _contexts[state.context] = state
    state.view = shared._register_finalization_view(state.context)
    state.admission_view = admission._register(state.context, 'finalization')


def _mode(state, writes=None, *, query_only=None):
    _invalidate(state)
    if query_only is not None:
        state.lifecycle = True
        try: state.target.execute('PRAGMA query_only='+('ON' if query_only else 'OFF'))
        finally: state.lifecycle = False
        state.mode = 'READ_ONLY' if query_only else 'WRITE_READY'
    state.writes = writes
    state.control.set_authorizer(state.control_authorizer)
    state.target.set_authorizer(state.target_authorizer)
    _register(state)


@contextmanager
def _reserved(config, session, primary, *, outer=None, journal_required=True):
    require(type(config) is a.LocalAdministration, 'local_administration_required')
    config.paths()
    state = _State(config, session, primary, outer=outer)
    if outer is not None:
        coordinator._require_outer(outer)
        require(outer.current_phase is None, 'finalization_phase_active')
        outer.current_phase = state
        outer.phase = 'IN_PHASE'
    try:
        with p._owned_connection(config.control, state) as control:
            try:
                control.execute('BEGIN IMMEDIATE'); v._history(control)
                if journal_required:journal.check_schema(control, 'control')
                with p._owned_connection(config.target, state) as target:
                    try:
                        target.execute('BEGIN IMMEDIATE'); target.execute('PRAGMA query_only=ON')
                        if journal_required:journal.check_schema(target, 'target')
                        state.bind(control, target)
                        _, state.started_at = state.clock.read()
                        state.snapshot = MappingProxyType(v._identity_snapshot(config, control, target, v._utc_now()))
                        state.mfa_epoch = shared._mfa(control, state.snapshot)
                        state.baseline = v._denial_baseline(control)
                        head=a._audit_head(control)
                        state.audit_sequence=head['sequence'] if head else 0
                        state.original_control, state.original_target = _data(control), _data(target)
                        state.control_changes, state.target_changes = control.total_changes, target.total_changes
                        state.phase = 'ACTIVE'
                        control.set_authorizer(state.control_authorizer); target.set_authorizer(state.target_authorizer)
                        _register(state)
                        token = report_authorizers.set((*report_authorizers.get(), (target, state.target_authorizer)))
                        try:
                            state.view.validate_session(session, primary_token=primary)
                            yield state
                            _time(state)
                            require(state.control_resolved, 'finalization_control_unresolved')
                        finally: report_authorizers.reset(token)
                    except BaseException as error:
                        if (state.denial is not None and type(error) is a.AdminError
                                and error.code==state.denial and not state.poisoned
                                and not state.commit_attempted and v._denial_safe(state)):
                            # Existing auth denial reductions resolve while the
                            # target reservation (and any uncommitted work) is
                            # still held. Target cleanup always rolls back.
                            require(v._identity_snapshot(config,control,target,v._utc_now())==state.snapshot,
                                    'finalization_denial_scope_changed')
                            _,now=state.clock.read()
                            require(now>=state.started_at,'administrative_clock_rollback')
                            state.lifecycle=True;state.commit_attempted=True
                            try:
                                control.commit();state.control_resolved=True;state.control_committed=True
                            finally:state.lifecycle=False
                        elif not state.control_resolved: p._rollback(state, control)
                        raise
                    finally:
                        _invalidate(state); state.active = False
            except BaseException:
                if not state.control_resolved: p._rollback(state, control)
                raise
    except BaseException:
        if outer is not None: outer.poisoned = True
        raise
    finally:
        if outer is not None:
            outer.current_phase = None
            outer.phase = 'POISONED' if outer.poisoned else 'CONTINUABLE'


def _commit_control(state):
    _read_parts(state.context); _time(state)
    state.lifecycle = True; state.commit_attempted = True
    try:
        state.control.commit()
        require(not state.control.in_transaction and state.target.in_transaction, 'finalization_control_commit_unknown')
        state.control_resolved = True; state.control_committed = True
    except BaseException:
        state.control_committed = None
        raise
    finally: state.lifecycle = False


def _audits(conn, action):
    a._audit_head(conn)
    return [source._record(r) for r in conn.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence')
            if load(r['body_json'])['action'] == action]


def _issuer(conn, issuer_sha256, *, now):
    matches = [x for x in _audits(conn, AUTHORIZE) if digest(x['subject']) == issuer_sha256]
    require(len(matches) == 1, 'finalization_issuer_not_authorized')
    record = matches[0]; value = contract.validate_issuer(record['subject'])
    require(record['actor'] == value['holder']['actor_id'] and record['at_utc'] == value['issued_at_utc'],
            'finalization_issuer_audit_mismatch')
    all_records = [source._record(r) for r in conn.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence')]
    last_index = -1
    for purpose, key in (('bind_governance','governance_binding_sha256'),('adopt_policy','adoption_sha256'),
                         ('appoint_issuer','appointment_sha256'),('authorize_issuer','approval_sha256')):
        found = [(i,r) for i,r in enumerate(all_records) if r['action']=='runtime_finalization_'+purpose+'_approval'
                 and digest(r['subject'])==value[key]]
        require(len(found)==1 and found[0][0]>last_index, 'finalization_governance_provenance')
        last_index, event = found[0]; proof = event['subject']
        if proof['approval']['environment']=='production':
            from .runtime_production_governance import verify_evidence
            verify_evidence(proof['governance_proof'],proof['approval'])
        require(proof['mandate']==contract.MANDATE and proof['purpose']==purpose
                and proof['actor_id']==event['actor']==value['holder']['actor_id']
                and proof['intent']==value['intent'] and proof['approval']['environment'] in ('disposable','production')
                and proof['approval']['action']==purpose
                and proof['approval']['operation_sha256']==digest(value['intent'])
                and proof['approval']['policy_sha256']==digest(value['policy'])
                and proof['approval']['reference']==contract.MANDATE
                and a.timestamp(event['at_utc'])<=a.timestamp(value['issued_at_utc']), 'finalization_governance_provenance')
    require(last_index < all_records.index(record), 'finalization_governance_provenance')
    require(a.timestamp(value['issued_at_utc']) <= a.timestamp(now) < a.timestamp(value['expires_at_utc']),
            'finalization_issuer_expired')
    require(not any(x['subject'].get('issuer_sha256') == issuer_sha256 for x in _audits(conn, REVOKE)),
            'finalization_issuer_revoked')
    return value


def _write_set(manifest):
    return digest(dict(format='recognition-runtime-fixed-write-set-v1', manifest_sha256=digest(manifest),
                       family=manifest['family'], tables=list(effects.TABLES), witness_format=journal.WITNESS_FORMAT))


def authorize_issuer(config, session, code, intent, *, primary_token, approvals, authority,
                     lifetime_policy=source.LIFETIME):
    """Exact provisioned governance approvals and fresh original-owner MFA."""
    operation._json(intent); contract._intent(intent)
    policy = dict(format=contract.POLICY, policy_id=contract.ISSUER_ROLE, version=1,
                  action=contract.EFFECT, max_grants=1, lifetime_policy=lifetime_policy)
    contract._policy(policy)  # Exact policy digest still requires every original approval.
    purposes = ('bind_governance', 'adopt_policy', 'appoint_issuer', 'authorize_issuer')
    require(type(approvals) is dict and set(approvals) == set(purposes), 'finalization_governance_approvals')
    # Provisioning verifies either the registered disposable workspace or signed
    # deployment input. This API never creates a production trust root.
    for purpose in purposes:
        approval = approvals[purpose]
        _isolated_config(config,approval)
        authorization.verify(config.target, approval, authority, family='runtime_finalization',
            permission='governance', action=purpose, operation_sha256=digest(intent),
            policy_sha256=digest(policy), population_sha256=None, reference=contract.MANDATE)
    with _reserved(config, session, primary_token) as state:
        state.auth_expiries.extend((a.timestamp(proof.expires_at_utc),'production_governance_expired')
                                  for proof in approvals.values() if proof.expires_at_utc is not None)
        actor = state.view.validate_session(session, primary_token=primary_token)
        require(actor['actor_id'] == intent['runtime_target']['owner_id'], 'finalization_governance_actor')
        operation.validate_target(intent['runtime_target'], context=state.view)
        require(not any(x['subject']['intent']['operation_id']==intent['operation_id']
                        or x['subject']['intent']['writer_manifest_sha256']==intent['writer_manifest_sha256']
                        for x in _audits(state.control,AUTHORIZE)), 'finalization_issuer_already_authorized')
        now = v._utc_now()
        mfa = state.control.execute('SELECT * FROM recognition_admin_mfa WHERE actor=?', (actor['actor_id'],)).fetchone()
        _mode(state, 'MFA')
        auth._code(state.kernel_control, config, {'installation_id':state.snapshot['installation_id']}, mfa, code, now)
        _mode(state, 'AUDIT')
        refs = {}
        for purpose in purposes:
            subject = dict(purpose=purpose, mandate=contract.MANDATE, intent=intent,
                           approval=asdict(approvals[purpose]), actor_id=actor['actor_id'])
            if approvals[purpose].environment=='production':
                from .runtime_production_governance import evidence
                subject['governance_proof']=evidence(authority,approvals[purpose])
            a._audit(state.control, 'runtime_finalization_'+purpose+'_approval', actor['actor_id'], now, subject)
            refs[purpose] = digest(subject)
        deadlines = [state.control.execute('SELECT expires FROM '+table+' WHERE token_hash=?', (a.token_hash(token),)).fetchone()[0]
                     for table,token in (('recognition_admin_primary',primary_token),('recognition_admin_sessions',session))]
        deadlines.extend(a.timestamp(proof.expires_at_utc) for proof in approvals.values()
                         if proof.expires_at_utc is not None)
        from .runtime_authority_consent import _time as timestamp
        body = contract.validate_issuer(dict(format=contract.ISSUER, mandate=contract.MANDATE,
            governance_binding_sha256=refs['bind_governance'], adoption_sha256=refs['adopt_policy'],
            appointment_sha256=refs['appoint_issuer'], approval_sha256=refs['authorize_issuer'],
            issuer_role=contract.ISSUER_ROLE, holder=dict(actor_id=actor['actor_id'],
            primary_sha256=a.token_hash(primary_token), session_sha256=a.token_hash(session)), intent=intent, policy=policy,
            issued_at_utc=now, expires_at_utc=timestamp(min(a.timestamp(now)+auth.RECENT_SECONDS,*deadlines))))
        a._audit(state.control, AUTHORIZE, actor['actor_id'], now, body)
        require(state.target.total_changes == state.target_changes
                and state.control.total_changes == state.control_changes+6, 'finalization_governance_write_count')
        _mode(state)
        _issuer(state.control, digest(body), now=v._utc_now())
        _commit_control(state)
    _entitlements[digest(body)] = dict(config=config,pid=os.getpid(),thread=threading.current_thread(),
        session=a.token_hash(session),primary=a.token_hash(primary_token),
        approval=approvals['authorize_issuer'],authority=authority)
    return MappingProxyType(dict(issuer_sha256=digest(body), issuer=body, execution_authority=False))


def _check_source_entitlement(state):
    _require_entitlement_owner(state.config,state.outer.finalization_issuer,state.session,state.primary)
    value = _issuer(state.control, state.outer.finalization_issuer, now=v._utc_now())
    require(value['holder'] == state.subject['authentication']
            and value['intent']['runtime_target'] == state.subject['runtime_target'], 'finalization_holder_scope')
    ref = state.subject['operation_reference']; intent = value['intent']
    require(all(intent[k] == ref[k] for k in ('operation_id','operation_sha256','writer_manifest_sha256'))
            and intent['family'] == ref['writer_family'], 'finalization_subject_mismatch')
    frozen = events.get_event(state.target, ref['event_id'])
    manifest = frozen['preparation']['manifest']
    require(_write_set(manifest) == intent['write_set_sha256'], 'finalization_write_set_mismatch')
    require(not any(x['subject']['issuer_sha256'] == digest(value) for x in _audits(state.control, ELIGIBILITY)),
            'finalization_issuer_already_consumed')
    step = source._artifact(state.control, state.pending['body']['producer_ceremony']['step_artifact_sha256'],
                            source.STEP_ACTION, source.STEP) if state.pending else None
    if step is not None:
        require(a.timestamp(value['issued_at_utc']) <= a.timestamp(step['issued_at_utc']),
                'finalization_issuer_not_prospective')
        rows=list(state.control.execute('SELECT sequence,body_json FROM recognition_admin_audit ORDER BY sequence'))
        before=[r[0] for r in rows if load(r[1])['action']==AUTHORIZE
                and digest(load(r[1])['subject'])==digest(value)]
        after=[r[0] for r in rows if load(r[1])['action']==source.STEP_ACTION
               and digest(load(r[1])['subject'])==digest(step)]
        require(len(before)==len(after)==1 and before[0]<after[0], 'finalization_issuer_not_prospective')
    starts=[x for x in _audits(state.control,ISSUER_STARTED) if x['subject']['issuer_sha256']==digest(value)]
    require(len(starts)==1 and starts[0]['subject']['confirmation_sha256']==
            state.pending['body']['producer_ceremony']['confirmation_token_sha256'], 'finalization_issuer_start_mismatch')
    return value


def _claim_issuer(outer, confirmation):
    """Durably spend issuance before construction; failed issuance cannot retry."""
    sha=outer.finalization_issuer
    _require_entitlement_owner(outer.config,sha,outer.session,outer.primary)
    entry=_entitlements[sha]
    require(not entry.get('started',False),'finalization_issuer_already_started')
    entry['started']=True  # Even a failed/uncertain claim is not reusable locally.
    with _reserved(outer.config,outer.session,outer.primary,outer=outer) as state:
        value=_issuer(state.control,sha,now=v._utc_now())
        require(not any(x['subject']['issuer_sha256']==sha for x in _audits(state.control,ISSUER_STARTED)),
                'finalization_issuer_already_started')
        state.subject=issuer._subject_for_owner(state.context)
        require(state.subject['authentication']==value['holder']
                and state.subject['runtime_target']==value['intent']['runtime_target'], 'finalization_holder_scope')
        artifact=issuer.consent._confirmation(state,confirmation)
        ref=state.subject['operation_reference'];intent=value['intent']
        require(all(intent[k]==ref[k] for k in ('operation_id','operation_sha256','writer_manifest_sha256')),
                'finalization_subject_mismatch')
        _mode(state,'AUDIT')
        a._audit(state.control,ISSUER_STARTED,state.snapshot['owner_id'],v._utc_now(),
                 dict(issuer_sha256=sha,confirmation_sha256=artifact['token_sha256'],intent_sha256=digest(intent)))
        require(state.control.total_changes==state.control_changes+1
                and state.target.total_changes==state.target_changes,'finalization_issuer_start_write_count')
        _mode(state);_commit_control(state)


def _bind_source(state):
    value = _check_source_entitlement(state)
    body = state.pending['body']
    action = contract.validate_action(dict(format=contract.ACTION, issuer_sha256=digest(value),
        authority_id=body['authority_id'], authority_sha256=digest(body), holder=value['holder'],
        intent=value['intent'], policy=value['policy'], issued_at_utc=body['issued_at_utc'],
        expires_at_utc=min(body['expires_at_utc'],value['expires_at_utc'])), issuer=value, authority=body)
    expected = dict(action=ELIGIBILITY, actor=value['holder']['actor_id'], at_utc=body['issued_at_utc'],
                    subject=action, previous_sha256=digest(state.pending['audits'][-1]))
    # Only the new exact coordinator protocol permits this one additional audit.
    state.finalization_writing = True
    state.control.set_authorizer(state.control_authorizer)
    try: a._audit(state.control, ELIGIBILITY, value['holder']['actor_id'], body['issued_at_utc'], action)
    finally:
        state.finalization_writing = False
        state.control.set_authorizer(state.control_authorizer)
    state.pending['audits'].append(expected)
    state.pending['finalization_action'] = action


def _validate_bound_source(state):
    action = state.pending['finalization_action']
    value = _issuer(state.control, action['issuer_sha256'], now=v._utc_now())
    contract.validate_action(action, issuer=value, authority=state.pending['body'])
    records = [x for x in _audits(state.control, ELIGIBILITY) if x['subject']['issuer_sha256'] == digest(value)]
    require(len(records) == 1 and records[0] == state.pending['audits'][-1], 'finalization_source_audit_mismatch')


def _current(state):
    return issuer._current(state)


def _readiness(state):
    binding = load(state.control.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
    return readiness._assess_inventory(state.control, state.target, binding,
        v._utc_now(), config=state.config, runtime=(state.view,state.session,state.primary))


def _dependencies(state, event_id):
    """Fresh source predicates, accounting only for this exact proved effect.

    This is not a reusable READY observation. All current source predicates are
    reread; only the known whole family delta is interpreted as our own outcome.
    Other owners/operations retain the original dependency reader unchanged.
    """
    _state(state.context)
    if not hasattr(state,'effect_before') or event_id != state.outer.subject['operation_reference']['event_id']:
        return dependencies.recheck(state.target,event_id)
    frozen=events.get_event(state.target,event_id)
    require(frozen['state'] not in ('STALE','INVALID'),'finalization_dependency_invalidated')
    prep=frozen['preparation']; manifest=prep['manifest']; old=prep['dependencies']
    require(manifest==state.effect_manifest,'finalization_effect_manifest_changed')
    dependencies.validate_binding(old,manifest)
    effects._verify_delta(state.target,manifest,state.effect_before)
    require(_data(state.target,exclude=(*effects.TABLES,journal.WITNESSES))==state.protected_target,
            'finalization_unexpected_write')
    observed=dependencies._observe(state.target,manifest)
    require(all(observed[k]==old['observations'][k] for k in observed if k!='permanent_records'),
            'finalization_source_dependencies_changed')
    # permanent_records alone changed, and the complete exact change has just
    # been proven from actual rows. It cannot authorize another action or holder.
    return dict(state='READY',reasons=[])


def revoke_issuer(config, session, issuer_sha256, *, primary_token, approval, authority):
    """Commit-ordered, scope-exact governance revocation; never an undo/retry."""
    _isolated_config(config,approval)
    authorization.verify(config.target, approval, authority, family='runtime_finalization',
        permission='governance', action='revoke_issuer', operation_sha256=issuer_sha256,
        reference=contract.MANDATE)
    with _reserved(config, session, primary_token) as state:
        values = [r for r in _audits(state.control, AUTHORIZE) if digest(r['subject']) == issuer_sha256]
        require(len(values) == 1 and values[0]['subject']['holder']['actor_id'] == state.snapshot['owner_id'],
                'finalization_issuer_not_authorized')
        require(approval.policy_sha256==digest(values[0]['subject']['policy']),
                'finalization_revocation_policy_mismatch')
        if approval.expires_at_utc is not None:
            state.auth_expiries.append((a.timestamp(approval.expires_at_utc),'production_governance_expired'))
        _mode(state, 'AUDIT')
        subject=dict(issuer_sha256=issuer_sha256, governance_approval=asdict(approval))
        if approval.environment=='production':
            from .runtime_production_governance import evidence
            subject['governance_proof']=evidence(authority,approval)
        a._audit(state.control, REVOKE, state.snapshot['owner_id'], v._utc_now(),
                 subject)
        require(state.control.total_changes == state.control_changes+1
                and state.target.total_changes == state.target_changes, 'finalization_revocation_write_count')
        _mode(state); _commit_control(state)


def _bound_action(state):
    _require_entitlement_owner(state.config,state.outer.finalization_issuer,state.session,state.primary)
    body = load(state.outer.authority_json)
    records = [x for x in _audits(state.control, ELIGIBILITY)
               if x['subject'].get('authority_id') == body['authority_id']]
    require(len(records) == 1, 'finalization_source_not_eligible')
    action = records[0]['subject']
    value = _issuer(state.control, action['issuer_sha256'], now=v._utc_now())
    contract.validate_action(action, issuer=value, authority=body)
    require(action['issuer_sha256'] == state.outer.finalization_issuer
            and action['holder']['primary_sha256'] == a.token_hash(state.primary)
            and action['holder']['session_sha256'] == a.token_hash(state.session), 'finalization_original_holder_mismatch')
    require(a.timestamp(v._utc_now()) < a.timestamp(action['expires_at_utc']), 'finalization_expired')
    state.auth_expiries.append((a.timestamp(action['expires_at_utc']), 'administrative_session_expired_or_revoked'))
    return action


@history_validation.evaluate
def _fresh(state, *, before_effect=True):
    _read_parts(state.context); _time(state)
    action = _bound_action(state)
    state.subject = issuer._subject_for_owner(state.context)
    require(canonical(state.subject) == canonical(state.outer.subject), 'finalization_live_subject_changed')
    body = load(state.outer.authority_json)
    from . import runtime_authority_consent as consent
    for key, audit_action, kind in (
        ('step_artifact_sha256',source.STEP_ACTION,source.STEP),
        ('confirmation_artifact_sha256',source.CONFIRM_ACTION,source.CONFIRMATION)):
        artifact = source._artifact(state.control, body['producer_ceremony'][key], audit_action, kind)
        consent._fresh(state, artifact)
    if before_effect:
        admission._collect(state.admission_view, state.session, state.primary, state.approval_id,
                           state.approval_sha256, state.reference)
    else:
        # Full pre-write manifest regeneration has already occurred under this
        # reservation. After our exact writes it must be verified as an actual
        # committed/staged operation, not regenerated as a second new action.
        permanent._verify_operation_records(state.target, body['operation_reference']['writer_manifest_sha256'])
    return action


def _event(decision, state, previous, kind, evidence):
    body = decision['authority']
    value = dict(format=journal.EVENT_FORMAT, authority_id=body['authority_id'], authority_sha256=digest(body),
        sequence=1 if previous is None else previous['sequence']+1, state=kind, at_utc=v._utc_now(),
        previous_sha256=None if previous is None else digest(previous), actor_id=body['runtime_target']['owner_id'], evidence=evidence)
    if previous is None: value['at_utc'] = decision['recorded_at_utc']
    return value


def _append_event(state, event):
    storage._insert(state.control, journal.HISTORY, storage._event_row(event))
    a._audit(state.control, 'runtime_finalization_'+event['state'].lower(), state.snapshot['owner_id'],
             event['at_utc'], dict(authority_id=event['authority_id'], authority_sha256=event['authority_sha256'],
                                  event_sha256=digest(event)))


def _start(attempt, outer):
    with _reserved(outer.config, outer.session, outer.primary, outer=outer) as state:
        action = _fresh(state)
        body = load(outer.authority_json)
        ref = body['operation_reference']
        require(not state.control.execute('SELECT 1 FROM '+journal.DECISIONS+
            ' WHERE authority_id=? OR operation_id=? OR writer_manifest_sha256=?',
            (body['authority_id'],ref['operation_id'],ref['writer_manifest_sha256'])).fetchone(),
            'finalization_decision_already_spent')
        decision = journal.validate_decision(dict(format=journal.DECISION_FORMAT,authority=body,recorded_at_utc=v._utc_now()))
        genesis = journal._genesis(decision)
        _mode(state, 'JOURNAL')
        storage._insert(state.control,journal.DECISIONS,storage._decision_row(decision))
        _append_event(state,genesis)
        require(state.control.total_changes == state.control_changes+3
                and state.target.total_changes == state.target_changes, 'finalization_start_write_count')
        _mode(state); _fresh(state)
        journal.inspect_rows(state.control,'control'); schema.check_control(state.control)
        _commit_control(state)
    # Z30 has a separately confirmed registration before its single execution
    # start. Failure here leaves an unused but permanently excluded decision.
    with _reserved(outer.config,outer.session,outer.primary,outer=outer) as state:
        require(_fresh(state)==action,'finalization_action_changed')
        row=state.control.execute('SELECT body_json FROM '+journal.DECISIONS+' WHERE authority_id=?',
                                  (body['authority_id'],)).fetchone()
        head=state.control.execute('SELECT body_json FROM '+journal.HISTORY+
            ' WHERE authority_id=? ORDER BY sequence DESC LIMIT 1',(body['authority_id'],)).fetchone()
        require(row is not None and row[0]==canonical(decision) and head is not None
                and head[0]==canonical(genesis),'finalization_decision_changed')
        pending=_event(decision,state,genesis,'TARGET_PENDING',dict(decision_sha256=digest(decision)))
        journal.validate_event(pending,decision=decision,previous=genesis)
        _mode(state,'JOURNAL');_append_event(state,pending);_mode(state)
        require(state.control.total_changes==state.control_changes+2
                and state.target.total_changes==state.target_changes,'finalization_pending_write_count')
        _fresh(state);journal.inspect_rows(state.control,'control');_commit_control(state)
    return decision, pending, action


def _commit_target(state):
    """Original manager only; effects and witness share this target commit."""
    require(_state(state.context) is state,'finalization_context_invalid')
    _invalidate(state);state.lifecycle=True
    try:
        state.target.commit()
        state.target_committed=True
    finally:state.lifecycle=False


def finalize(attempt, target_entry):
    """One genuine original attempt + exact durable entry; no replacement inputs."""
    original = coordinator._attempt_entry(attempt)
    entry = metadata._results.get(target_entry) if type(target_entry) is metadata.TargetEntry else None
    require(entry is not None and entry['attempt'] is attempt, 'finalization_original_entry_required')
    target_entry.snapshot  # Genuine original-lifetime inspection, not writer authority.
    outer = original['outer']
    _require_entitlement_owner(outer.config,outer.finalization_issuer,outer.session,outer.primary)
    require(attempt not in _spent and outer.finalization_issuer is not None, 'finalization_original_attempt_spent')
    _spent[attempt] = True
    decision, pending, action = _start(attempt,outer)
    with _reserved(outer.config,outer.session,outer.primary,outer=outer) as state:
        require(_fresh(state) == action, 'finalization_action_changed')
        current = state.control.execute('SELECT body_json FROM '+journal.HISTORY+
            ' WHERE authority_id=? ORDER BY sequence DESC LIMIT 1',(action['authority_id'],)).fetchone()
        require(current is not None and current[0] == canonical(pending), 'finalization_pending_changed')
        frozen = events.get_event(state.target,decision['authority']['operation_reference']['event_id'])
        manifest = frozen['preparation']['manifest']
        require(_write_set(manifest) == action['intent']['write_set_sha256'], 'finalization_write_set_mismatch')
        expected = permanent._prepare(state.target,manifest['family'],manifest['inputs'],
                                      manifest['evaluation_at_utc'],manifest['authorization_reference'])
        require(expected == manifest, 'finalization_stale_preparation')
        require(not state.target.execute('SELECT 1 FROM recognition_private_operations WHERE operation_id=?',
                                        (digest(manifest),)).fetchone(), 'finalization_existing_effect')
        family_before = effects._family_snapshot(state.target)
        excluded = (*effects.TABLES,journal.WITNESSES)
        protected_target = _data(state.target,exclude=excluded)
        _mode(state, 'EFFECT',query_only=False)
        _fresh(state)
        permanent._insert_family_effects(state.target,manifest,sealed_at=v._utc_now())
        effects._verify_delta(state.target,manifest,family_before)
        state.effect_before=family_before;state.effect_manifest=manifest;state.protected_target=protected_target
        evidence = effects._evidence(state.target,manifest,decision,pending)
        witness = journal.validate_witness(dict(format=journal.WITNESS_FORMAT,decision=decision,pending=pending,
            recorded_at_utc=v._utc_now(),outcome='TARGET_COMMITTED',effect_evidence_sha256=digest(evidence)))
        storage._insert(state.target,journal.WITNESSES,storage._witness_row(witness))
        effects._verify_delta(state.target,manifest,family_before)
        require(_data(state.target,exclude=excluded) == protected_target
                and _data(state.control) == state.original_control, 'finalization_unexpected_write')
        _mode(state,query_only=True)
        _fresh(state,before_effect=False)
        require(state.target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                and not state.target.execute('PRAGMA foreign_key_check').fetchone(), 'finalization_target_integrity')
        staged=state.target.execute('SELECT body_json,body_sha256 FROM '+journal.WITNESSES+
            ' WHERE authority_id=?',(action['authority_id'],)).fetchone()
        require(staged is not None and staged[0]==canonical(witness) and staged[1]==digest(witness),
                'finalization_witness_mismatch')
        _commit_target(state)
        with p._owned_connection(outer.config.target,state) as verified:
            state.bind(state.control,verified)
            verified.execute('BEGIN IMMEDIATE'); verified.execute('PRAGMA query_only=ON')
            state.target_reservation_epoch += 1
            verified.set_authorizer(state.target_authorizer)
            _register(state)
            _fresh(state,before_effect=False)
            actual = verified.execute('SELECT body_json,body_sha256 FROM '+journal.WITNESSES+
                                      ' WHERE authority_id=?',(action['authority_id'],)).fetchone()
            require(actual is not None and actual[0] == canonical(witness) and actual[1] == digest(witness),
                    'finalization_witness_mismatch')
            effects._verify_witness_effect(verified,manifest,decision,pending,witness)
            completed = _event(decision,state,pending,'COMPLETED',
                dict(pending_sha256=digest(pending),witness_sha256=digest(witness)))
            journal.validate_event(completed,decision=decision,previous=pending,pending=pending,witness=witness)
            _mode(state,'JOURNAL'); _append_event(state,completed); _mode(state)
            require(state.control.total_changes == state.control_changes+2, 'finalization_outcome_write_count')
            journal.inspect_rows(state.control,'control',witnesses={action['authority_id']:witness})
            _commit_control(state)
    return MappingProxyType(dict(state='COMPLETED',authority_id=action['authority_id'],
        authority_sha256=action['authority_sha256'],witness_sha256=digest(witness),
        effect_evidence_sha256=witness['effect_evidence_sha256'],execution_authority=False,retry_authorized=False))


def inspect_outcome(config, authority_id, *, approval=None, authority=None):
    """Read-only durable diagnosis. No returned value can authorize execution."""
    from .trust import identity
    identity(authority_id); config.paths()
    if approval is not None:
        _isolated_config(config,approval)
        authorization.verify(config.target,approval,authority,family='runtime_finalization',permission='inspection',
                             action='inspect_outcome',reference=authority_id)
    else:
        roots=[entry for entry in _entitlements.values() if entry['config']==config and entry['pid']==os.getpid()]
        require(bool(roots),'finalization_disposable_inspection_required')
        _isolated_config(config,roots[0]['approval'])
    with a.connect(config.control) as control, a.connect(config.target) as target:
        control.execute('BEGIN'); target.execute('BEGIN')
        schema.check_control(control); journal.check_schema(target,'target')
        row = control.execute('SELECT body_json,body_sha256 FROM '+journal.DECISIONS+' WHERE authority_id=?',(authority_id,)).fetchone()
        require(row is not None,'finalization_decision_missing')
        decision = journal.parse_decision(row[0],expected_sha256=row[1])
        body = decision['authority']
        if approval is not None and approval.environment=='production':
            require(approval.operation_sha256==digest(body),'finalization_inspection_authority_mismatch')
        current_binding=load(control.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
        target_scope=target.execute('SELECT installation_id,target_id FROM recognition_local_installation').fetchone()
        require(digest(current_binding)==body['runtime_target']['binding_sha256']
                and target_scope is not None and target_scope['installation_id']==body['runtime_target']['installation_id']
                and target_scope['target_id']==body['runtime_target']['target_id'], 'finalization_inspection_scope')
        require(asdict(a.target_identity(control)) == body['physical_snapshot']['control_identity']
                and a.observe_target(target) == body['physical_snapshot']['target'], 'finalization_inspection_identity')
        history = control.execute('SELECT body_json FROM '+journal.HISTORY+' WHERE authority_id=? ORDER BY sequence',(authority_id,)).fetchall()
        pending = next((load(r[0]) for r in history if load(r[0])['state']=='TARGET_PENDING'),None)
        last = load(history[-1][0]) if history else None
        witness_row = target.execute('SELECT body_json,body_sha256 FROM '+journal.WITNESSES+' WHERE authority_id=?',(authority_id,)).fetchone()
        committed = False
        if witness_row is not None:
            witness = journal.parse_witness(witness_row[0],expected_sha256=witness_row[1])
            require(witness['decision'] == decision and witness['pending'] == pending,'finalization_inspection_binding')
            manifest = events.get_event(target,body['operation_reference']['event_id'])['preparation']['manifest']
            effects._verify_witness_effect(target,manifest,decision,pending,witness)
            committed=True
            if last['state']=='COMPLETED':
                journal.validate_event(last,decision=decision,previous=pending,pending=pending,witness=witness)
        require(last is not None and (last['state']!='COMPLETED' or committed),'finalization_false_completion')
        return MappingProxyType(dict(authority_id=authority_id,authority_sha256=digest(body),
            state=last['state'],target_commit_verified=committed,execution_authority=False,retry_authorized=False))
