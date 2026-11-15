"""Trusted-administrator recovery decision, NOT proof of storage continuity.

Only the execution-claim schema installer consumes these immutable audit events.
No identity verifier, runtime authority or authentication policy consumes them.
"""

from contextlib import contextmanager
from pathlib import Path
import re

from . import administration as a, runtime_execution_claim_schema as claims
from . import runtime_validation as runtime
from .rules import digest
from .trust import load, require


AUTHORIZED = 'deployment_claim_schema_recovery_authorized'
CONSUMED = 'deployment_claim_schema_recovery_consumed'
LIFETIME = 600
BOUNDARY = ('This recovery is an explicit trusted-administrator authorization that accepts '
            'unresolved storage-continuity uncertainty for this specific control-schema migration. '
            'It does not establish physical continuity and does not protect against a trusted '
            'administrator deliberately presenting a coherent clone.')


def _mount(path, device):
    """Current Linux mount observation only; neither provenance nor attestation."""
    def unescape(value):
        return re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), value)
    candidates = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        left, right = line.split(' - ', 1)
        parts, fs = left.split(), right.split()
        mount = Path(unescape(parts[4]))
        if path == mount or mount in path.parents:
            candidates.append((len(mount.parts), parts, fs))
    require(bool(candidates), 'claim_recovery_mount_missing')
    _, parts, fs = max(candidates, key=lambda item: item[0])
    require(fs[0] in ('nfs', 'nfs4'), 'claim_recovery_nfs_required')
    import os
    require(parts[2] == f'{os.major(device)}:{os.minor(device)}', 'claim_recovery_mount_device_mismatch')
    return dict(filesystem=fs[0], source=unescape(fs[1]), root=unescape(parts[3]),
                mount_target=unescape(parts[4]), major_minor=parts[2])


def snapshot(config, control, target, *, installed=False):
    """Exact, freshly validated candidate. It intentionally makes no continuity claim."""
    from .runtime_evidence import _observation
    from .local_readiness import _state
    binding, profile, _ = runtime._history(control)
    require(binding['generation'] == 5, 'claim_recovery_generation_required')
    require(binding['production_state'] == 'NOT_ACTIVATED', 'claim_recovery_requires_not_activated')
    if control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_local_activation'").fetchone():
        require(_state(control, binding)['state'] == 'NOT_ACTIVATED', 'claim_recovery_requires_not_activated')
    observed, current_control = _observation(control, target, config.target, config.control, binding)
    current_target = observed['observation']
    for old, new in ((binding['control_identity'], current_control),
                     (binding['target']['observation'], current_target)):
        require(set(old) == set(new) == {'hostname', 'database', 'device', 'inode'}
                and all(old[k] == new[k] for k in ('hostname', 'database', 'inode')),
                'claim_recovery_non_device_mismatch')
        require(type(new['device']) is int and new['device'] >= 0, 'claim_recovery_device_invalid')
    require(current_control != binding['control_identity']
            or current_target != binding['target']['observation'], 'claim_recovery_device_unchanged')
    mounts = [_mount(Path(item['database']), item['device']) for item in (current_target, current_control)]
    require(mounts[0] == mounts[1], 'claim_recovery_mount_pair_mismatch')
    source = load(control.execute('SELECT body_json FROM recognition_admin_bindings WHERE generation=4').fetchone()[0])
    enrollment = control.execute('SELECT body_sha256 FROM recognition_admin_audit WHERE sequence=?',
                                 (profile['audit_sequence'],)).fetchone()[0]
    return dict(format='deployment-claim-schema-recovery-v1', operation=claims.ACTION,
                migration_id=claims.MIGRATION, migration_definitions_sha256=digest(claims.definitions()),
                installation_id=binding['installation_id'], generation=5, target_id=binding['target_id'],
                production_state='NOT_ACTIVATED',
                owner_id=binding['owner_id'], binding_sha256=digest(binding),
                profile_sha256=profile['profile_sha256'], enrollment_binding_sha256=digest(source),
                enrollment_audit_sha256=enrollment, recorded_target=binding['target']['observation'],
                recorded_control=binding['control_identity'], observed_target=current_target,
                observed_control=current_control, target_schema_sha256=observed['schema_sha256'],
                control_schema_sha256=claims.manifest(control, exclude=tuple(claims.definitions()) if installed else ()),
                mount=mounts[0], boundary=BOUNDARY)


@contextmanager
def _reserved(config, *, write):
    require(type(config) is a.LocalAdministration, 'local_administration_required')
    config.paths()
    with a.connect(config.control, write=write) as control:
        control.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        with a.connect(config.target, write=write) as target:
            target.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            target.execute('PRAGMA query_only=ON')
            yield control, target


def preview(config):
    with _reserved(config, write=False) as (control, target):
        require(not control.execute('SELECT 1 FROM sqlite_master WHERE name=?', (claims.CLAIMS,)).fetchone(),
                'claim_recovery_already_installed')
        body = snapshot(config, control, target)
        return dict(snapshot=body, snapshot_sha256=digest(body))


def authorize(config, *, approved_snapshot_sha256, owner_id, operator, reason):
    runtime.enrollment._text(operator, 200)
    runtime.enrollment._text(reason, 2000)
    require(type(owner_id) is int, 'claim_recovery_owner_mismatch')
    with _reserved(config, write=True) as (control, target):
        require(not control.execute('SELECT 1 FROM sqlite_master WHERE name=?', (claims.CLAIMS,)).fetchone(),
                'claim_recovery_already_installed')
        body = snapshot(config, control, target)
        require(owner_id == body['owner_id'], 'claim_recovery_owner_mismatch')
        require(digest(body) == approved_snapshot_sha256, 'claim_recovery_preview_mismatch')
        now = runtime._utc_now()
        subject = dict(state='AUTHORIZED', snapshot=body, owner_id=owner_id, operator=operator, reason=reason,
                       created_at=a.timestamp(now), expires_at=a.timestamp(now)+LIFETIME,
                       previous_audit_sha256=a._audit_head(control)['body_sha256'])
        a._audit(control, AUTHORIZED, operator, now, subject)
        require(snapshot(config, control, target) == body, 'claim_recovery_observation_changed')
        require(subject['created_at'] <= a.timestamp(runtime._utc_now()) < subject['expires_at'], 'claim_recovery_expired')
        result = dict(recovery_sha256=a._audit_head(control)['body_sha256'], expires_at=subject['expires_at'])
        control.commit()
        return result


def validate(config, control, target, recovery_sha256):
    a._audit_head(control)
    rows = control.execute('SELECT body_json FROM recognition_admin_audit WHERE body_sha256=?',
                           (recovery_sha256,)).fetchall()
    require(len(rows) == 1, 'claim_recovery_not_found')
    event = load(rows[0][0])
    require(digest(event) == recovery_sha256 and event['action'] == AUTHORIZED, 'claim_recovery_invalid')
    for row in control.execute('SELECT body_json FROM recognition_admin_audit'):
        other = load(row[0])
        require(not (other['action'] == CONSUMED and other['subject']['recovery_sha256'] == recovery_sha256),
                'claim_recovery_replayed')
    require(a._audit_head(control)['body_sha256'] == recovery_sha256, 'claim_recovery_state_changed')
    subject = event['subject']
    now = a.timestamp(runtime._utc_now())
    require(subject['created_at'] == a.timestamp(event['at_utc'])
            and subject['expires_at'] == subject['created_at']+LIFETIME
            and subject['created_at'] <= now < subject['expires_at'], 'claim_recovery_expired')
    require(subject['state'] == 'AUTHORIZED'
            and event['actor'] == subject['operator'] and subject['owner_id'] == subject['snapshot']['owner_id']
            and event['previous_sha256'] == subject['previous_audit_sha256'], 'claim_recovery_invalid')
    require(snapshot(config, control, target) == subject['snapshot'], 'claim_recovery_scope_changed')
    return subject['snapshot']


def finish(config, control, target, recovery_sha256, expected):
    require(snapshot(config, control, target, installed=True) == expected, 'claim_recovery_observation_changed')
    row = control.execute('SELECT body_json FROM recognition_admin_audit WHERE body_sha256=?',
                          (recovery_sha256,)).fetchone()
    require(a.timestamp(runtime._utc_now()) < load(row[0])['subject']['expires_at'], 'claim_recovery_expired')
    migration = a._audit_head(control)
    require(load(migration['body_json'])['action'] == claims.ACTION, 'claim_recovery_migration_missing')
    a._audit(control, CONSUMED, load(row[0])['actor'], runtime._utc_now(),
             dict(state='CONSUMED', recovery_sha256=recovery_sha256, operation=claims.ACTION,
                  migration_audit_sha256=migration['body_sha256']))
    return load(row[0])['subject']['expires_at']


def inspect(config, recovery_sha256):
    """Durable read-only outcome inspection, including after lost acknowledgement."""
    config.paths()
    with a.connect(config.control) as control:
        control.execute('BEGIN')
        binding, profile, _ = runtime._history(control)
        events = [load(row[0]) for row in control.execute('SELECT body_json FROM recognition_admin_audit')]
        authorized = [event for event in events if digest(event) == recovery_sha256 and event['action'] == AUTHORIZED]
        require(len(authorized) == 1, 'claim_recovery_not_found')
        consumed = [event for event in events if event['action'] == CONSUMED
                    and event['subject']['recovery_sha256'] == recovery_sha256]
        require(len(consumed) <= 1, 'claim_recovery_invalid')
        installed = bool(control.execute('SELECT 1 FROM sqlite_master WHERE name=?', (claims.CLAIMS,)).fetchone())
        require(not consumed or installed, 'claim_recovery_invalid')
        from .local_readiness import _state
        activation = (_state(control, binding)['state'] if control.execute(
            "SELECT 1 FROM sqlite_master WHERE name='recognition_local_activation'").fetchone()
            else binding['production_state'])
        return dict(recovery_sha256=recovery_sha256, state='CONSUMED' if consumed else 'AUTHORIZED',
                    installed=installed, generation=binding['generation'], installation_id=binding['installation_id'],
                    profile_sha256=profile['profile_sha256'], activation_state=activation, execution_authority=False,
                    expires_at=authorized[0]['subject']['expires_at'])
