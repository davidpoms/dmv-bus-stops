"""Deployment-only challenge issuance. No runtime authentication or enrollment.

The trusted local operator is authenticated by host access, never by supplied
identity strings. This deliberately does not open the ordinary v3 authority gate.
"""

from dataclasses import asdict
import hashlib
import secrets
from uuid import uuid4

from . import administration as a, administration_schema as schema
from . import runtime_profile_schema as r
from .rules import digest
from .trust import identity, load


def _deployment_binding(control):
    """Verify history for this ceremony only; never return runtime authority."""
    previous = None
    rows = control.execute('SELECT * FROM recognition_admin_bindings ORDER BY generation').fetchall()
    a.need(bool(rows), 'installation_not_initialized', 503)
    for generation, row in enumerate(rows, 1):
        body = load(row['body_json'])
        a.need(row['generation'] == generation and type(body.get('generation')) is int
               and body['generation'] == generation and digest(body) == row['body_sha256']
               and 'previous_sha256' in body and body['previous_sha256'] == previous,
               'installation_history_integrity_failure', 503)
        previous = row['body_sha256']
    a.need(body.get('format') == r.V3, 'runtime_challenge_requires_v3', 503)
    return body


def issue_challenge(config, *, expected_generation, installation_id, target_id,
                    owner_id, source_binding_sha256, operator, reason, now):
    """Return the nonce once to the local caller; persist only its SHA256.

    Lock control first, then reserve target through the control commit. No target
    SQL mutations, key reads, revocations, generation changes or profiles occur.
    """
    a.need(type(config) is a.LocalAdministration, 'local_administration_required', 503)
    config.paths()
    identity(installation_id)
    identity(target_id)
    a.need(type(expected_generation) is int and expected_generation > 0
           and type(owner_id) is int and owner_id > 0, 'runtime_challenge_scope_required')
    a.need(type(operator) is str and operator.strip() and len(operator) <= 200 and '\x00' not in operator
           and type(reason) is str and reason.strip() and len(reason) <= 2000 and '\x00' not in reason,
           'runtime_challenge_ceremony_required')
    r._check_sha(source_binding_sha256)
    issued_at = a.timestamp(now)
    a.need(0 <= issued_at <= r.MAX_TIME - 600, 'runtime_challenge_time_invalid')
    with a.connect(config.control, write=True) as control:
        control.execute('BEGIN IMMEDIATE')
        schema.check_control(control)
        head = a._audit_head(control)
        binding = _deployment_binding(control)
        a.need(binding['generation'] == expected_generation, 'runtime_challenge_generation_conflict')
        a.need(binding['installation_id'] == installation_id and binding['target_id'] == target_id
               and binding['owner_id'] == owner_id and digest(binding) == source_binding_sha256,
               'runtime_challenge_scope_mismatch')
        a.need(binding['control_identity'] == asdict(a.target_identity(config.control)), 'control_identity_mismatch', 503)
        with a.connect(config.target, write=True) as target:
            target.execute('BEGIN IMMEDIATE')
            a._verify(config, control, target, binding)
            owner = target.execute('SELECT role,email_verified_at FROM community_reviewers WHERE id=?', (owner_id,)).fetchone()
            a.need(owner is not None and owner['role'] == 'owner' and owner['email_verified_at'], 'verified_project_owner_required')
            a.need(binding['production_state'] == 'NOT_ACTIVATED', 'runtime_challenge_requires_not_activated')
            if control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_local_activation'").fetchone():
                from .local_readiness import _state
                a.need(_state(control, binding)['state'] == 'NOT_ACTIVATED', 'runtime_challenge_requires_not_activated')
            nonce = secrets.token_urlsafe(32)
            row = dict(challenge_id=str(uuid4()), format='recognition-runtime-enrollment-challenge-v1',
                installation_id=installation_id, source_generation=expected_generation,
                source_binding_sha256=source_binding_sha256, target_id=target_id, owner_id=owner_id,
                role='runtime', nonce_sha256=hashlib.sha256(nonce.encode()).hexdigest(),
                issued_at=issued_at, expires_at=issued_at + 600, operator=operator, reason=reason,
                audit_sequence=head['sequence'] + 1 if head else 1)
            row['challenge_sha256'] = digest(row)
            control.execute(f"INSERT INTO {r.CHALLENGES} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", tuple(row.values()))
            a._audit(control, 'runtime_enrollment_challenge_issued', operator, now,
                     dict(challenge_sha256=row['challenge_sha256'], reason=reason))
            schema.check_control(control)
            a.need(asdict(a.target_identity(control)) == binding['control_identity'], 'control_identity_mismatch', 503)
            a._verify(config, control, target, binding)
            control.commit()
    return dict(challenge=row, nonce=nonce)
