"""Trusted-local G+1 schema transition. No runtime enrollment or writer authority.

Only the original synchronous maintenance call can move a committed prefix
forward. Any exception poisons that continuation; historical inspection cannot
recreate it. Control and target commits are deliberately independent.
"""

from contextlib import contextmanager, closing
from dataclasses import asdict
from pathlib import Path
import os
import sqlite3
import tempfile
import threading
import time

from . import administration as a, administration_schema as base, approvals
from . import runtime_enrollment_transition_schema as storage
from . import runtime_target_entry_storage as package
from . import runtime_validation as runtime, runtime_challenges, local_readiness
from . import runtime_execution_attempt_schema as attempts
from . import runtime_execution_claim_schema as claims
from . import enrollment
from .rules import canonical, digest
from .trust import require, load


def _objects(conn):
    return [tuple(r) for r in conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]


def _data(conn, *, exclude=()):
    """Exact typed logical snapshot, including BLOBs/floats; never persisted/logged."""
    result = []
    for name, in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        if name not in exclude:
            quoted = '"'+name.replace('"','""')+'"'
            result.append((name, sorted(repr(tuple(row)) for row in conn.execute('SELECT * FROM '+quoted))))
    return result


def _integrity(conn):
    require([r[0] for r in conn.execute('PRAGMA integrity_check')] == ['ok']
            and not conn.execute('PRAGMA foreign_key_check').fetchone(), 'transition_integrity_failure')


def _inventory(control, target):
    """Reject orphan ACKs/proposals and downstream residue without minting a read view."""
    from . import runtime_proposal_records as records, runtime_operation_contract as contract
    acknowledgements = {}
    for row in control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence'):
        body = records._record(row)
        if body['action'] == records.ACK_ACTION:
            records.parse_acknowledgement(row['body_json'],acknowledgement_sha256=row['body_sha256'])
            oid=body['subject']['operation_id']
            require(oid not in acknowledgements, 'transition_conflicting_acknowledgements')
            acknowledgements[oid]=body['subject']
    proposals=set()
    for row in target.execute('SELECT * FROM recognition_operation_contracts'):
        body=load(row['body_json'])
        require(canonical(body)==row['body_json'] and digest(body)==row['body_sha256'], 'transition_operation_integrity')
        if body.get('format')==contract.OPERATION_FORMAT:
            oid=row['operation_id'];proposals.add(oid)
            require(acknowledgements.get(oid)==records._subject(body,row['body_sha256']), 'transition_orphan_proposal')
    require(proposals==set(acknowledgements), 'transition_orphan_acknowledgement')
    for table in ('recognition_execution_seals','recognition_execution_audit','recognition_operation_receipts'):
        if target.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
            require(not target.execute('SELECT 1 FROM '+table).fetchone(), 'transition_downstream_inventory')
    if control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_execution_blocks'").fetchone():
        require(not control.execute('SELECT 1 FROM recognition_execution_blocks').fetchone(), 'transition_recovery_inventory')


def _package(plan):
    if plan["migration_id"]==storage.PACKAGE:return package
    from .runtime_finalization_schema_upgrade import PACKAGE, TargetPackage
    require(plan["migration_id"]==PACKAGE,"transition_package_mismatch")
    return TargetPackage


def _preview(target, *, migration_id=storage.PACKAGE):
    package=_package(dict(migration_id=migration_id))
    """Disposable schema-only computation with unchanged full fingerprint algorithm."""
    require(not any(name.startswith(package.TABLE) for _,name,_,_ in _objects(target)), 'transition_package_already_present')
    with tempfile.TemporaryDirectory() as directory:
        with closing(sqlite3.connect(Path(directory)/'preview.db')) as preview:
            # SQLite stores raw SQL when executing sqlite_master definitions.
            order = {'table':0,'index':1,'view':2,'trigger':3}
            for _,_,_,sql in sorted(_objects(target), key=lambda r:(order[r[0]],r[1])):
                require(sql is not None, 'transition_preview_unsupported_schema')
                preview.execute(sql)
            for pragma in ('application_id','user_version'):
                value = target.execute('PRAGMA '+pragma).fetchone()[0]
                preview.execute('PRAGMA '+pragma+'='+str(value))
            require(enrollment._schema(preview) == enrollment._schema(target), 'transition_preview_source_mismatch')
            for sql in package.definitions().values(): preview.execute(sql)
            package.check_schema(preview)
            return enrollment._schema(preview)


def _backup(source, path, config):
    require(isinstance(path,Path) and path.is_absolute() and path.resolve() not in
            (config.target.resolve(),config.control.resolve(),config.key_file.resolve()), 'transition_verified_backup_required')
    with a.connect(path) as backup:
        backup.execute('BEGIN')
        require(enrollment._schema(backup) == enrollment._schema(source)
                and _data(backup) == _data(source), 'transition_backup_mismatch')
        # integrity_check may materialize SQLite's temp schema. Fingerprint
        # checks intentionally require a main-only connection, so perform them
        # first and discard this read-only connection after integrity checking.
        _integrity(backup)


def _insert(conn, table, row):
    conn.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",tuple(row.values()))


def _commit(conn, stage):
    """Private manager commit boundary, also usable for fault injection in tests."""
    conn.commit()
    require(not conn.in_transaction, 'transition_commit_unconfirmed')


class _Owner:
    __slots__ = ('config','plan','pid','thread','last_time','last_tick','alive','binding','profile','data','objects')

    def __init__(self, config, plan):
        self.config, self.plan = config, plan
        self.pid, self.thread = os.getpid(), threading.get_ident()
        self.last_time, self.last_tick, self.alive = None, time.monotonic(), True
        self.binding = self.profile = self.data = self.objects = None

    def __reduce_ex__(self, protocol):
        raise TypeError('nonserializable_transition_owner')

    def now(self):
        require(self.alive and self.pid == os.getpid() and self.thread == threading.get_ident(), 'transition_owner_invalid')
        now = runtime._utc_now(); tick = time.monotonic()
        storage.validate_expiry(self.plan,now=now)
        moment = a.timestamp(now)
        require(tick >= self.last_tick and (self.last_time is None or moment >= self.last_time), 'transition_clock_rollback')
        self.last_time,self.last_tick = moment,tick
        return now

    @contextmanager
    def phase(self):
        self.now()
        with a.connect(self.config.control,write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            base.check_control(control); a._audit_head(control)
            with a.connect(self.config.target,write=True) as target:
                target.execute('BEGIN IMMEDIATE'); target.execute('PRAGMA query_only=ON')
                try:
                    yield control,target
                except BaseException:
                    self.alive=False
                    raise
                finally:
                    # Target release is always after the control commit/rollback.
                    if control.in_transaction: control.rollback()
                    if target.in_transaction: target.rollback()

    def fresh(self, control, target, *, installed=False, prefix=0):
        now=self.now(); plan=self.plan; package=_package(plan)
        require(control.in_transaction and target.in_transaction
                and target.execute('PRAGMA query_only').fetchone()[0] == 1, 'transition_reservation_lost')
        base.check_control(control)
        require(storage.present(control), 'transition_storage_missing')
        binding,profile,_ = runtime._history(control)
        require(binding['generation'] == plan['source_generation']
                and digest(binding) == plan['source_binding_sha256']
                and binding['runtime_profile_sha256'] == plan['source_profile_sha256']
                and all(binding[k] == plan[k] for k in ('installation_id','target_id','owner_id')),
                'transition_source_changed')
        require(binding['target']['schema_sha256'] == plan['target_schema']['before_sha256']
                == profile['target_schema_sha256'], 'transition_source_fingerprint_mismatch')
        require(asdict(a.target_identity(control)) == binding['control_identity'], 'control_identity_mismatch')
        expected = operation_copy(binding)
        if installed: expected['target']['schema_sha256']=plan['target_schema']['after_sha256']
        a._verify(self.config,control,target,expected)
        require(plan['control_schema_sha256'] == claims.manifest(control), 'transition_control_schema_changed')
        metadata=target.execute(f'SELECT * FROM {base.TARGET_TABLE}').fetchone()
        owner=target.execute('SELECT role,email_verified_at FROM community_reviewers WHERE id=?',(plan['owner_id'],)).fetchone()
        mfa=control.execute('SELECT state,epoch FROM recognition_admin_mfa WHERE actor=?',(plan['owner_id'],)).fetchone()
        require(owner and owner['role']=='owner' and owner['email_verified_at'] and metadata['auth_epoch']==plan['source_auth_epoch']
                and mfa and mfa['state']=='ENROLLED' and mfa['epoch']==plan['source_mfa_epoch'], 'transition_owner_epoch_changed')
        head=control.execute('SELECT * FROM recognition_local_activation ORDER BY sequence DESC LIMIT 1').fetchone()
        require(head and dict(sequence=head['sequence'],event_sha256=head['body_sha256'],state=load(head['body_json'])['state'])==plan['activation_head']
                and binding['production_state']=='NOT_ACTIVATED'
                and local_readiness._state(control,binding)['state'] in ('NOT_ACTIVATED','DEACTIVATED'), 'transition_activation_changed')
        require(not control.execute(f'SELECT 1 FROM {attempts.ATTEMPTS}').fetchone()
                and not control.execute(f'SELECT 1 FROM {claims.CLAIMS}').fetchone()
                and not control.execute(f'SELECT 1 FROM {storage.authority.AUTHORITIES}').fetchone(), 'transition_unsettled_runtime_work')
        require(not target.execute('SELECT 1 FROM recognition_execution_claims').fetchone(), 'transition_unsettled_legacy_work')
        _inventory(control,target)
        # Proposal/approval history is retained and invalidated, never converted.
        execution = target.execute("SELECT state FROM recognition_operation_executions e WHERE sequence=(SELECT max(sequence) FROM recognition_operation_executions WHERE operation_id=e.operation_id)").fetchall()
        require(all(row[0] in ('NOT_STARTED','COMPLETED','COMPLETED_WITH_QUARANTINE','FAILED_BEFORE_COMMIT') for row in execution), 'transition_unsettled_legacy_work')
        require(not control.execute(f'SELECT 1 FROM {storage.PLANS} q WHERE q.plan_id<>? AND NOT EXISTS('
            f'SELECT 1 FROM {storage.HISTORY} h WHERE h.plan_id=q.plan_id AND h.sequence=4)',(plan['plan_id'],)).fetchone(),
            'transition_other_pending_plan')
        rows=control.execute(f'SELECT * FROM {storage.PLANS} WHERE plan_id=?',(plan['plan_id'],)).fetchall()
        if prefix:
            require(len(rows)==1 and rows[0]['body_json']==canonical(plan) and rows[0]['body_sha256']==digest(plan), 'transition_pending_plan_changed')
            require(control.execute(f'SELECT max(sequence) FROM {storage.HISTORY} WHERE plan_id=?',(plan['plan_id'],)).fetchone()[0]==prefix, 'transition_prefix_changed')
            require(not control.execute('SELECT 1 FROM recognition_admin_primary WHERE revoked=0').fetchone()
                    and not control.execute('SELECT 1 FROM recognition_admin_sessions WHERE revoked=0').fetchone()
                    and not control.execute('SELECT 1 FROM recognition_admin_stepups').fetchone()
                    and not control.execute('SELECT 1 FROM recognition_admin_confirmations WHERE used=0').fetchone(), 'transition_auth_not_revoked')
        else:
            require(not rows, 'transition_already_recorded_inspection_required')
        if self.data is None:
            self.data,self.objects,self.binding,self.profile = _data(target),_objects(target),binding,profile
        require(_data(target,exclude=(package.TABLE,) if installed else ())==self.data, 'transition_target_data_changed')
        if installed:
            package.check_schema(target)
            require(not target.execute(f'SELECT 1 FROM {package.TABLE}').fetchone(), 'transition_created_entry')
            added = package.definitions()
            require([r for r in _objects(target) if r[1] not in added]==self.objects, 'transition_original_schema_changed')
        else:
            require(_objects(target)==self.objects, 'transition_original_schema_changed')
        require(a.timestamp(now)>=a.timestamp(load(a._audit_head(control)['body_json'])['at_utc']), 'transition_audit_clock')
        return now

    def event(self, control, sequence, now, evidence, binding=None):
        plan=self.plan
        prior=control.execute(f'SELECT body_sha256 FROM {storage.HISTORY} WHERE plan_id=? ORDER BY sequence DESC LIMIT 1',(plan['plan_id'],)).fetchone()
        event=dict(format=storage.EVENT_FORMAT,plan_id=plan['plan_id'],plan_sha256=digest(plan),sequence=sequence,
            state=storage.STATES[sequence-1],at_utc=now,previous_sha256=prior[0] if prior else None,
            actor_id=plan['owner_id'],operator=plan['operator'],reason=plan['reason'],evidence=evidence)
        storage.validate_event(event)
        audit=a._audit_head(control)['sequence']+1
        _insert(control,storage.HISTORY,dict(plan_id=plan['plan_id'],sequence=sequence,state=event['state'],at=a.timestamp(now),
            previous_sha256=event['previous_sha256'],body_json=canonical(event),body_sha256=digest(event),audit_sequence=audit,
            destination_generation=binding['generation'] if binding else None,
            destination_binding_sha256=digest(binding) if binding else None,destination_profile_sha256=None))
        if binding:
            control.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(binding['generation'],canonical(binding),digest(binding)))
        a._audit(control,storage.ACTIONS[sequence-1],plan['operator'],now,
            dict(plan_id=plan['plan_id'],plan_sha256=digest(plan),event_sequence=sequence,event_sha256=digest(event)))
        base.check_control(control); a._audit_head(control)


def operation_copy(value):
    return load(canonical(value))


def transition(config, *, plan, plan_sha256, target_backup, control_backup):
    """Trusted deployment ceremony only. Caller supplies expectations, never SQL/authority.

    Requires independently created, exact verified backup files. No restart or
    existing-plan continuation API exists; every repeated call fails closed.
    """
    require(type(config) is a.LocalAdministration, 'local_administration_required'); config.paths()
    plan=storage.parse_plan(canonical(plan),plan_sha256=plan_sha256)
    package=_package(plan)
    require(package.PACKAGE==plan['migration_id']
            and digest(package.definitions())==plan['target_schema']['added_definitions_sha256'], 'transition_package_mismatch')
    owner=_Owner(config,plan)
    try:
        with owner.phase() as (control,target):
            owner.fresh(control,target)
            require(_preview(target,migration_id=plan['migration_id'])==plan['target_schema']['after_sha256'], 'transition_preview_mismatch')
            _backup(target,target_backup,config); _backup(control,control_backup,config)
            now=owner.fresh(control,target)
            a._invalidate(control); approvals._invalidate_all(control,plan['operator'],now,'target-schema-transition')
            row={k:plan[k] for k in ('plan_id','installation_id','source_generation','source_binding_sha256','source_profile_sha256')}
            row.update(created_at=a.timestamp(plan['created_at_utc']),deadline_at=a.timestamp(plan['deadline_at_utc']),
                body_json=canonical(plan),body_sha256=digest(plan),audit_sequence=a._audit_head(control)['sequence']+1)
            _insert(control,storage.PLANS,row)
            owner.event(control,1,now,{k:plan[k] for k in storage.EVIDENCE[0]})
            owner.fresh(control,target,prefix=1); _commit(control,'prepared')
        with owner.phase() as (control,target):
            now=owner.fresh(control,target,prefix=1)
            previous=control.execute(f'SELECT body_sha256 FROM {storage.HISTORY} WHERE plan_id=? AND sequence=1',(plan['plan_id'],)).fetchone()[0]
            owner.event(control,2,now,dict(prepared_event_sha256=previous))
            owner.fresh(control,target,prefix=2); _commit(control,'intent')
        with owner.phase() as (control,target):
            owner.fresh(control,target,prefix=2)
            require(_preview(target,migration_id=plan['migration_id'])==plan['target_schema']['after_sha256'], 'transition_preview_mismatch')
            before=target.total_changes
            target.execute('PRAGMA query_only=OFF')
            def ddl_only(action, arg1, arg2, database, trigger):
                if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
                    return sqlite3.SQLITE_OK if arg1 in ('sqlite_master','sqlite_schema') else sqlite3.SQLITE_DENY
                if action==sqlite3.SQLITE_CREATE_TABLE:
                    return sqlite3.SQLITE_OK if arg1==package.TABLE else sqlite3.SQLITE_DENY
                if action==sqlite3.SQLITE_CREATE_TRIGGER:
                    return sqlite3.SQLITE_OK if arg1 in package.definitions() and arg2==package.TABLE else sqlite3.SQLITE_DENY
                if action==sqlite3.SQLITE_CREATE_INDEX:
                    return sqlite3.SQLITE_OK if arg2==package.TABLE else sqlite3.SQLITE_DENY
                if action in (sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH,sqlite3.SQLITE_ALTER_TABLE,
                              sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_DROP_TRIGGER,sqlite3.SQLITE_DROP_INDEX):
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            target.set_authorizer(ddl_only)
            for sql in package.definitions().values(): target.execute(sql)
            target.execute('PRAGMA query_only=ON')
            owner.fresh(control,target,installed=True,prefix=2)
            require(target.total_changes==before, 'transition_target_dml')
            _integrity(target)
            _commit(target,'target')
            # Planned postcommit connection replacement discards the old
            # reservation AND integrity_check's temp schema. It is not recovery:
            # any failure poisons this call; control remains reserved throughout.
            with a.connect(config.target,write=True) as observed:
                observed.execute('BEGIN IMMEDIATE'); observed.execute('PRAGMA query_only=ON')
                now=owner.fresh(control,observed,installed=True,prefix=2)
                bound=operation_copy(owner.binding)
                bound.update(generation=plan['source_generation']+1,previous_sha256=digest(owner.binding),
                    at_utc=now,runtime_profile_sha256=None,production_state='NOT_ACTIVATED')
                bound['target']['schema_sha256']=plan['target_schema']['after_sha256']
                previous=control.execute(f'SELECT body_sha256 FROM {storage.HISTORY} WHERE plan_id=? AND sequence=2',(plan['plan_id'],)).fetchone()[0]
                owner.event(control,3,now,dict(intent_event_sha256=previous,observed_schema_sha256=plan['target_schema']['after_sha256'],
                    generation=bound['generation'],binding_sha256=digest(bound)),binding=bound)
                require(runtime_challenges._deployment_binding(control)==bound, 'transition_destination_changed')
                a._verify(config,control,observed,bound)
                require(asdict(a.target_identity(control))==bound['control_identity'], 'control_identity_mismatch')
                require(_data(observed,exclude=(package.TABLE,))==owner.data, 'transition_target_data_changed')
                _integrity(observed)
                owner.now()
                _commit(control,'schema_bound')
                require(observed.in_transaction, 'transition_reservation_lost')
                with a.connect(config.control) as verification:
                    verification.execute('BEGIN');base.check_control(verification);_integrity(verification)
                    require(runtime_challenges._deployment_binding(verification)==bound, 'transition_commit_unconfirmed')
        owner.alive=False
        return dict(plan_id=plan['plan_id'],plan_sha256=digest(plan),state='SCHEMA_BOUND',generation=bound['generation'],
            production_state='NOT_ACTIVATED',runtime_profile_sha256=None,execution_authority=False,retry_authorized=False,
            target_ddl_count=len(package.definitions()),target_dml_count=0,target_commit_count=1,writer_capability_count=0,execution_count=0)
    finally:
        owner.alive=False


inspect_transition=storage.inspect_transition


def _schema_bound(config, control, target, plan_id, plan_sha256, now):
    """Resolve the exact unfinished B1 graph, never runtime authentication."""
    base.check_control(control); a._audit_head(control)
    row=control.execute(f'SELECT * FROM {storage.PLANS} WHERE plan_id=?',(plan_id,)).fetchone()
    require(row is not None and row['body_sha256']==plan_sha256, 'transition_plan_mismatch')
    plan=storage.parse_plan(row['body_json'],plan_sha256=plan_sha256)
    storage.validate_expiry(plan,now=now)
    histories=control.execute(f'SELECT * FROM {storage.HISTORY} WHERE plan_id=? ORDER BY sequence',(plan_id,)).fetchall()
    require(len(histories)==3 and histories[-1]['state']=='SCHEMA_BOUND', 'transition_requires_schema_bound')
    require(control.execute(f'SELECT count(*) FROM {storage.PLANS} q WHERE NOT EXISTS(SELECT 1 FROM {storage.HISTORY} h WHERE h.plan_id=q.plan_id AND h.sequence=4)').fetchone()[0]==1,
            'transition_conflicting_pending_plan')
    bound=runtime_challenges._deployment_binding(control)
    require(bound['generation']==plan['source_generation']+1 and bound['runtime_profile_sha256'] is None
            and digest(bound)==histories[-1]['destination_binding_sha256'], 'transition_schema_binding_mismatch')
    source,profile=storage._source(control,plan)
    require(source['runtime_profile_sha256']==profile['profile_sha256'] and
            bound['target']['schema_sha256']==plan['target_schema']['after_sha256'], 'transition_profile_source_mismatch')
    require(asdict(a.target_identity(control))==bound['control_identity'], 'control_identity_mismatch')
    require(control.in_transaction and target.in_transaction and target.execute('PRAGMA query_only').fetchone()[0]==1,
            'transition_reservation_lost')
    package=_package(plan)
    a._verify(config,control,target,bound); package.check_schema(target)
    require(package.PACKAGE==plan['migration_id'] and digest(package.definitions())==plan['target_schema']['added_definitions_sha256'],
            'transition_package_mismatch')
    require(not target.execute(f'SELECT 1 FROM {package.TABLE}').fetchone(), 'transition_created_entry')
    owner=target.execute('SELECT role,email_verified_at FROM community_reviewers WHERE id=?',(plan['owner_id'],)).fetchone()
    epoch=target.execute(f'SELECT auth_epoch FROM {base.TARGET_TABLE}').fetchone()
    mfa=control.execute('SELECT state,epoch FROM recognition_admin_mfa WHERE actor=?',(plan['owner_id'],)).fetchone()
    require(owner and owner['role']=='owner' and owner['email_verified_at'] and epoch[0]==plan['source_auth_epoch']
            and mfa and mfa['state']=='ENROLLED' and mfa['epoch']==plan['source_mfa_epoch'], 'transition_owner_epoch_changed')
    head=control.execute('SELECT * FROM recognition_local_activation ORDER BY sequence DESC LIMIT 1').fetchone()
    require(head and dict(sequence=head['sequence'],event_sha256=head['body_sha256'],state=load(head['body_json'])['state'])==plan['activation_head']
            and bound['production_state']=='NOT_ACTIVATED' and local_readiness._state(control,bound)['state']=='NOT_ACTIVATED',
            'transition_activation_changed')
    require(a.timestamp(now)>=a.timestamp(load(a._audit_head(control)['body_json'])['at_utc']), 'transition_audit_clock')
    require(not control.execute(f'SELECT 1 FROM {attempts.ATTEMPTS}').fetchone()
            and not control.execute(f'SELECT 1 FROM {claims.CLAIMS}').fetchone()
            and not control.execute(f'SELECT 1 FROM {storage.authority.AUTHORITIES}').fetchone(), 'transition_unsettled_runtime_work')
    require(not target.execute('SELECT 1 FROM recognition_execution_claims').fetchone(), 'transition_unsettled_legacy_work')
    _inventory(control,target)
    return plan,bound,profile,dict(histories[-1])


def enroll_transition_runtime_profile(config, serialized_review, nonce, *, plan_id, plan_sha256,
        expected_generation, installation_id, target_id, owner_id, source_binding_sha256,
        challenge_id, challenge_sha256, approved_review_sha256, approved_observation_sha256,
        operator, reason, confirm_private_log_review, confirm_enroll_runtime_profile):
    """Explicit local private-log approval; atomic enrollment + FINALIZED, no activation.

    Unsigned evidence/nonce/flags do not authenticate the runtime. Host access and
    the operator's independent private-log review remain the provenance boundary.
    """
    import hashlib
    import hmac
    from . import runtime_enrollment as codec, runtime_evidence as evidence, runtime_profile_schema as profiles
    require(type(config) is a.LocalAdministration, 'local_administration_required');config.paths()
    require(confirm_private_log_review is True and confirm_enroll_runtime_profile is True,
            'explicit_runtime_enrollment_approval_required')
    codec._text(operator,200);codec._text(reason,2000)
    codec._integer(expected_generation,1,2**63-2);codec._integer(owner_id,1,2**63-1)
    for value in (plan_id,installation_id,target_id,challenge_id): storage.identity(value)
    for value in (plan_sha256,source_binding_sha256,challenge_sha256,approved_review_sha256,approved_observation_sha256):profiles._check_sha(value)
    review,selected=codec._approved_review(serialized_review,nonce,approved_review_sha256=approved_review_sha256,
        approved_observation_sha256=approved_observation_sha256,operator=operator,reason=reason)
    # This owner is local to one synchronous call; no continuation is published.
    with a.connect(config.control,write=True) as control:
        control.execute('BEGIN IMMEDIATE')
        with a.connect(config.target,write=True) as target:
            target.execute('BEGIN IMMEDIATE');target.execute('PRAGMA query_only=ON')
            try:
                now=runtime._utc_now();tick=time.monotonic()
                plan,old,old_profile,previous=_schema_bound(config,control,target,plan_id,plan_sha256,now)
                require(old['generation']==expected_generation and digest(old)==source_binding_sha256
                        and all(old[k]==v for k,v in (('installation_id',installation_id),('target_id',target_id),('owner_id',owner_id))),
                        'runtime_enrollment_scope_mismatch')
                challenge,checked=evidence._challenge(control,challenge_id,challenge_sha256,now)
                require(checked==old, 'runtime_enrollment_binding_changed')
                require(hmac.compare_digest(hashlib.sha256(nonce.encode('ascii')).hexdigest(),challenge['nonce_sha256']),
                        'runtime_enrollment_nonce_mismatch')
                codec.validate_review_scope(review,challenge,old,now)
                require(all(selected[k]==old_profile[k] for k in codec.PHYSICAL_FIELDS if k!='target_schema_sha256'),
                        'transition_runtime_physical_discontinuity')
                target_before=_data(target);changes=target.total_changes
                from .execution import _stop
                stop=_stop(control)
                generation=expected_generation+1
                a._invalidate(control);approvals._invalidate_all(control,operator,now,'runtime-transition-profile-enrolled')
                audit=a._audit_head(control)['sequence']+1
                profile=dict(format='recognition-runtime-profile-v1',installation_id=old['installation_id'],generation=generation,
                    role='runtime',**{k:selected[k] for k in codec.PHYSICAL_FIELDS},target_id=old['target_id'],owner_id=old['owner_id'],
                    challenge_id=challenge_id,observation_sha256=approved_observation_sha256,evidence_channel=evidence.CHANNEL,
                    observed_at=selected['observed_at'],created_at=a.timestamp(now),operator=operator,reason=reason,audit_sequence=audit)
                profile['profile_sha256']=digest(profile)
                bound=dict(old,generation=generation,previous_sha256=digest(old),at_utc=now,runtime_profile_sha256=profile['profile_sha256'])
                event=dict(format=storage.EVENT_FORMAT,plan_id=plan_id,plan_sha256=plan_sha256,sequence=4,state='FINALIZED',
                    at_utc=now,previous_sha256=previous['body_sha256'],actor_id=plan['owner_id'],operator=operator,reason=reason,
                    evidence=dict(schema_bound_event_sha256=previous['body_sha256'],generation=generation,binding_sha256=digest(bound),
                        profile_sha256=profile['profile_sha256'],challenge_sha256=challenge_sha256,
                        observation_sha256=approved_observation_sha256,review_sha256=approved_review_sha256))
                storage.validate_event(event)
                # Deferred FKs require the complete graph before the single commit.
                _insert(control,storage.HISTORY,dict(plan_id=plan_id,sequence=4,state='FINALIZED',at=a.timestamp(now),
                    previous_sha256=event['previous_sha256'],body_json=canonical(event),body_sha256=digest(event),audit_sequence=audit+1,
                    destination_generation=generation,destination_binding_sha256=digest(bound),destination_profile_sha256=profile['profile_sha256']))
                _insert(control,profiles.PROFILES,profile)
                control.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(generation,canonical(bound),digest(bound)))
                a._audit(control,'runtime_profile_enrolled',operator,now,dict(reason=reason,previous_generation=expected_generation,
                    generation=generation,source_binding_sha256=digest(old),binding_sha256=digest(bound),challenge_sha256=challenge_sha256,
                    profile_sha256=profile['profile_sha256'],observation_sha256=approved_observation_sha256,
                    review_sha256=approved_review_sha256,private_log_review_confirmed=True,enrollment_confirmed=True,review=review))
                a._audit(control,storage.ACTIONS[3],operator,now,dict(plan_id=plan_id,plan_sha256=plan_sha256,event_sequence=4,event_sha256=digest(event)))
                base.check_control(control)
                actual,_,_=runtime._history(control)
                require(actual==bound, 'transition_destination_changed')
                a._verify(config,control,target,bound)
                require(asdict(a.target_identity(control))==bound['control_identity'], 'control_identity_mismatch')
                require(_data(target)==target_before and target.total_changes==changes and target.execute('PRAGMA query_only').fetchone()[0]==1,
                        'transition_target_changed')
                require(_stop(control)==stop, 'transition_emergency_stop_changed')
                final=runtime._utc_now();storage.validate_expiry(plan,now=final)
                require(time.monotonic()>=tick and a.timestamp(now)<=a.timestamp(final)<challenge['expires_at'], 'transition_expired_or_clock_rollback')
                # Profile, binding, unchanged enrollment audit and FINALIZED audit
                # are all durable or none are. Target reservation remains held.
                _commit(control,'runtime_profile_finalized')
                require(target.in_transaction, 'transition_reservation_lost')
                with a.connect(config.control) as verified:
                    verified.execute('BEGIN');base.check_control(verified)
                    require(runtime._history(verified)[0]==bound, 'transition_commit_unconfirmed')
            except BaseException:
                if control.in_transaction:control.rollback()
                raise
    return dict(plan_id=plan_id,state='FINALIZED',generation=generation,profile_sha256=profile['profile_sha256'],
                production_state='NOT_ACTIVATED',execution_authority=False,retry_authorized=False,runtime_authentication_issued=False)


def inspect_runtime_profile_transition(control_path, *, plan_id):
    """Read-only control history, never a jointly verified target/runtime credential."""
    from .runtime_execution_admission import _freeze
    result=dict(storage.inspect_transition(control_path,plan_id=plan_id))
    result['profile_result_authority']=False
    if result['status']=='MALFORMED':result['status']='CONFLICTING_OR_UNCERTAIN'
    # A separately committed P1/G+2-prepared state is forbidden by deferred
    # constraints/guards. Such a partial graph is corruption, not resumable work.
    return _freeze(result)
