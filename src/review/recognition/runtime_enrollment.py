"""Local operator approval of reviewed runtime evidence, never runtime authority.

Host access and independently verified private-log retrieval establish trust.
Neither these unsigned records, confirmation flags nor nonce possession do so.
"""

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import hmac
from pathlib import Path

from . import administration as a, administration_schema as schema
from . import runtime_evidence as evidence, runtime_profile_schema as r
from .runtime_challenges import _deployment_binding
from .rules import canonical, digest
from .trust import fields, identity, load


REVIEW_FORMAT = 'recognition-runtime-enrollment-review-v1'
MAX_REVIEW_BYTES = 262144
MAX_OBSERVATIONS = 32
OBSERVATION_FIELDS = frozenset('''format role installation_id target_id owner_id source_generation
source_binding_sha256 challenge_id challenge_sha256 nonce_sha256 challenge_expires_at observed_at
hostname target_path target_device target_inode control_path control_device control_inode
target_schema_sha256 pid python_version python_executable evidence_channel provenance'''.split())
PHYSICAL_FIELDS = ('hostname','target_path','target_device','target_inode','control_path',
                   'control_device','control_inode','target_schema_sha256')


def _text(value, maximum):
    a.need(type(value) is str and value.strip() and '\x00' not in value and len(value) <= maximum,
           'runtime_enrollment_text_invalid')


def _integer(value, low=0, high=r.MAX_TIME):
    a.need(type(value) is int and low <= value <= high, 'runtime_enrollment_integer_invalid')


def _path(value):
    _text(value, 4096)
    # Match Slice 1's lexical path contract before filesystem resolution;
    # notably UNC paths are not supported by the existing profile schema.
    normalized = value.replace('\\','/')
    absolute = value.startswith('/') or (len(value) >= 3 and value[0] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
                                        and value[1:3] == ':\\')
    a.need(absolute and '//' not in normalized and '/./' not in normalized and '/../' not in normalized
           and not normalized.endswith(('/','/.','/..')), 'runtime_enrollment_path_invalid')
    path = Path(value)
    a.need(path.is_absolute() and str(path.resolve()) == value, 'runtime_enrollment_path_invalid')
    from .runtime_history_validation import record_path
    record_path(value,'enrollment')


def validate_observation(record):
    fields(record, ('observation','observation_sha256'))
    value = record['observation']
    fields(value, OBSERVATION_FIELDS)
    a.need(len(canonical(record).encode('utf-8')) <= 16384, 'runtime_observation_too_large')
    r._check_sha(record['observation_sha256'])
    a.need(digest(value) == record['observation_sha256'], 'runtime_observation_digest_mismatch')
    a.need(value['format'] == evidence.FORMAT and value['role'] == 'runtime'
           and value['evidence_channel'] == evidence.CHANNEL and value['provenance'] == 'REQUIRES_OPERATOR_REVIEW',
           'runtime_observation_format_invalid')
    for key in ('installation_id','target_id','challenge_id'):
        identity(value[key])
    for key in ('source_binding_sha256','challenge_sha256','nonce_sha256','target_schema_sha256'):
        r._check_sha(value[key])
    for key in ('owner_id','source_generation','pid'):
        _integer(value[key], 1, 9223372036854775807)
    for key in ('observed_at','challenge_expires_at'):
        _integer(value[key])
    a.need(value['observed_at'] < value['challenge_expires_at'], 'runtime_observation_time_invalid')
    _text(value['hostname'], 255)
    _text(value['python_version'], 4096)
    # Process metadata is preserved exactly, not resolved in the console's
    # filesystem namespace (the worker executable may be a symlink there).
    _text(value['python_executable'], 4096)
    for prefix in ('target','control'):
        _path(value[prefix+'_path'])
        r._check_decimal(value[prefix+'_device'])
        r._check_decimal(value[prefix+'_inode'], inode=True)
    return value


def parse_review(serialized):
    a.need(type(serialized) is str and len(serialized.encode('utf-8')) <= MAX_REVIEW_BYTES,
           'runtime_review_too_large')
    review = load(serialized)
    fields(review, ('format','observations','selected_observation_sha256'))
    a.need(review['format'] == REVIEW_FORMAT and type(review['observations']) is list
           and 1 <= len(review['observations']) <= MAX_OBSERVATIONS, 'runtime_review_format_invalid')
    a.need(len(canonical(review).encode('utf-8')) <= MAX_REVIEW_BYTES, 'runtime_review_too_large')
    r._check_sha(review['selected_observation_sha256'])
    values = [validate_observation(record) for record in review['observations']]
    hashes = [record['observation_sha256'] for record in review['observations']]
    a.need(len(set(hashes)) == len(hashes) and review['selected_observation_sha256'] in hashes,
           'runtime_review_selection_invalid')
    scope = ('installation_id','target_id','owner_id','source_generation','source_binding_sha256',
             'challenge_id','challenge_sha256','nonce_sha256','challenge_expires_at') + PHYSICAL_FIELDS
    a.need(all(all(value[k] == values[0][k] for k in scope) for value in values), 'runtime_worker_disagreement')
    return review


def validate_review_scope(review, challenge, binding, now):
    moment = a.timestamp(now)
    for record in review['observations']:
        value = record['observation']
        expected = dict(installation_id=binding['installation_id'], target_id=binding['target_id'],
            owner_id=binding['owner_id'], source_generation=binding['generation'], source_binding_sha256=digest(binding),
            challenge_id=challenge['challenge_id'], challenge_sha256=challenge['challenge_sha256'],
            nonce_sha256=challenge['nonce_sha256'], challenge_expires_at=challenge['expires_at'],
            target_path=binding['target']['observation']['database'],
            target_inode=str(binding['target']['observation']['inode']), control_path=binding['control_identity']['database'],
            control_inode=str(binding['control_identity']['inode']), target_schema_sha256=binding['target']['schema_sha256'])
        a.need(all(value[k] == v for k,v in expected.items()), 'runtime_review_scope_mismatch')
        a.need(challenge['issued_at'] <= value['observed_at'] <= moment < challenge['expires_at'],
               'runtime_review_expired_or_future')


def _utc_now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _approved_review(serialized_review, nonce, *, approved_review_sha256,
                     approved_observation_sha256, operator, reason):
    """Shared initial/transition review validation; no provenance or authority grant."""
    import base64
    import re
    a.need(type(nonce) is str and re.fullmatch('[A-Za-z0-9_-]{43}',nonce) is not None,
           'runtime_enrollment_nonce_invalid')
    decoded = base64.urlsafe_b64decode(nonce+'=')
    a.need(base64.urlsafe_b64encode(decoded).decode().rstrip('=') == nonce, 'runtime_enrollment_nonce_invalid')
    review = parse_review(serialized_review)
    a.need(nonce not in canonical(review) and nonce not in operator and nonce not in reason,
           'runtime_enrollment_nonce_in_record')
    a.need(digest(review) == approved_review_sha256
           and review['selected_observation_sha256'] == approved_observation_sha256,
           'runtime_enrollment_approval_digest_mismatch')
    selected = next(record['observation'] for record in review['observations']
                    if record['observation_sha256'] == approved_observation_sha256)
    return review, selected


def enroll_runtime_profile(config, serialized_review, nonce, *, expected_generation, installation_id,
                           target_id, owner_id, source_binding_sha256, challenge_id, challenge_sha256,
                           approved_review_sha256, approved_observation_sha256, operator, reason,
                           confirm_private_log_review, confirm_enroll_runtime_profile):
    """Initial enrollment only. No ordinary v3 gate, key read or target mutation.

    Input files remain untrusted; confirmations attribute the trusted operator's
    independent review, not a machine-verified provenance claim.
    """
    a.need(type(config) is a.LocalAdministration, 'local_administration_required', 503)
    config.paths()
    a.need(confirm_private_log_review is True and confirm_enroll_runtime_profile is True,
           'explicit_runtime_enrollment_approval_required')
    _text(operator, 200)
    _text(reason, 2000)
    _integer(expected_generation, 1, 9223372036854775806)
    _integer(owner_id, 1, 9223372036854775807)
    for value in (installation_id,target_id,challenge_id):
        identity(value)
    for value in (source_binding_sha256,challenge_sha256,approved_review_sha256,approved_observation_sha256):
        r._check_sha(value)
    # Slice 2a emits exactly 32 random bytes as unpadded URL-safe base64.
    review, selected = _approved_review(serialized_review, nonce,
        approved_review_sha256=approved_review_sha256, approved_observation_sha256=approved_observation_sha256,
        operator=operator, reason=reason)
    with a.connect(config.control, write=True) as control:
        control.execute('BEGIN IMMEDIATE')
        schema.check_control(control)
        from .runtime_enrollment_transition_schema import require_no_pending
        require_no_pending(control)  # Initial enrollment cannot finalize a maintenance plan.
        head = a._audit_head(control)
        old = _deployment_binding(control)
        a.need(old['generation'] == expected_generation and digest(old) == source_binding_sha256,
               'runtime_enrollment_generation_or_binding_conflict')
        a.need(old['installation_id'] == installation_id and old['target_id'] == target_id and old['owner_id'] == owner_id,
               'runtime_enrollment_scope_mismatch')
        a.need(old['runtime_profile_sha256'] is None, 'runtime_profile_already_enrolled')
        a.need(old['control_identity'] == asdict(a.target_identity(config.control)), 'control_identity_mismatch', 503)
        with a.connect(config.target, write=True) as target:
            target.execute('BEGIN IMMEDIATE')
            target.execute('PRAGMA query_only=ON')
            a._verify(config, control, target, old)
            owner = target.execute('SELECT role,email_verified_at FROM community_reviewers WHERE id=?',(owner_id,)).fetchone()
            a.need(owner is not None and owner['role'] == 'owner' and owner['email_verified_at'], 'verified_project_owner_required')
            now = _utc_now()  # Never use the CLI's time captured before lock acquisition.
            challenge, checked = evidence._challenge(control, challenge_id, challenge_sha256, now)
            a.need(checked == old, 'runtime_enrollment_binding_changed')
            a.need(hmac.compare_digest(hashlib.sha256(nonce.encode('ascii')).hexdigest(),challenge['nonce_sha256']),
                   'runtime_enrollment_nonce_mismatch')
            validate_review_scope(review, challenge, old, now)
            generation = expected_generation + 1
            profile = dict(format='recognition-runtime-profile-v1', installation_id=installation_id,
                generation=generation, role='runtime', **{k:selected[k] for k in PHYSICAL_FIELDS},
                target_id=target_id, owner_id=owner_id, challenge_id=challenge_id,
                observation_sha256=approved_observation_sha256, evidence_channel=evidence.CHANNEL,
                observed_at=selected['observed_at'], created_at=a.timestamp(now), operator=operator, reason=reason,
                audit_sequence=head['sequence'] + 1 if head else 1)
            profile['profile_sha256'] = digest(profile)
            body = dict(old,generation=generation,previous_sha256=digest(old),at_utc=now,
                        runtime_profile_sha256=profile['profile_sha256'],production_state='NOT_ACTIVATED')
            control.execute('SAVEPOINT enroll_runtime_profile')
            try:
                control.execute(f"INSERT INTO {r.PROFILES} ({','.join(profile)}) VALUES ({','.join('?' for _ in profile)})",tuple(profile.values()))
                a._invalidate(control)
                if control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_approvals'").fetchone():
                    from .approvals import _invalidate_all
                    _invalidate_all(control, operator, now, 'runtime-profile-enrolled')
                control.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(generation,canonical(body),digest(body)))
                a._audit(control,'runtime_profile_enrolled',operator,now,dict(reason=reason,
                    previous_generation=expected_generation,generation=generation,
                    source_binding_sha256=digest(old),binding_sha256=digest(body),challenge_sha256=challenge_sha256,
                    profile_sha256=profile['profile_sha256'],observation_sha256=approved_observation_sha256,
                    review_sha256=approved_review_sha256,private_log_review_confirmed=True,
                    enrollment_confirmed=True,review=review))
                schema.check_control(control)
                a._audit_head(control)
                a.need(asdict(a.target_identity(control)) == old['control_identity'], 'control_identity_mismatch',503)
                a._verify(config,control,target,old)
                owner = target.execute('SELECT role,email_verified_at FROM community_reviewers WHERE id=?',(owner_id,)).fetchone()
                a.need(owner is not None and owner['role'] == 'owner' and owner['email_verified_at'], 'verified_project_owner_required')
                final_time = a.timestamp(_utc_now())
                a.need(profile['created_at'] <= final_time < challenge['expires_at'], 'runtime_enrollment_expired_or_clock_rollback')
                control.execute('RELEASE enroll_runtime_profile')
                control.commit()  # Retain target reservation; target always rolls back.
            except BaseException:
                if control.in_transaction:
                    control.rollback()
                raise
    return dict(generation=generation,profile_sha256=profile['profile_sha256'],
                production_state='NOT_ACTIVATED',runtime_access='BLOCKED')
