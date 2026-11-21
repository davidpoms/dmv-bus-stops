"""Closed, signed G5→G6 maintenance owner. No DDL, target DML or runtime authority."""
import base64
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import hmac
from pathlib import Path
import secrets
import sqlite3
import os
import threading
from types import SimpleNamespace
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from . import administration as a, runtime_validation as runtime, runtime_profile_schema as profiles
from . import runtime_enrollment as enrollment, runtime_evidence as evidence
from . import runtime_production_governance as governance, runtime_profile_successor_contract as contract
from .rules import canonical, digest
from .trust import load

PREPARED = 'runtime_profile_successor_challenge_issued'
COMMITTED = 'runtime_profile_device_successor_committed'
INVALIDATIONS = ['primary_proofs', 'admin_sessions', 'stepups', 'confirmations', 'outstanding_approvals']
_owners = {}


def _need(value, code='runtime_successor_invalid'):
    a.need(value, code, 503)


def _root(config):
    from .runtime_target_schema_lineage import _protected_root
    root = _protected_root(config)
    public = base64.b64decode(root['public_key'], validate=True)
    _need(len(public) == 32 and base64.b64encode(public).decode() == root['public_key'])
    return root, public


def _signed(config, envelope, kind, *, at=None, control=None, event=None):
    contract.fields(envelope, 'serialized_approval signature')
    encoded = envelope['serialized_approval']
    _need(type(encoded) is str and len(encoded.encode('utf-8')) <= 262144)
    body = load(encoded)
    if at is None:
        _need(control is None and event is None, 'runtime_successor_history_context')
        root, public = _root(config)
    else:
        from .runtime_governance_recovery import historical_root
        _need(control is not None and event is not None and at == event['at_utc']
              and event['subject'].get('authorization') == envelope, 'runtime_successor_history_context')
        root = historical_root(config, control, event)
        public = base64.b64decode(root['public_key'], validate=True)
    contract.validate_envelope(body, root)
    _need(canonical(body) == encoded and body['subject']['kind'] == kind, 'runtime_successor_purpose')
    _need(type(envelope['signature']) is str and len(envelope['signature']) == 88, 'runtime_successor_signature')
    signature = base64.b64decode(envelope['signature'], validate=True)
    _need(base64.b64encode(signature).decode() == envelope['signature'])
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(signature, governance.DOMAIN+encoded.encode('utf-8'))
    except Exception:
        raise a.AdminError('runtime_successor_signature', 403) from None
    issued, expires = a.timestamp(body['issued_at_utc']), a.timestamp(body['expires_at_utc'])
    _need(issued <= a.timestamp(at or runtime._utc_now()) < expires <= issued+600, 'runtime_successor_expired')
    return body


def _wsgi():
    from flask import has_request_context, request
    _need(has_request_context() and request.environ.get('wsgi.version') == (1, 0), 'runtime_successor_wsgi_required')


@contextmanager
def _reserved(config, *, write=False):
    _need(type(config) is a.LocalAdministration)
    config.paths()
    with a.connect(config.control, write=write) as control, a.connect(config.target, write=write) as target:
        control.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        target.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        target.execute('PRAGMA query_only=ON')
        from . import deployment_qualification as qualification
        for db, path in ((control, config.control), (target, config.target)):
            _need(db.execute('PRAGMA journal_mode').fetchone()[0].lower() == 'delete', 'runtime_successor_journal')
            _need(db.execute('PRAGMA synchronous').fetchone()[0] == 2, 'runtime_successor_synchronization')
            # integrity_check may instantiate SQLite's temp schema. Keep it off
            # the canonical isolated control connection; do not relax its guard.
            with a.connect(path) as reader:
                qualification._integrity(reader)
        qualification.permissions(config)
        from .runtime_execution_claims import _Clock
        clock = _Clock()
        def authorize(action, first, second, *rest):
            if action == sqlite3.SQLITE_INSERT:
                return sqlite3.SQLITE_OK if write and first in (
                    profiles.CHALLENGES, profiles.PROFILES, 'recognition_admin_bindings', 'recognition_admin_audit',
                    'recognition_approval_history') else sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_UPDATE:
                return sqlite3.SQLITE_OK if write and (first, second) in (
                    ('recognition_admin_primary','revoked'), ('recognition_admin_sessions','revoked'),
                    ('recognition_admin_confirmations','used')) else sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_DELETE:
                return sqlite3.SQLITE_OK if write and first == 'recognition_admin_stepups' else sqlite3.SQLITE_DENY
            if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_ALTER_TABLE,
                          sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_CREATE_TRIGGER,
                          sqlite3.SQLITE_CREATE_VIEW, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_INDEX,
                          sqlite3.SQLITE_DROP_TRIGGER, sqlite3.SQLITE_DROP_VIEW,
                          sqlite3.SQLITE_CREATE_TEMP_TABLE, sqlite3.SQLITE_CREATE_TEMP_INDEX,
                          sqlite3.SQLITE_CREATE_TEMP_TRIGGER, sqlite3.SQLITE_CREATE_TEMP_VIEW,
                          sqlite3.SQLITE_DROP_TEMP_TABLE, sqlite3.SQLITE_DROP_TEMP_INDEX,
                          sqlite3.SQLITE_DROP_TEMP_TRIGGER, sqlite3.SQLITE_DROP_TEMP_VIEW):
                return sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_PRAGMA and first in (
                    'journal_mode','synchronous','query_only','foreign_keys','application_id','user_version','writable_schema') and second is not None:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        control.set_authorizer(authorize)
        _owners[control] = [clock, target, os.getpid(), threading.current_thread(), None]
        try:
            yield control, target
        finally:
            _owners.pop(control, None)
            control.set_authorizer(None)
            if control.in_transaction:
                control.rollback()
            if target.in_transaction:
                target.rollback()


def _scope(config, control, target, *, audit_sha256=None):
    from . import local_readiness, runtime_execution_claim_schema as claims, runtime_target_schema_lineage as foundation
    binding, profile, head = runtime._history(control)
    _need(binding['generation'] == 5 and digest(binding) == contract.SOURCE_BINDING
          and profile['profile_sha256'] == contract.SOURCE_PROFILE, 'runtime_successor_source')
    _need(not control.execute("SELECT 1 FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",
                              (COMMITTED,)).fetchone(), 'runtime_successor_conflicting_history')
    _need(not foundation.present(control), 'runtime_successor_foundation_present')
    _need(foundation.normalized_manifest(dict(a.schema._control_objects(control))) ==
          foundation.normalized_manifest(foundation.source_definitions()), 'runtime_successor_control_topology')
    _need(local_readiness._state(control, binding)['state'] == 'NOT_ACTIVATED', 'runtime_successor_inactive_required')
    # A generation-scoped inactive result must not erase an earlier activation.
    activation = [load(row[0]) for row in control.execute('SELECT body_json FROM recognition_local_activation')]
    _need(all(row['state'] == 'NOT_ACTIVATED' for row in activation), 'runtime_successor_previous_activation')
    observed, actual_control = evidence._observation(control, target, config.target, config.control, binding)
    actual = dict(target=observed['observation'], control=actual_control)
    original = {prefix: dict(hostname=profile['hostname'], database=profile[prefix+'_path'],
                            device=int(profile[prefix+'_device']), inode=int(profile[prefix+'_inode']))
                for prefix in ('target', 'control')}
    _need(canonical(original) == canonical(contract.SOURCE) and canonical(actual) == canonical(contract.destination()),
          'runtime_successor_physical_identity')
    _need(a.timestamp(runtime._utc_now()) >= a.timestamp(load(head['body_json'])['at_utc']), 'administrative_clock_rollback')
    # Closed pre-foundation topology. Absent target prerequisites are not queried.
    empty = ('recognition_runtime_execution_claims', 'recognition_runtime_execution_claim_history',
             'recognition_runtime_execution_authorities', 'recognition_runtime_execution_attempts',
             'recognition_execution_claims', 'recognition_execution_blocks', 'recognition_operation_contracts',
             'recognition_operation_receipts', 'recognition_execution_seals', 'recognition_execution_audit',
             'recognition_operation_executions', 'recognition_operation_decisions')
    for db in (control, target):
        for name in empty:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone():
                _need(not db.execute('SELECT 1 FROM '+name+' LIMIT 1').fetchone(), 'runtime_successor_work_present')
    from .runtime_proposal_records import ACK_ACTION
    _need(not control.execute("SELECT 1 FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",
                              (ACK_ACTION,)).fetchone(), 'runtime_successor_work_present')
    from .runtime_enrollment_transition_schema import require_no_pending
    require_no_pending(control)
    root, public = _root(config)
    _need(root['installation_id'] == binding['installation_id'] and root['owner_id'] == binding['owner_id'])
    owner = target.execute('SELECT reviewer_key FROM community_reviewers WHERE id=?', (binding['owner_id'],)).fetchone()
    from src.review.admin_dashboard import owner_access
    _need(owner is not None and owner_access(target, binding['owner_id'], owner[0])[0], 'recognition_owner_required')
    metadata = target.execute('SELECT auth_epoch FROM '+a.schema.TARGET_TABLE).fetchone()
    # Use the canonical target metadata table rather than a second identity store.
    mfa = control.execute('SELECT * FROM recognition_admin_mfa WHERE actor=?', (binding['owner_id'],)).fetchone()
    _need(mfa is not None and mfa['state'] == 'ENROLLED', 'mfa_enrollment_required')
    from . import admin_auth, execution
    admin_auth._cipher(config)  # Validate the existing protected host key; never expose it.
    _need(execution._stop(control)['active'] is False, 'runtime_successor_emergency_stop')
    stop = [list(row) for row in control.execute('SELECT * FROM recognition_execution_stops ORDER BY sequence')]
    _need(stop, 'runtime_successor_emergency_stop')
    scope = dict(policy=contract.POLICY, source_generation=5, destination_generation=6,
        binding_sha256=digest(binding), profile_sha256=profile['profile_sha256'],
        enrollment_audit_sha256=control.execute('SELECT body_sha256 FROM recognition_admin_audit WHERE sequence=?',
                                               (profile['audit_sequence'],)).fetchone()[0],
        installation_id=binding['installation_id'], target_id=binding['target_id'], owner_id=binding['owner_id'],
        source=original, destination=actual, target_schema_sha256=observed['schema_sha256'],
        control_schema_sha256=claims.manifest(control), owner_key_sha256=hashlib.sha256(owner[0].encode()).hexdigest(),
        auth_epoch=metadata[0], mfa_epoch=mfa['epoch'], activation_sha256=digest(activation), stop_sha256=digest(stop),
        recovery_sha256=digest([]), root_sha256=hashlib.sha256(public).hexdigest(),
        audit_sha256=audit_sha256 or head['body_sha256'], boundary=contract.BOUNDARY)
    contract.validate_scope(scope)
    return scope, binding, profile


def describe(config):
    """Read-only actual-worker preparation scope. No authority, nonce or credentials."""
    _wsgi()
    with _reserved(config) as (control, target):
        scope, _, _ = _scope(config, control, target)
        return dict(scope=scope, scope_sha256=digest(scope), read_only=True, execution_authority=False)


def _events(control, action, identifier):
    result = []
    for row in control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence'):
        body = load(row['body_json'])
        if body['action'] == action:
            _need(type(body['subject']) is dict, 'runtime_successor_history')
            if body['subject'].get('authorization_id') == identifier:
                result.append(dict(row))
    return result


def prepare(config, envelope):
    _wsgi()
    body = _signed(config, envelope, contract.PREPARE)
    subject = body['subject']; identifier = subject['authorization_id']
    with _reserved(config, write=True) as (control, target):
        _owners[control][4] = a.timestamp(body['expires_at_utc'])
        scope, binding, _ = _scope(config, control, target)
        _need(scope == subject['scope'], 'runtime_successor_scope_changed')
        _need(not _events(control, PREPARED, identifier), 'runtime_successor_replay')
        for candidate in control.execute('SELECT body_json,sequence FROM recognition_admin_audit'):
            event = load(candidate['body_json'])
            if event['action'] == PREPARED:
                previous = control.execute(f'SELECT expires_at FROM {profiles.CHALLENGES} WHERE audit_sequence=?',
                                           (candidate['sequence'],)).fetchone()
                _need(previous is not None and a.timestamp(runtime._utc_now()) >= previous['expires_at'],
                      'runtime_successor_pending_preparation')
        now = runtime._utc_now(); issued = a.timestamp(now)
        nonce = secrets.token_urlsafe(32)
        challenge = dict(challenge_id=str(uuid4()), format='recognition-runtime-enrollment-challenge-v1',
            installation_id=binding['installation_id'], source_generation=5, source_binding_sha256=digest(binding),
            target_id=binding['target_id'], owner_id=binding['owner_id'], role='runtime',
            nonce_sha256=hashlib.sha256(nonce.encode('ascii')).hexdigest(), issued_at=issued, expires_at=issued+600,
            operator=subject['operator'], reason=subject['reason'], audit_sequence=a._audit_head(control)['sequence']+1)
        challenge['challenge_sha256'] = digest(challenge)
        _insert(control, profiles.CHALLENGES, challenge)
        a._audit(control, PREPARED, subject['operator'], now, dict(authorization_id=identifier,
            challenge_sha256=challenge['challenge_sha256'], authorization=envelope, scope=scope))
        _need(_scope(config, control, target, audit_sha256=scope['audit_sha256'])[0] == scope)
        _signed(config, envelope, contract.PREPARE)
        _commit(control)
    # Collector opens independent read-only snapshots after the challenge commit.
    record = evidence._collect(config.target, config.control, challenge_id=challenge['challenge_id'],
        challenge_sha256=challenge['challenge_sha256'], now=runtime._utc_now())
    from flask import current_app
    evidence._log_record(current_app, record)
    return dict(state='PREPARED', authorization_id=identifier, challenge=challenge,
                nonce=nonce, execution_authority=False)


def _insert(control, table, value):
    control.execute(f"INSERT INTO {table} ({','.join(value)}) VALUES ({','.join('?' for _ in value)})", tuple(value.values()))


def _preparation(config, control, identifier):
    events = _events(control, PREPARED, identifier)
    _need(len(events) == 1, 'runtime_successor_preparation_missing')
    event = load(events[0]['body_json']); value = event['subject']
    contract.fields(value, 'authorization_id challenge_sha256 authorization scope')
    body = _signed(config, value['authorization'], contract.PREPARE, at=event['at_utc'], control=control, event=event)
    _need(body['subject']['authorization_id'] == identifier and body['subject']['scope'] == value['scope']
          and event['actor'] == body['subject']['operator']
          and event['previous_sha256'] == value['scope']['audit_sha256'])
    challenge = control.execute(f'SELECT * FROM {profiles.CHALLENGES} WHERE audit_sequence=?', (events[0]['sequence'],)).fetchone()
    _need(challenge is not None and challenge['challenge_sha256'] == value['challenge_sha256']
          and challenge['source_generation'] == 5 and challenge['source_binding_sha256'] == contract.SOURCE_BINDING
          and challenge['operator'] == body['subject']['operator'] and challenge['reason'] == body['subject']['reason']
          and challenge['issued_at'] == a.timestamp(event['at_utc'])
          and all(challenge[key] == value['scope'][key] for key in ('installation_id','target_id','owner_id')))
    return events[0], value, dict(challenge), body


def _templates(binding, review, preparation):
    observation = next(row['observation'] for row in review['observations']
                       if row['observation_sha256'] == review['selected_observation_sha256'])
    subject = preparation['subject']
    profile = dict(format='recognition-runtime-profile-v1', installation_id=binding['installation_id'], generation=6,
        role='runtime', **{key: observation[key] for key in enrollment.PHYSICAL_FIELDS},
        target_id=binding['target_id'], owner_id=binding['owner_id'], challenge_id=observation['challenge_id'],
        observation_sha256=review['selected_observation_sha256'], evidence_channel=observation['evidence_channel'],
        observed_at=observation['observed_at'], operator=subject['operator'], reason=subject['reason'])
    destination = {key: value for key, value in binding.items() if key not in ('at_utc', 'runtime_profile_sha256')}
    destination.update(generation=6, previous_sha256=digest(binding))
    return profile, destination


def _plan(config, control, target, identifier, review, backups):
    row, prepared, challenge, approval = _preparation(config, control, identifier)
    _need(a._audit_head(control)['body_sha256'] == row['body_sha256'], 'runtime_successor_stale')
    scope, binding, _ = _scope(config, control, target, audit_sha256=prepared['scope']['audit_sha256'])
    _need(scope == prepared['scope'], 'runtime_successor_scope_changed')
    evidence._challenge(control, challenge['challenge_id'], challenge['challenge_sha256'], runtime._utc_now())
    review = enrollment.parse_review(canonical(review))
    enrollment.validate_review_scope(review, challenge, binding, runtime._utc_now())
    expected = scope['destination']
    for record in review['observations']:
        observed = record['observation']
        for prefix in ('target', 'control'):
            _need(observed['hostname'] == expected[prefix]['hostname'] and observed[prefix+'_path'] == expected[prefix]['database']
                  and observed[prefix+'_device'] == str(expected[prefix]['device'])
                  and observed[prefix+'_inode'] == str(expected[prefix]['inode']), 'runtime_successor_evidence')
    from . import deployment_qualification as qualification
    paths = {key: value['path'] if type(value) is dict else value for key, value in backups.items()}
    pair = qualification._backups(config, control, target, binding, paths)
    profile, destination = _templates(binding, review, approval)
    return dict(format=contract.POLICY, authorization_id=identifier, preparation_sha256=row['body_sha256'],
        challenge_sha256=challenge['challenge_sha256'], scope=scope, review=review, review_sha256=digest(review),
        selected_observation_sha256=review['selected_observation_sha256'], profile_template=profile,
        binding_template=destination, template_sha256=digest(dict(profile=profile, binding=destination)),
        invalidations=list(INVALIDATIONS), backups=pair, created_at_utc=load(row['body_json'])['at_utc'],
        deadline_at_utc=datetime.fromtimestamp(challenge['expires_at'], timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        execution_authority=False)


def plan(config, envelope, review, backups):
    _wsgi()
    body = _signed(config, envelope, contract.INSPECT)
    with _reserved(config) as (control, target):
        value = _plan(config, control, target, body['subject']['authorization_id'], review, backups)
        return dict(plan=value, plan_sha256=digest(value), read_only=True, execution_authority=False)


def _commit(control):
    _need(control in _owners, 'runtime_successor_owner')
    clock, target, pid, thread, deadline = _owners[control]
    _need(pid == os.getpid() and thread is threading.current_thread() and control.in_transaction
          and target.in_transaction and target.execute('PRAGMA query_only').fetchone()[0] == 1
          and target.total_changes == 0, 'runtime_successor_owner')
    _, now = clock.read()
    _need(deadline is not None and now < deadline, 'runtime_successor_expired')
    try:
        control.commit()
    except sqlite3.Error:
        raise a.AdminError('runtime_successor_outcome_unconfirmed', 503) from None
    _need(not control.in_transaction, 'runtime_successor_commit_unconfirmed')


def complete(config, envelope, nonce):
    _wsgi()
    approval = _signed(config, envelope, contract.COMPLETE)
    value = approval['subject']['plan']
    with _reserved(config, write=True) as (control, target):
        fresh = _plan(config, control, target, value['authorization_id'], value['review'], value['backups'])
        _need(canonical(fresh) == canonical(value), 'runtime_successor_plan_changed')
        _, _, challenge, _ = _preparation(config, control, value['authorization_id'])
        _owners[control][4] = min(a.timestamp(approval['expires_at_utc']), challenge['expires_at'])
        _need(type(nonce) is str and hmac.compare_digest(hashlib.sha256(nonce.encode('ascii')).hexdigest(),
                                                       challenge['nonce_sha256']), 'runtime_enrollment_nonce_mismatch')
        from . import approvals
        a._invalidate(control)
        now = runtime._utc_now()
        approvals._invalidate_all(control, value['profile_template']['operator'], now, 'runtime-device-successor')
        profile = dict(value['profile_template'], created_at=a.timestamp(now), audit_sequence=a._audit_head(control)['sequence']+1)
        profile['profile_sha256'] = digest(profile)
        binding = dict(value['binding_template'], runtime_profile_sha256=profile['profile_sha256'], at_utc=now)
        _insert(control, profiles.PROFILES, profile)
        _insert(control, 'recognition_admin_bindings', dict(generation=6, body_json=canonical(binding), body_sha256=digest(binding)))
        observed = dict(target=asdict(a.target_identity(target)), control=asdict(a.target_identity(control)))
        a._audit(control, COMMITTED, profile['operator'], now, dict(authorization_id=value['authorization_id'],
            profile_sha256=profile['profile_sha256'], binding_sha256=digest(binding), preparation_sha256=value['preparation_sha256'],
            challenge_sha256=value['challenge_sha256'], plan_sha256=digest(value), authorization=envelope,
            invalidations=list(INVALIDATIONS), physical=observed, state='CONSUMED', execution_authority=False))
        _need(observed == value['scope']['destination'], 'runtime_successor_physical_identity')
        _signed(config, envelope, contract.COMPLETE)
        evidence._physical(observed['target']); evidence._physical(observed['control'])
        _need(a.timestamp(runtime._utc_now()) < challenge['expires_at'], 'runtime_successor_expired')
        runtime._identity_snapshot(config, control, target, runtime._utc_now())
        from . import deployment_qualification as qualification
        qualification.permissions(config)
        for backup in value['backups'].values():
            _need(qualification._file(Path(backup['path']), config) == backup, 'deployment_backup_changed')
        _signed(config, envelope, contract.COMPLETE)
        _commit(control)
        return dict(state='COMMITTED', generation=6, binding_sha256=digest(binding),
                    profile_sha256=profile['profile_sha256'], execution_authority=False)


def verify(control, bindings, head):
    """Historical successor reader; no authorization or physical tolerance is issued."""
    _need(len(bindings) == 6 and bindings[-1]['generation'] == 6, 'runtime_successor_generation')
    stored = control.execute('SELECT * FROM recognition_admin_bindings ORDER BY generation').fetchall()
    _need(len(stored) == 6, 'runtime_successor_generation')
    previous = None
    for number, (row, body) in enumerate(zip(stored, bindings), 1):
        runtime._binding(body)
        _need(row['generation'] == body['generation'] == number and row['body_json'] == canonical(body)
              and row['body_sha256'] == digest(body) and body['previous_sha256'] == previous,
              'installation_history_integrity_failure')
        previous = row['body_sha256']
    _need(dict(a._audit_head(control)) == dict(head), 'runtime_successor_history')
    profiles.check_rows(control)
    source, old_profile, _ = runtime._enrollment_history(control, bindings[:-1], head)
    _need(digest(source) == contract.SOURCE_BINDING and old_profile['profile_sha256'] == contract.SOURCE_PROFILE)
    events = [dict(row) for row in control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence')
              if load(row['body_json'])['action'] == COMMITTED]
    _need(len(events) == 1, 'runtime_successor_history')
    event = load(events[0]['body_json']); subject = event['subject']
    contract.fields(subject, 'authorization_id profile_sha256 binding_sha256 preparation_sha256 challenge_sha256 '
                    'plan_sha256 authorization invalidations physical state execution_authority')
    config = SimpleNamespace(control=Path(control.execute('PRAGMA database_list').fetchone()[2]).resolve())
    approval = _signed(config, subject['authorization'], contract.COMPLETE, at=event['at_utc'], control=control, event=event)
    plan = approval['subject']['plan']; identifier = plan['authorization_id']
    prepared, preparation, challenge, preparation_body = _preparation(config, control, identifier)
    _need(plan['scope'] == preparation['scope'] and subject['authorization_id'] == identifier
          and plan['preparation_sha256'] == subject['preparation_sha256'] == prepared['body_sha256']
          and plan['challenge_sha256'] == subject['challenge_sha256'] == challenge['challenge_sha256']
          and subject['plan_sha256'] == digest(plan) and subject['state'] == 'CONSUMED'
          and subject['execution_authority'] is False
          and canonical(subject['physical']) == canonical(plan['scope']['destination'])
          and subject['invalidations'] == plan['invalidations'] == INVALIDATIONS)
    review = enrollment.parse_review(canonical(plan['review']))
    enrollment.validate_review_scope(review, challenge, source, event['at_utc'])
    selected = next(record['observation'] for record in review['observations']
                    if record['observation_sha256'] == review['selected_observation_sha256'])
    for prefix in ('target', 'control'):
        expected = contract.destination()[prefix]
        _need(selected['hostname'] == expected['hostname'] and selected[prefix+'_path'] == expected['database']
              and selected[prefix+'_device'] == str(expected['device'])
              and selected[prefix+'_inode'] == str(expected['inode']))
    _need(plan['scope']['enrollment_audit_sha256'] == control.execute(
        'SELECT body_sha256 FROM recognition_admin_audit WHERE sequence=?', (old_profile['audit_sequence'],)).fetchone()[0]
        and source['installation_id'] == plan['scope']['installation_id']
        and source['target_id'] == plan['scope']['target_id'] and source['owner_id'] == plan['scope']['owner_id']
        and plan['scope']['target_schema_sha256'] == old_profile['target_schema_sha256']
        and event['actor'] == preparation_body['subject']['operator']
        and plan['created_at_utc'] == load(prepared['body_json'])['at_utc']
        and a.timestamp(plan['deadline_at_utc']) == challenge['expires_at']
        and a.timestamp(event['at_utc']) < challenge['expires_at']
        and prepared['sequence'] < events[0]['sequence'])
    _need(plan['review_sha256'] == digest(review) and plan['selected_observation_sha256'] == review['selected_observation_sha256'])
    ptemplate, btemplate = _templates(source, review, preparation_body)
    _need(plan['profile_template'] == ptemplate and plan['binding_template'] == btemplate
          and plan['template_sha256'] == digest(dict(profile=ptemplate, binding=btemplate)))
    expected_profile = dict(ptemplate, created_at=a.timestamp(event['at_utc']), audit_sequence=events[0]['sequence'])
    expected_profile['profile_sha256'] = digest(expected_profile)
    expected_binding = dict(btemplate, at_utc=event['at_utc'], runtime_profile_sha256=expected_profile['profile_sha256'])
    actual = control.execute(f'SELECT * FROM {profiles.PROFILES} WHERE generation=6').fetchall()
    _need(len(actual) == 1 and dict(actual[0]) == expected_profile and bindings[-1] == expected_binding
          and subject['binding_sha256'] == digest(expected_binding) and subject['profile_sha256'] == expected_profile['profile_sha256'])
    return expected_binding, expected_profile, head


def eligible(control, binding):
    if binding['generation'] == 5:
        return True
    return (binding['generation'] == 6 and bool(control.execute(
        "SELECT 1 FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?", (COMMITTED,)).fetchone())
        and runtime._history(control)[0] == binding)


def inspect(config, envelope):
    _wsgi()
    body = _signed(config, envelope, contract.INSPECT)
    identifier = body['subject']['authorization_id']
    with a.connect(config.control) as control:
        control.execute('BEGIN')
        try:
            a._audit_head(control)
            # An absent/renamed consumption action is not proof of an unused
            # preparation. Validate the whole durable graph before classifying.
            binding, profile, _ = runtime._history(control)
            rows = _events(control, PREPARED, identifier)
            if not rows:
                return dict(state='INCONSISTENT' if _events(control, COMMITTED, identifier) else 'NOT_PREPARED',
                            execution_authority=False)
            _, _, challenge, _ = _preparation(config, control, identifier)
            commits = _events(control, COMMITTED, identifier)
            if commits:
                return dict(state='COMMITTED', generation=6, binding_sha256=digest(binding),
                            profile_sha256=profile['profile_sha256'], execution_authority=False)
            return dict(state='EXPIRED_UNCONSUMED' if a.timestamp(runtime._utc_now()) >= challenge['expires_at'] else 'PREPARED',
                        execution_authority=False)
        except (ValueError, sqlite3.Error, KeyError, TypeError):
            return dict(state='INCONSISTENT', execution_authority=False)
