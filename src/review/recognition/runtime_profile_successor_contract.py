"""Pure, closed G5/G6 custodian-signing contract. No SQLite or key access."""
import re
from .rules import canonical, digest

PREPARE = 'runtime_profile_device_successor_prepare'
COMPLETE = 'runtime_profile_device_successor_complete'
INSPECT = 'runtime_profile_device_successor_inspect'
PURPOSES = (PREPARE, COMPLETE, INSPECT)
POLICY = 'recognition-g5-g6-device-successor-v1'
BOUNDARY = ('This authorization accepts unresolved storage-continuity uncertainty for the exact approved device transition. '
            'It does not establish physical continuity or authorize arbitrary filesystem changes.')
SOURCE_BINDING = '055d7f03d6dae4157d067e086a17a5b3f6baecb461cf4f4fbd7c1f6e7634cb0b'
SOURCE_PROFILE = '6ee02a54dce497afe4f6d0185f614ac0229b41a5831ab71b9f5e3c6cf72e6560'
SOURCE = dict(target=dict(hostname='blue-liveweb36', database='/home/davidpoms/dmv_bus_stops.db', device=57, inode=224816447),
              control=dict(hostname='blue-liveweb36', database='/home/davidpoms/recognition-admin-control.db', device=57, inode=224805688))


def need(value):
    if not value:
        raise ValueError('runtime_successor_contract')


def fields(value, names):
    need(type(value) is dict and set(value) == set(names.split()))


def sha(value):
    need(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None)


def destination():
    return {key: dict(value, device=49) for key, value in SOURCE.items()}


def validate_scope(value):
    fields(value, 'policy source_generation destination_generation binding_sha256 profile_sha256 enrollment_audit_sha256 '
           'installation_id target_id owner_id source destination target_schema_sha256 control_schema_sha256 '
           'owner_key_sha256 auth_epoch mfa_epoch activation_sha256 stop_sha256 recovery_sha256 '
           'root_sha256 audit_sha256 boundary')
    need(value['policy'] == POLICY and type(value['source_generation']) is int and value['source_generation'] == 5
         and type(value['destination_generation']) is int and value['destination_generation'] == 6)
    need(value['binding_sha256'] == SOURCE_BINDING and value['profile_sha256'] == SOURCE_PROFILE
         and canonical(value['source']) == canonical(SOURCE) and canonical(value['destination']) == canonical(destination())
         and value['boundary'] == BOUNDARY)
    for key in value:
        if key.endswith('_sha256'):
            sha(value[key])
    for key in ('owner_id', 'auth_epoch', 'mfa_epoch'):
        need(type(value[key]) is int and value[key] > 0)
    from uuid import UUID
    for key in ('installation_id', 'target_id'):
        need(str(UUID(value[key])) == value[key])


def approval(subject, physical, expires, mandate):
    kind = subject['kind']
    need(kind in PURPOSES)
    return dict(target=physical, environment='production', family=POLICY,
                permission='inspection' if kind == INSPECT else 'migration', action=kind,
                operation_sha256=digest(subject), policy_sha256=digest(POLICY),
                population_sha256=None, reference=mandate, expires_at_utc=expires)


def validate_envelope(body, root):
    fields(body, 'format mandate installation_id binding_sha256 holder subject target control issued_at_utc expires_at_utc approvals')
    need(body['format'] == root['format'] and body['mandate'] == root['mandate']
         and body['installation_id'] == root['installation_id'] and body['binding_sha256'] == SOURCE_BINDING)
    fields(body['holder'], 'kind actor_id')
    need(body['holder']['kind'] == 'governance_custodian' and type(body['holder']['actor_id']) is int
         and body['holder']['actor_id'] == root['owner_id'])
    subject = body['subject']
    need(type(subject) is dict)
    fields(subject, 'kind authorization_id scope operator reason' if subject.get('kind') == PREPARE else
           'kind plan' if subject.get('kind') == COMPLETE else 'kind authorization_id')
    need(subject['kind'] in PURPOSES)
    if subject['kind'] == PREPARE:
        validate_scope(subject['scope'])
        for key, limit in (('operator', 200), ('reason', 2000)):
            need(type(subject[key]) is str and 1 <= len(subject[key].strip()) <= limit and '\0' not in subject[key])
    elif subject['kind'] == COMPLETE:
        plan = subject['plan']
        fields(plan, 'format authorization_id preparation_sha256 challenge_sha256 scope review review_sha256 '
               'selected_observation_sha256 profile_template binding_template template_sha256 invalidations '
               'backups created_at_utc deadline_at_utc execution_authority')
        need(plan['format'] == POLICY and plan['execution_authority'] is False)
        validate_scope(plan['scope'])
        for key in ('preparation_sha256', 'challenge_sha256', 'review_sha256', 'selected_observation_sha256', 'template_sha256'):
            sha(plan[key])
    from uuid import UUID
    identifier = subject['plan']['authorization_id'] if subject['kind'] == COMPLETE else subject['authorization_id']
    need(str(UUID(identifier)) == identifier)
    need(canonical(dict(target=body['target'], control=body['control'])) == canonical(destination()))
    need(body['approvals'] == [approval(subject, body['target'], body['expires_at_utc'], root['mandate'])])
    need(len(canonical(body).encode('utf-8')) <= 262144)
    return body
