"""Read-only deployment-side claim disposition DATA, never admission authority."""

from dataclasses import asdict

from . import administration as a, runtime_validation as runtime
from . import runtime_execution_claims as claims, runtime_execution_claim_schema as schema
from .rules import digest
from .trust import load, require


def inspect_claims(config):
    """Inspect one committed control snapshot, without opening target or key.

    Like existing claim inspection, this requires strict deployment identity.
    It is not an activated runtime owner, authentication or a retry/recovery API.
    No caller clock, replacement scope, claim filter or detached claim is accepted.
    Errors fail closed; callers must not treat them as an empty inventory.
    """
    require(type(config) is a.LocalAdministration, 'local_administration_required')
    config.paths()
    clock = claims._Clock()
    with a.connect(config.control) as control:
        control.execute('BEGIN')
        binding, profile, head = runtime._history(control)
        require(asdict(a.target_identity(control)) == binding['control_identity']
                == asdict(a.target_identity(config.control)), 'control_identity_mismatch')
        require(str(config.target) == binding['target']['observation']['database'], 'target_path_mismatch')
        return _inspect_reserved(control, binding, profile, head, clock)


def _inspect_reserved(control, binding, profile, head, clock):
    """Fixed inventory for an owner that already verified the complete history.

    Borrowed handles stay private. This does not register an owner, accept a
    detached claim, authenticate a caller or replace physical identity checks.
    """
    require(control.execute('SELECT 1 FROM sqlite_master WHERE name=?', (schema.CLAIMS,)).fetchone()
                is not None, 'runtime_claim_schema_required')
    rows = control.execute('SELECT * FROM '+schema.CLAIMS+' ORDER BY claim_id').fetchall()
    records = []
    for row in rows:
        body = schema._body(row['body_json'], row['body_sha256'])
        scope = body['runtime_scope']
        require(all(scope[key] == binding[key] == profile[key]
                        for key in ('installation_id', 'target_id', 'owner_id', 'generation'))
                    and scope['binding_sha256'] == digest(binding)
                    and scope['runtime_profile_sha256'] == profile['profile_sha256'],
                    'runtime_claim_disposition_scope_mismatch')
        event = control.execute('SELECT state,at FROM '+schema.HISTORY+
                                    ' WHERE claim_id=? ORDER BY sequence DESC LIMIT 1',
                                    (row['claim_id'],)).fetchone()
        # _history/check_control already validates the complete immutable
        # claim/event/audit graph, including transitions and expiry columns.
        require(event is not None, 'runtime_execution_claim_genesis_missing')
        records.append((row, event))
    checked, now = clock.read()
    require(head is None or now >= a.timestamp(load(head['body_json'])['at_utc']),
                'runtime_claim_clock_anomaly')
    result = []
    for row, event in records:
        require(now >= row['issued_at'] and now >= event['at'], 'runtime_claim_clock_anomaly')
        state = event['state']
        if state == 'ISSUED':
            disposition = 'LIVE_ISSUED' if now < row['expires_at'] else 'EXPIRED_ISSUED'
        else:
            require(state in {'EXPIRED', 'REVOKED', 'CONSUMED', 'RECOVERY_REQUIRED'},
                        'runtime_execution_claim_transition')
            disposition = state
        result.append(dict(claim_id=row['claim_id'], operation_id=row['operation_id'],
                state=state, disposition=disposition,
                blocks_readiness=disposition in {'LIVE_ISSUED', 'RECOVERY_REQUIRED'},
                completion='NOT_ESTABLISHED',
                commit_outcome='RECOVERY_REQUIRED' if state == 'RECOVERY_REQUIRED' else 'NOT_ASSESSED'))
    return dict(checked_at_utc=checked, snapshot_only=True, claims=result,
                    execution_authority=False, retry_authorized=False)
