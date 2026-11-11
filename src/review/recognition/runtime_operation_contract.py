"""Slice 4a: detached proposal contracts, never persistence or admission.

Current-scope checks require a live Slice 3a context. That manager validates
durable enrollment/history and actual identity before entry and before commit.
No identity mapping, raw connection, authentication or writer capability is
accepted or returned here. In-memory preparation data is not a durable event.
"""

from . import dependencies, events, operations, permanent
from . import runtime_scope_validation, runtime_profile_schema as profiles
from . import runtime_validation as runtime
from .rules import canonical, digest
from .trust import fields, identity, load, require, utc


TARGET_FORMAT = 'recognition-runtime-operation-target-v1'
OPERATION_FORMAT = 'recognition-local-operation-v2'
TARGET_FIELDS = frozenset('''format installation_id target_id generation owner_id
    binding_sha256 runtime_profile_sha256 auth_epoch mfa_epoch'''.split())
CREATION_FIELDS = frozenset('''request_id request_sha256 actor_id primary_sha256 session_sha256'''.split())
ENVELOPE_FIELDS = frozenset('''format operation_version initial_state operation_id event_id event_sha256
    preparation_id preparation_sha256 parent_event_id dependencies_sha256 family action writer_manifest_sha256
    target_observation rule rule_sha256 population_sha256 member_ids accounting_policy created_at_utc
    frozen_at_utc provenance local_target creation'''.split())


def _json(value, depth=0):
    """Reject lossy/non-JSON values before serialization (including subclasses)."""
    require(depth <= 64, 'runtime_contract_nesting_limit')
    if type(value) is dict:
        for key, item in value.items():
            require(type(key) is str and '\0' not in key, 'runtime_contract_invalid_key')
            if key.endswith('_utc') and item is not None:
                utc(item)
            _json(item, depth+1)
    elif type(value) is list:
        for item in value:
            _json(item, depth+1)
    elif type(value) is str:
        require('\0' not in value, 'runtime_contract_nul')
    else:
        require(value is None or type(value) in (int, bool), 'runtime_contract_non_json_number')


def _copy(value):
    _json(value)
    return load(canonical(value))


def _positive(value):
    require(type(value) is int and 1 <= value <= 2**63-1, 'runtime_contract_integer')


def _current(context):
    # These are guarded views, not raw handles. Callers cannot supply a scope
    # dictionary or a historical validate_runtime_snapshot() result instead.
    require(type(context) in (runtime.RuntimeValidationContext, runtime_scope_validation.RuntimeReadView),
            'runtime_contract_context_required')
    return runtime_scope_validation._contract_parts(context)


def _shape(value):
    _json(value)
    fields(value, TARGET_FIELDS)
    require(value['format'] == TARGET_FORMAT, 'runtime_contract_target_format')
    for key in ('installation_id', 'target_id'):
        identity(value[key])
    for key in ('binding_sha256', 'runtime_profile_sha256'):
        profiles._check_sha(value[key])
    for key in ('generation', 'owner_id', 'auth_epoch', 'mfa_epoch'):
        _positive(value[key])


def build_target(context):
    """Detached current target data. Does not authenticate a caller."""
    _, binding, scope, mfa_epoch = _current(context)
    value = dict(format=TARGET_FORMAT, installation_id=scope['installation_id'],
        target_id=scope['target_id'], generation=scope['generation'], owner_id=scope['owner_id'],
        binding_sha256=digest(binding), runtime_profile_sha256=scope['profile_sha256'],
        auth_epoch=scope['auth_epoch'], mfa_epoch=mfa_epoch)
    _shape(value)
    return value


def validate_target(value, *, context):
    """Validate against locked, manager-validated durable scope; no cached authority."""
    _shape(value)
    expected = build_target(context)
    for key in sorted(TARGET_FIELDS):
        require(value[key] == expected[key], 'runtime_contract_target_mismatch:' + key)
    return _copy(value)


def parse_target(serialized, *, context):
    value = load(serialized)
    require(canonical(value) == serialized, 'runtime_contract_noncanonical_json')
    return validate_target(value, context=context)


def require_same_target(left, right, *, context):
    validate_target(left, context=context)
    validate_target(right, context=context)
    require(canonical(left) == canonical(right), 'runtime_contract_targets_differ')


def _physical(value, *, context):
    fields(value, ('hostname', 'database', 'device', 'inode'))
    runtime._physical(value)  # Existing strict paths, NUL and lossless integer rules.
    control, _, scope, _ = _current(context)
    profile = control.execute(f'SELECT * FROM {profiles.PROFILES} WHERE profile_sha256=?',
                              (scope['profile_sha256'],)).fetchone()
    # Do not coerce submitted observations; bool/float/decimal text are rejected.
    require(value['hostname'] == profile['hostname'] and value['database'] == profile['target_path']
        and str(value['device']) == profile['target_device'] and str(value['inode']) == profile['target_inode'],
        'runtime_contract_observation_mismatch')


def _frozen(value, *, context):
    """Check detached content; does NOT establish durable event history/freshness."""
    value = _copy(value)
    fields(value, ('preparation', 'event'))
    p, e = value['preparation'], value['event']
    fields(p, ('format', 'preparation_id', 'request', 'generated_at_utc', 'generator',
               'target_observation', 'manifest', 'manifest_sha256', 'population_sha256', 'dependencies'))
    fields(e, ('format', 'event_id', 'preparation_id', 'preparation_sha256', 'parent_event_id', 'frozen_at_utc'))
    fields(p['request'], events.REQUEST_FIELDS)
    require(p['format'] == 'recognition-preparation-v1' and p['generator'] == 'permanent._prepare:v1'
            and e['format'] == 'recognition-event-v1', 'runtime_contract_preparation_format')
    for value in (p['preparation_id'], e['event_id'], e['preparation_id']):
        identity(value)
    if e['parent_event_id'] is not None:
        identity(e['parent_event_id'])
    for value in (p['generated_at_utc'], e['frozen_at_utc'], p['manifest']['evaluation_at_utc'],
                  p['request']['evaluation_at_utc']):
        utc(value)
    require(utc(p['generated_at_utc']) <= utc(e['frozen_at_utc']), 'runtime_contract_time_order')
    manifest, request = p['manifest'], p['request']
    require(utc(manifest['inputs']['cutoff_utc']) <= utc(manifest['evaluation_at_utc']),
            'runtime_contract_evaluation_before_cutoff')
    dependencies.validate_manifest(manifest)
    permanent._validate_manifest(manifest)
    dependencies.validate_binding(p['dependencies'], manifest)
    require(e['preparation_id'] == p['preparation_id'] and e['preparation_sha256'] == digest(p)
        and e['parent_event_id'] == request['parent_event_id']
        and p['manifest_sha256'] == digest(manifest) and p['population_sha256'] == digest(manifest['candidates']),
        'runtime_contract_frozen_mismatch')
    require(all(request[k] == manifest[k] for k in ('family', 'inputs', 'evaluation_at_utc'))
        and request['review_reference'] == manifest['authorization_reference'], 'runtime_contract_request_mismatch')
    target = build_target(context)
    require(request['generation_reference'] == target['installation_id'] + ':' + str(target['generation']),
            'runtime_contract_preparation_generation')
    _physical(p['target_observation'], context=context)
    return dict(preparation=p, event=e)


def _creation(value, *, context):
    value = _copy(value)
    fields(value, CREATION_FIELDS)
    identity(value['request_id'])
    _positive(value['actor_id'])
    for key in ('request_sha256', 'primary_sha256', 'session_sha256'):
        profiles._check_sha(value[key])
    control, _, scope, _ = _current(context)
    require(value['actor_id'] == scope['owner_id'], 'runtime_contract_creation_owner')
    for kind in ('primary', 'session'):
        table = 'recognition_admin_primary' if kind == 'primary' else 'recognition_admin_sessions'
        proof = control.execute(f'SELECT * FROM {table} WHERE token_hash=?', (value[kind + '_sha256'],)).fetchone()
        ref = control.execute(f'SELECT * FROM {profiles.AUTH} WHERE token_kind=? AND token_hash=?',
                              (kind, value[kind + '_sha256'])).fetchone()
        require(proof is not None and ref is not None and proof['actor'] == scope['owner_id']
            and proof['generation'] == scope['generation'] and ref['profile_sha256'] == scope['profile_sha256']
            and proof['created'] == ref['created_at'], 'runtime_contract_creation_reference')
        if kind == 'session':
            require(proof['primary_hash'] == value['primary_sha256'], 'runtime_contract_creation_parent')
    # These are historical references: intentionally not session authentication,
    # expiry/revocation checks, TOTP verification or a call to auth._deny().
    return value


def build_operation(context, *, frozen, operation_id, creation, created_at_utc):
    """Construct detached v2 proposal data, without writing or admitting it."""
    identity(operation_id)
    utc(created_at_utc)
    frozen = _frozen(frozen, context=context)
    creation = _creation(creation, context=context)
    require(utc(frozen['event']['frozen_at_utc']) <= utc(created_at_utc), 'runtime_contract_time_order')
    require(frozen['preparation']['request']['preparer_id'] == str(creation['actor_id']),
            'runtime_contract_preparer_mismatch')
    body = operations._envelope(frozen, operation_id, operations.LOCAL_POLICY, created_at_utc)
    del body['synthetic_contract_only'], body['enrollment']
    body.update(format=OPERATION_FORMAT, operation_version=2, initial_state='PREPARED',
                local_target=build_target(context), creation=creation)
    require(len(set(body['member_ids'])) == len(body['member_ids']), 'duplicate_population_member')
    return _copy(body)


def validate_operation(value, *, context, frozen, operation_sha256):
    """Verify content against separate frozen data/digest, not against itself."""
    _json(value)
    require(type(value) is dict and value.get('format') == OPERATION_FORMAT, 'runtime_contract_legacy_or_unknown_format')
    fields(value, ENVELOPE_FIELDS)
    require(type(value['operation_version']) is int and value['operation_version'] == 2,
            'runtime_contract_operation_version')
    profiles._check_sha(operation_sha256)
    validate_target(value['local_target'], context=context)
    expected = build_operation(context, frozen=frozen, operation_id=value['operation_id'],
                              creation=value['creation'], created_at_utc=value['created_at_utc'])
    require(canonical(value) == canonical(expected), 'runtime_contract_envelope_mismatch')
    require(digest(value) == operation_sha256, 'runtime_contract_operation_digest_mismatch')
    return _copy(value)


def parse_operation(serialized, **kwargs):
    value = load(serialized)
    require(canonical(value) == serialized, 'runtime_contract_noncanonical_json')
    return validate_operation(value, **kwargs)
