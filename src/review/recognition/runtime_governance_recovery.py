"""Custodian-only recovery trust. Never a runtime credential or identity override.

The OS deployment custodian is trusted; same-UID/host compromise is outside this
boundary. Enrollment additionally requires the existing verified owner's email
challenge and replay-protected TOTP. No browser/API registers recovery authority.
SQLite and protected-file publication are deliberately NOT claimed to be atomic.
"""
import base64
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import sqlite3
from uuid import UUID, uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from . import administration as a, admin_auth as auth
from .rules import canonical, digest
from .trust import fields, load, require

KEY_FORMAT = 'recognition-governance-recovery-key-v1'
PLAN_FORMAT = 'recognition-governance-root-cutover-v1'
DOMAIN = b'DMV-governance-root-recovery-v1\x00'
REQUEST = 'governance_recovery_enrollment_requested'
ENROLLED = 'governance_recovery_key_enrolled'
CUTOVER = 'governance_root_recovery_committed'
LIFETIME = 600


def _now():
    from .runtime_validation import _utc_now
    return _utc_now()


def _sha(value):
    from .runtime_profile_schema import _check_sha
    _check_sha(value)


def _public(value):
    require(type(value) is str, 'recovery_public_key')
    raw = base64.b64decode(value, validate=True)
    require(len(raw) == 32 and base64.b64encode(raw).decode() == value, 'recovery_public_key')
    Ed25519PublicKey.from_public_bytes(raw)
    return raw


def validate_key(value):
    fields(value, ('format', 'installation_id', 'owner_id', 'public_key'))
    require(value['format'] == KEY_FORMAT and type(value['owner_id']) is int and value['owner_id'] > 0
            and str(UUID(value['installation_id'])) == value['installation_id'], 'recovery_key_scope')
    _public(value['public_key'])
    return value


def _root_value(value):
    from . import runtime_production_governance as gov
    fields(value, ('format', 'mandate', 'installation_id', 'owner_id', 'public_key'))
    require(value['format'] == gov.FORMAT and value['mandate'] == gov.contract.MANDATE
            and type(value['owner_id']) is int and value['owner_id'] > 0
            and str(UUID(value['installation_id'])) == value['installation_id'], 'recovery_root_scope')
    _public(value['public_key'])
    return value


def fingerprint(root):
    return hashlib.sha256(_public(root['public_key'])).hexdigest()


def certificate_directory(config):
    return config.control.with_name(config.control.name + '.governance-recovery')


def _protected(path, *, directory=False):
    # Reuse the operator's canonical path, single-link and platform ACL checks.
    from scripts.operator.recognition_governance import _protected as check
    check(path)
    require(path.is_dir() if directory else path.is_file(), 'recovery_protected_file')
    if os.name != 'nt':
        require(path.stat().st_uid == os.geteuid(), 'recovery_custodian_owner')


def _original(config):
    from . import runtime_production_governance as gov
    path = gov.trust_path(config)
    _protected(path)
    _protected(path.parent, directory=True)
    return _root_value(gov._installed_root(config))


def _records(control):
    a._audit_head(control)
    rows = []
    for row in control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence'):
        body = load(row['body_json'])
        require(canonical(body) == row['body_json'], 'recovery_audit_encoding')
        rows.append((dict(row), body))
    return rows


def _member(control, event):
    a._audit_head(control)
    matches = control.execute('SELECT * FROM recognition_admin_audit WHERE body_sha256=?', (digest(event),)).fetchall()
    require(len(matches) == 1, 'recovery_historical_membership')
    require(matches[0]['body_json'] == canonical(event), 'recovery_historical_membership')
    return dict(matches[0])


def _check_boundary(rows, boundary):
    fields(boundary, ('sequence', 'sha256'))
    require(type(boundary['sequence']) is int and 1 <= boundary['sequence'] <= len(rows),
            'recovery_audit_boundary')
    require(rows[boundary['sequence']-1][0]['body_sha256'] == boundary['sha256'], 'recovery_audit_boundary')


def _boundary(control):
    head = a._audit_head(control)
    require(head is not None, 'recovery_audit_boundary')
    return dict(sequence=head['sequence'], sha256=head['body_sha256'])


def _certificate_name(index):
    return 'enrollment.json' if index == 0 else 'cutover-%08d.json' % index


def _certificate(config, name, expected, *, pending=False):
    directory = certificate_directory(config)
    if not directory.exists() and not directory.is_symlink():
        require(pending, 'recovery_publication_pending')
        return False
    _protected(directory, directory=True)
    path = directory / name
    if not path.exists() and not path.is_symlink():
        require(pending, 'recovery_publication_pending')
        return False
    _protected(path)
    require(path.stat().st_size <= 262144 and path.read_text(encoding='utf-8') == canonical(expected),
            'recovery_certificate_conflict')
    return True


def _chain(config, control, *, pending=False):
    """Only audit order selects keys. Never use an approval's claimed timestamp."""
    from . import runtime_production_governance as gov
    root = _root_value(gov._installed_root(config))
    exists = control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_admin_audit'").fetchone()
    if not exists:
        require(not certificate_directory(config).exists() and not certificate_directory(config).is_symlink(),
                'recovery_history_missing')
        return root, None, [], []
    # Installations which have never enrolled recovery retain their original
    # root-loading behavior. In particular, an empty bootstrap DB needs no new
    # schema and ordinary legacy authorization does not run a custodian ACL tool.
    enrolled = control.execute("SELECT 1 FROM recognition_admin_audit WHERE json_extract(body_json,'$.action') IN (?,?) LIMIT 1",
                               (ENROLLED, CUTOVER)).fetchone()
    if not enrolled:
        require(not certificate_directory(config).exists() and not certificate_directory(config).is_symlink(),
                'recovery_uncommitted_certificate')
        return root, None, [], []
    root = _original(config)
    rows = _records(control)
    events = [(row, body) for row, body in rows if body['action'] in (ENROLLED, CUTOVER)]
    key, edges, publications, ids = None, [], [], set()
    used_keys = {root['public_key']}
    for index, (row, event) in enumerate(events):
        subject = event['subject']
        fields(subject, ('certificate', 'certificate_sha256'))
        cert = subject['certificate']
        require(digest(cert) == subject['certificate_sha256'], 'recovery_certificate_digest')
        fields(cert, ('format', 'id', 'request', 'approval') if index == 0 else
               ('format', 'id', 'plan', 'authorization'))
        require(cert['id'] not in ids and str(UUID(cert['id'])) == cert['id'], 'recovery_replay')
        ids.add(cert['id'])
        if index == 0:
            require(event['action'] == ENROLLED and cert['format'] == KEY_FORMAT, 'recovery_enrollment_required')
            request = cert['request']; _validate_request(request)
            require(request['id'] == cert['id'] and request['root'] == root, 'recovery_enrollment_scope')
            _check_boundary(rows, request['scope']['audit'])
            earlier = [(r,b) for r,b in rows[:row['sequence']-1]
                       if b['action'] == REQUEST and b['subject']['request'] == request]
            require(len(earlier) == 1 and event['previous_sha256'] == earlier[0][0]['body_sha256'],
                    'recovery_enrollment_predecessor')
            require(earlier[0][1]['previous_sha256'] == request['scope']['audit']['sha256']
                    and earlier[0][0]['sequence'] == request['scope']['audit']['sequence']+1
                    and earlier[0][1]['actor'] == root['owner_id'], 'recovery_enrollment_predecessor')
            fields(cert['approval'], ('kind', 'request_sha256', 'mfa_epoch'))
            require(cert['approval'] == dict(kind='custodian_owner_email_totp', request_sha256=digest(request),
                    mfa_epoch=request['scope']['mfa_epoch']) and event['actor'] == root['owner_id']
                    and a.timestamp(request['created_at_utc']) <= a.timestamp(event['at_utc'])
                    < a.timestamp(request['expires_at_utc']), 'recovery_enrollment_approval')
            key = validate_key(request['key'])
            require(key['public_key'] not in used_keys, 'recovery_independent_key_required')
            used_keys.add(key['public_key'])
        else:
            require(event['action'] == CUTOVER and cert['format'] == PLAN_FORMAT, 'recovery_cutover_order')
            plan = cert['plan']; validate_plan(plan)
            require(cert['id'] == plan['id'] and plan['old_root'] == root
                    and plan['recovery_key_sha256'] == digest(key), 'recovery_cutover_scope')
            require(plan['new_root']['public_key'] not in used_keys, 'recovery_root_reuse')
            used_keys.add(plan['new_root']['public_key'])
            _check_boundary(rows, plan['scope']['audit'])
            require(event['previous_sha256'] == plan['scope']['audit']['sha256']
                    and row['sequence'] == plan['scope']['audit']['sequence']+1
                    and event['actor'] == root['owner_id'], 'recovery_cutover_predecessor')
            _verify_signature(key, plan, cert['authorization'])
            require(a.timestamp(plan['created_at_utc']) <= a.timestamp(event['at_utc'])
                    < a.timestamp(plan['expires_at_utc']), 'recovery_cutover_expired')
            root = plan['new_root']
            edges.append((row['sequence'], root))
        present = _certificate(config, _certificate_name(index), cert, pending=pending)
        publications.append((row, cert, present))
    directory = certificate_directory(config)
    if directory.exists() or directory.is_symlink():
        _protected(directory, directory=True)
        expected = {_certificate_name(i) for i in range(len(events))}
        # Incomplete exclusive-publish temporary files are inert, never roots.
        require(all(path.name in expected or path.name.startswith('.') for path in directory.iterdir()),
                'recovery_uncommitted_certificate')
        require(events, 'recovery_history_missing')
    return root, key, edges, publications


def current_root(config, *, control=None):
    if control is None:
        with a.connect(config.control) as db:
            db.execute('BEGIN')
            return _chain(config, db)[0]
    return _chain(config, control)[0]


def historical_root(config, control, event):
    row = _member(control, event)
    current, key, edges, _ = _chain(config, control)
    if not edges:
        # _chain already checked the protected original in recovery mode. Before
        # recovery exists, retain the old foundation's metadata checks, without
        # spawning an offline custodian ACL tool in every runtime validation.
        from . import runtime_production_governance as gov
        path = gov.trust_path(config)
        require(path.is_file() and path.stat().st_nlink == 1, 'foundation_approval_root')
        if os.name != 'nt':
            require(path.stat().st_mode & 0o022 == 0 and path.parent.stat().st_mode & 0o022 == 0,
                    'foundation_unprotected_root')
        return current
    root = _original(config)
    for sequence, successor in edges:
        if sequence < row['sequence']:
            root = successor
    return root


def _local():
    from flask import has_request_context
    require(not has_request_context(), 'recovery_local_custodian_required')


@contextmanager
def _reserved(config):
    _local()
    require(type(config) is a.LocalAdministration, 'recovery_configuration')
    config.paths()
    from . import deployment_qualification as qualification
    qualification.permissions(config)
    _original(config)
    with a.connect(config.control, write=True) as control, a.connect(config.target, write=True) as target:
        control.execute('BEGIN IMMEDIATE')
        target.execute('BEGIN IMMEDIATE')
        target.execute('PRAGMA query_only=ON')
        for db, path in ((control, config.control), (target, config.target)):
            require(db.execute('PRAGMA journal_mode').fetchone()[0].lower() == 'delete'
                    and db.execute('PRAGMA synchronous').fetchone()[0] == 2, 'recovery_storage_settings')
            with a.connect(path) as reader:
                qualification._integrity(reader)
        # The existing TOTP denial commits ONLY throttles + denial audit. Recovery
        # writes are never staged before verification. No credential/session DML.
        from .runtime_validation import _AUTHENTICATION_DDL_DENY
        def guard(action, table, column, database, source):
            if action == sqlite3.SQLITE_INSERT:
                return sqlite3.SQLITE_OK if table in ('recognition_admin_audit', 'recognition_admin_attempts') else sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_UPDATE:
                return sqlite3.SQLITE_OK if (table == 'recognition_admin_attempts'
                    or (table == 'recognition_admin_mfa' and column == 'last_counter')) else sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_DELETE or action in _AUTHENTICATION_DDL_DENY:
                return sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_PRAGMA and column is not None:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        control.set_authorizer(guard)
        try:
            yield control, target
        finally:
            control.set_authorizer(None)


def _scope(config, control, target):
    from . import runtime_validation as runtime, runtime_target_schema_lineage as lineage
    from . import local_readiness, runtime_execution_claim_schema as claims
    binding, profile, _ = runtime._history(control)  # Provenance, never identity admission.
    root = current_root(config, control=control)
    require(root['installation_id'] == binding['installation_id'] and root['owner_id'] == binding['owner_id'],
            'recovery_installation')
    require(local_readiness._state(control, binding)['state'] == 'NOT_ACTIVATED', 'recovery_inactive_required')
    from .runtime_enrollment_transition_schema import require_no_pending
    require_no_pending(control)
    from .runtime_proposal_records import ACK_ACTION
    records = _records(control)
    require(not any(body['action'] == ACK_ACTION for _,body in records), 'recovery_work_present')
    # Closed pre-work recovery. Never adopt an unfinished successor/issuer/claim.
    for db in (control, target):
        for name in ('recognition_runtime_execution_claims', 'recognition_runtime_execution_claim_history',
                     'recognition_runtime_execution_authorities', 'recognition_runtime_execution_attempts',
                     'recognition_execution_claims', 'recognition_execution_blocks', 'recognition_execution_seals',
                     'recognition_operation_receipts', 'recognition_operation_contracts',
                     'recognition_execution_audit', 'recognition_operation_executions', 'recognition_operation_decisions'):
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone():
                require(not db.execute('SELECT 1 FROM '+name+' LIMIT 1').fetchone(), 'recovery_work_present')
    prepared = [b for _,b in records if b['action'] == 'runtime_profile_successor_challenge_issued']
    completed = [b for _,b in records if b['action'] == 'runtime_profile_device_successor_committed']
    require(len(prepared) == len(completed), 'recovery_pending_successor')
    require(not any(b['action'] in ('runtime_finalization_issuer_authorized', 'runtime_finalization_issuer_started')
                    for _,b in records), 'recovery_issuer_present')
    a.schema.check_target(target)
    observation = a.observe_target(target)
    lineage.validate_target(control, target, binding, profile, observation['schema_sha256'])
    metadata = target.execute('SELECT * FROM '+a.schema.TARGET_TABLE).fetchall()
    require(len(metadata) == 1 and all(metadata[0][k] == binding[k]
            for k in ('installation_id','target_id','owner_id')), 'recovery_target_scope')
    physical = dict(target=asdict(a.target_identity(target)), control=asdict(a.target_identity(control)))
    for side, path in (('target', config.target), ('control', config.control)):
        require(physical[side] == asdict(a.target_identity(path))
                and physical[side]['database'] == profile[side+'_path']
                and str(physical[side]['inode']) == profile[side+'_inode'], 'recovery_file_identity')
    owner = target.execute('SELECT reviewer_key,email FROM community_reviewers WHERE id=?', (binding['owner_id'],)).fetchone()
    from src.review.admin_dashboard import owner_access
    require(owner is not None and owner_access(target, binding['owner_id'], owner[0])[0], 'recovery_owner')
    from src.review.auth import normalize_email
    email = normalize_email(owner['email'])
    mfa = control.execute('SELECT * FROM recognition_admin_mfa WHERE actor=?', (binding['owner_id'],)).fetchone()
    require(mfa is not None and mfa['state'] == 'ENROLLED', 'recovery_mfa_required')
    auth._cipher(config)
    require(a.timestamp(_now()) >= a.timestamp(records[-1][1]['at_utc']), 'recovery_clock')
    return dict(installation_id=binding['installation_id'], owner_id=binding['owner_id'], target_id=binding['target_id'],
        generation=binding['generation'], binding_sha256=digest(binding), profile_sha256=profile['profile_sha256'],
        target_schema_sha256=observation['schema_sha256'], control_schema_sha256=claims.manifest(control),
        physical=physical, email_sha256=digest(email), owner_key_sha256=digest(owner['reviewer_key']),
        auth_epoch=metadata[0]['auth_epoch'], mfa_epoch=mfa['epoch'], audit=_boundary(control)), binding, mfa, email


def _validate_scope(scope):
    fields(scope, ('installation_id','owner_id','target_id','generation','binding_sha256','profile_sha256',
        'target_schema_sha256','control_schema_sha256','physical','email_sha256','owner_key_sha256',
        'auth_epoch','mfa_epoch','audit'))
    for name in ('installation_id','target_id'):
        require(str(UUID(scope[name])) == scope[name], 'recovery_scope')
    for name in ('owner_id','generation','auth_epoch','mfa_epoch'):
        require(type(scope[name]) is int and scope[name] > 0, 'recovery_scope')
    for name in scope:
        if name.endswith('_sha256'):
            _sha(scope[name])
    from .runtime_validation import _physical
    fields(scope['physical'], ('target','control'))
    for value in scope['physical'].values():
        _physical(value)
    fields(scope['audit'], ('sequence','sha256')); _sha(scope['audit']['sha256'])


def _lifetime(value):
    start, end = a.timestamp(value['created_at_utc']), a.timestamp(value['expires_at_utc'])
    require(start < end <= start+LIFETIME, 'recovery_lifetime')


def _validate_request(value):
    fields(value, ('format','id','root','key','scope','reason','created_at_utc','expires_at_utc'))
    require(value['format'] == KEY_FORMAT and str(UUID(value['id'])) == value['id'], 'recovery_request')
    _root_value(value['root']); validate_key(value['key']); _validate_scope(value['scope']); _lifetime(value)
    require(type(value['reason']) is str and 1 <= len(value['reason'].strip()) <= 2000, 'recovery_reason')
    require(all(value['root'][k] == value['key'][k] == value['scope'][k] for k in ('installation_id','owner_id')),
            'recovery_request_scope')
    require(value['root']['public_key'] != value['key']['public_key'], 'recovery_independent_key_required')


def _expires(now):
    from datetime import timedelta
    from .trust import utc
    return (utc(now)+timedelta(seconds=LIFETIME)).strftime('%Y-%m-%dT%H:%M:%SZ')


def request_enrollment(config, key, *, reason):
    """Local host owner + actual configured email delivery. Never returns token."""
    from src.review.email_delivery import governance_recovery_sender_from_env
    sender = governance_recovery_sender_from_env()  # No dev outbox/injected HTTP sender.
    token = secrets.token_urlsafe(32)
    with _reserved(config) as (control, target):
        root, previous_key, _, _ = _chain(config, control)
        require(previous_key is None, 'recovery_already_enrolled')
        scope, _, _, email = _scope(config, control, target)
        requests = [b for _,b in _records(control) if b['action'] == REQUEST]
        require(not requests or a.timestamp(_now()) >= a.timestamp(requests[-1]['subject']['request']['expires_at_utc']),
                'recovery_request_pending')
        now = _now()
        request = dict(format=KEY_FORMAT, id=str(uuid4()), root=root, key=key, scope=scope, reason=reason,
                       created_at_utc=now, expires_at_utc=_expires(now))
        _validate_request(request)
        a._audit(control, REQUEST, scope['owner_id'], now,
                 dict(request=request, email_token_sha256=hashlib.sha256(token.encode()).hexdigest()))
        fresh, _, _, _ = _scope(config, control, target); fresh['audit'] = scope['audit']
        require(fresh == scope, 'recovery_scope_changed')
        control.commit()
    # An uncertain/failed send leaves a bounded pending request, not authority.
    sender(email, canonical(dict(request=request, request_sha256=digest(request), email_challenge=token)), LIFETIME//60)
    return dict(state='EMAIL_CHALLENGE_SENT', request_id=request['id'], request_sha256=digest(request),
                request=request, execution_authority=False)


def _append(control, action, certificate):
    a._audit(control, action, certificate.get('request', certificate.get('plan'))['scope']['owner_id'], _now(),
             dict(certificate=certificate, certificate_sha256=digest(certificate)))


def _commit(control):
    """No retry on lost acknowledgement. Publication requires confirmed return."""
    control.commit()


def _approval_clock():
    from .runtime_execution_claims import _Clock
    clock = _Clock()
    clock.issued = clock.previous  # Entry sample includes time spent acquiring reservations.
    return clock


def _live_approval(clock, approval, code='recovery_expired'):
    stamp, now = clock.read()  # Existing rollback/stall/monotonic anomaly guard.
    created, expires = a.timestamp(approval['created_at_utc']), a.timestamp(approval['expires_at_utc'])
    require(created <= now < expires, code)
    # Clip to the ORIGINAL expiry, not another 600 seconds at verification.
    # Use the earliest entry sample and latest current sample conservatively.
    start_ns, start_utc, _ = clock.issued
    require(clock.previous[2]-start_ns < (expires-start_utc)*1_000_000_000, code)
    return stamp


def _publish(config, name, certificate):
    from scripts.operator.recognition_governance import _publish as publish
    directory = certificate_directory(config)
    if not directory.exists():
        directory.mkdir(mode=0o700)  # Only after a confirmed database commit.
    _protected(directory, directory=True)
    publish(directory/name, canonical(certificate).encode('utf-8'))
    if os.name != 'nt':
        # Persist creation of the certificate directory itself, including after
        # an interrupted first publication left an empty directory behind.
        parent = os.open(directory.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)


def enroll(config, request_id, *, email_challenge, code, approved_request_sha256):
    clock = _approval_clock()
    with _reserved(config) as (control, target):
        require(_chain(config, control)[1] is None, 'recovery_already_enrolled')
        rows = [(r,b) for r,b in _records(control) if b['action'] == REQUEST
                and b['subject']['request']['id'] == request_id]
        require(len(rows) == 1, 'recovery_request_missing')
        row, event = rows[0]; request = event['subject']['request']; _validate_request(request)
        require(digest(request) == approved_request_sha256 and _boundary(control)['sha256'] == row['body_sha256'],
                'recovery_request_stale')
        _live_approval(clock, request, 'recovery_request_expired')
        require(type(email_challenge) is str and 20 <= len(email_challenge) <= 256
                and hmac.compare_digest(hashlib.sha256(email_challenge.encode()).hexdigest(),
                                        event['subject']['email_token_sha256']), 'recovery_email_required')
        scope, binding, mfa, _ = _scope(config, control, target); scope['audit'] = request['scope']['audit']
        require(scope == request['scope'] and current_root(config, control=control) == request['root'], 'recovery_scope_changed')
        # No staged recovery writes before this call: its documented denial
        # commit can persist only replay/throttle/denial changes allowed above.
        auth._code(control, config, binding, mfa, code, _live_approval(clock, request, 'recovery_request_expired'))
        fresh, _, _, _ = _scope(config, control, target); fresh['audit'] = request['scope']['audit']
        require(fresh == request['scope'], 'recovery_scope_changed')
        certificate = dict(format=KEY_FORMAT, id=request_id, request=request,
            approval=dict(kind='custodian_owner_email_totp', request_sha256=digest(request), mfa_epoch=mfa['epoch']))
        _append(control, ENROLLED, certificate)
        _final_files(config, control, target, request['scope'], request['root'])
        _live_approval(clock, request, 'recovery_request_expired')
        _commit(control)  # Unknown acknowledgement: publish nothing; inspect first.
    _publish(config, _certificate_name(0), certificate)
    return inspect(config)


def _final_files(config, control, target, expected, root):
    # Full live scope is revalidated immediately BEFORE the event is staged.
    # Reservations + SQL authorizer exclude subsequent DB changes; public root
    # and actual file identities are checked again immediately before commit.
    from . import deployment_qualification as qualification
    qualification.permissions(config)
    for side, path in (('target',config.target),('control',config.control)):
        require(asdict(a.target_identity(path)) == expected['physical'][side], 'recovery_file_identity')
    require(_original(config) == root, 'recovery_source_root_changed')
    _, _, _, publications = _chain(config, control, pending=True)
    require(publications and all(present for _,_,present in publications[:-1]),
            'recovery_predecessor_publication_changed')
    require(target.total_changes == 0 and target.execute('PRAGMA query_only').fetchone()[0] == 1,
            'recovery_target_write')


def validate_plan(plan):
    fields(plan, ('format','id','old_root','new_root','recovery_key_sha256','scope','reason','created_at_utc','expires_at_utc'))
    require(plan['format'] == PLAN_FORMAT and str(UUID(plan['id'])) == plan['id'], 'recovery_plan')
    _root_value(plan['old_root']); _root_value(plan['new_root']); _validate_scope(plan['scope']); _lifetime(plan)
    _sha(plan['recovery_key_sha256'])
    require(plan['old_root']['public_key'] != plan['new_root']['public_key']
            and all(plan['old_root'][k] == plan['new_root'][k] for k in ('format','mandate','installation_id','owner_id'))
            and all(plan['old_root'][k] == plan['scope'][k] for k in ('installation_id','owner_id')),
            'recovery_root_scope')
    require(type(plan['reason']) is str and 1 <= len(plan['reason'].strip()) <= 2000, 'recovery_reason')
    return plan


def signing_bytes(plan):
    validate_plan(plan)
    return DOMAIN+canonical(plan).encode('utf-8')


def _verify_signature(key, plan, envelope):
    fields(envelope, ('serialized_approval','signature'))
    require(envelope['serialized_approval'] == canonical(plan), 'recovery_exact_plan_required')
    signature = base64.b64decode(envelope['signature'], validate=True)
    require(len(signature) == 64 and base64.b64encode(signature).decode() == envelope['signature'], 'recovery_signature')
    try:
        Ed25519PublicKey.from_public_bytes(_public(key['public_key'])).verify(signature, signing_bytes(plan))
    except Exception:
        raise a.AdminError('recovery_signature', 403) from None


def plan(config, new_root, *, reason):
    with _reserved(config) as (control, target):
        root, key, _, publications = _chain(config, control)
        require(key is not None, 'recovery_enrollment_required')
        scope, _, _, _ = _scope(config, control, target)
        now = _now()
        result = dict(format=PLAN_FORMAT, id=str(uuid4()), old_root=root, new_root=new_root,
            recovery_key_sha256=digest(key), scope=scope, reason=reason,
            created_at_utc=now, expires_at_utc=_expires(now))
        validate_plan(result)
        # Retired roots and the recovery key cannot become current governance.
        used = [_original(config)['public_key'], key['public_key']] + [cert['plan']['new_root']['public_key']
            for _,cert,_ in publications if cert['format'] == PLAN_FORMAT]
        require(new_root['public_key'] not in used, 'recovery_root_reuse')
        return dict(plan=result, plan_sha256=digest(result), execution_authority=False)


def cutover(config, envelope, *, approved_plan_sha256):
    clock = _approval_clock()
    fields(envelope, ('serialized_approval','signature'))
    proposed = load(envelope['serialized_approval']); validate_plan(proposed)
    require(digest(proposed) == approved_plan_sha256, 'recovery_exact_plan_required')
    with _reserved(config) as (control, target):
        installed = _original(config)
        root, key, _, publications = _chain(config, control)
        require(key is not None and root == proposed['old_root'], 'recovery_source_root_changed')
        _verify_signature(key, proposed, envelope)
        scope, _, _, _ = _scope(config, control, target)
        require(scope == proposed['scope'], 'recovery_scope_changed')
        _live_approval(clock, proposed)
        require(not any(cert['id'] == proposed['id'] for _,cert,_ in publications), 'recovery_replay')
        used = [_original(config)['public_key'], key['public_key']] + [cert['plan']['new_root']['public_key']
            for _,cert,_ in publications if cert['format'] == PLAN_FORMAT]
        require(proposed['new_root']['public_key'] not in used, 'recovery_root_reuse')
        fresh, _, _, _ = _scope(config, control, target)
        require(fresh == scope, 'recovery_scope_changed')
        certificate = dict(format=PLAN_FORMAT, id=proposed['id'], plan=proposed, authorization=envelope)
        _append(control, CUTOVER, certificate)
        _final_files(config, control, target, scope, installed)
        _live_approval(clock, proposed)
        _commit(control)
    _publish(config, _certificate_name(len(publications)), certificate)
    return inspect(config)


def inspect(config):
    _local()
    with a.connect(config.control) as control:
        control.execute('BEGIN')
        root, key, _, publications = _chain(config, control, pending=True)
        missing = [cert['id'] for _,cert,present in publications if not present]
        return dict(state='PUBLICATION_PENDING' if missing else 'READY' if key else 'NOT_ENROLLED',
            root_sha256=digest(root), public_key_sha256=fingerprint(root),
            current_public_key_sha256=None if missing else fingerprint(root),
            recovery_key_sha256=digest(key) if key else None, pending_ids=missing, execution_authority=False)


def publish_committed(config, identifier):
    """Explicit finish-publication only. No new approval, audit write or retry."""
    _local(); _original(config)
    # Hold the CONTROL reservation across exact file publication so another
    # custodian cannot publish conflicting ordering. Never migrate/repair SQL.
    with _reserved(config) as (control, target):
        _, _, _, publications = _chain(config, control, pending=True)
        missing = [(i,row,cert) for i,(row,cert,present) in enumerate(publications) if not present]
        require(len(missing) == 1 and missing[0][2]['id'] == identifier, 'recovery_publication_scope')
        index, row, cert = missing[0]
        require(_boundary(control) == dict(sequence=row['sequence'], sha256=row['body_sha256']),
                'recovery_publication_stale')
        scope = cert.get('request', cert.get('plan'))['scope']
        from .runtime_execution_claim_schema import manifest
        require(a.observe_target(target)['schema_sha256'] == scope['target_schema_sha256']
                and manifest(control) == scope['control_schema_sha256'], 'recovery_publication_stale')
        _final_files(config, control, target, scope, _original(config))
        _publish(config, _certificate_name(index), cert)
    return inspect(config)
