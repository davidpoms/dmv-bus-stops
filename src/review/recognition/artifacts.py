"""Strict synthetic artifact verification, deliberately disconnected from writers.

No production trust loader, enrollment registration, Authority, SQL or signing API.
The only verifier owns a fresh temporary root. Results are immutable data, never
writer authorization. This is not a sandbox against arbitrary Python execution.
"""

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import socket
import stat
import tempfile

from .authorization import AuthorizationError
from .rules import canonical, digest


FORMAT = 'recognition-synthetic-approval-v1'
ALGORITHM = 'Ed25519'
DOMAIN = b'DMV-recognition-synthetic-approval-v1\x00'
ENVELOPE = frozenset('format algorithm key_id payload signature'.split())
PAYLOAD = frozenset('''approval_id issuer_id approver_id environment enrollment_id
    enrollment_generation enrollment_sha256 target deployment_id family permission
    action operation_sha256 policy_sha256 rule_sha256 population_sha256 manifest_sha256
    snapshot_sha256 reference issued_at_utc not_before_utc expires_at_utc
    revocation_registry_id minimum_revocation_sequence usage evidence'''.split())
ENROLLMENT = frozenset('''enrollment_id enrollment_generation environment host_id
    hostname database_absolute_path device inode parent_directory_absolute_path
    parent_device parent_inode required_link_count deployment_id reference issuer_id
    issued_at_utc'''.split())
TARGET = frozenset('hostname database device inode'.split())
BINDINGS = frozenset('''family permission action operation_sha256 policy_sha256
    rule_sha256 population_sha256 manifest_sha256 snapshot_sha256 reference evidence'''.split())
# Action-specific evidence supplements, never replaces, independently computed bindings.
EVIDENCE = {
    'enqueue': {'activation_at_utc': 'time', 'historical_cutoff_utc': 'time',
                'sqlite_utc_provenance': 'optional_text'},
    'approve_closed_population': {'historical_operation_id': 'hash',
        'historical_qualified_sha256': 'hash', 'activation_at_utc': 'time',
        'frontier_at_utc': 'time', 'gap_assignment_ids': 'ids',
        'baseline_link_review_reference': 'text'},
    'process_delivery': {'assignment_id': 'positive'},
    'seal_pending': {'finality_approval_id': 'text', 'delivery_approval_id': 'text'},
    'finalize': {'review_package_sha256': 'hash'},
    'install': {'prerequisite_schema_sha256': 'hash'},
}
MATRIX = frozenset({
    ('first_look', 'capture', 'enqueue'),
    ('first_look', 'finality', 'approve_closed_population'),
    ('first_look', 'issuance', 'process_delivery'),
    ('first_look', 'issuance', 'seal_pending'),
    ('first_look', 'issuance', 'finalize'),
    ('geography_steward', 'issuance', 'finalize'),
    ('private_recognition', 'migration', 'install'),
    ('first_look', 'migration', 'install'),
})


def _require(value, code):
    if not value:
        raise AuthorizationError(code)


def _object(value, fields):
    _require(type(value) is dict and set(value) == set(fields), 'artifact_fields_invalid')


def _text(value):
    _require(type(value) is str and bool(value.strip()), 'artifact_text_invalid')


def _integer(value, minimum=0):
    _require(type(value) is int and minimum <= value <= 2**128 - 1, 'artifact_integer_invalid')


def _hash(value):
    _require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
             'artifact_hash_invalid')


def _time(value):
    _require(type(value) is str, 'artifact_time_invalid')
    try:
        result = datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        raise AuthorizationError('artifact_time_invalid') from None
    _require(result.strftime('%Y-%m-%dT%H:%M:%SZ') == value, 'artifact_time_noncanonical')
    return result


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'artifact_duplicate_key')
        result[key] = value
    return result


def _bad_number(value):
    raise AuthorizationError('artifact_number_invalid')


def _load(text):
    # Only serialized input: no mappings, subclasses or accepting custom objects.
    _require(type(text) is str and len(text) <= 1_000_000, 'artifact_json_required')
    try:
        return json.loads(text, object_pairs_hook=_pairs, parse_constant=_bad_number,
                          parse_float=_bad_number)
    except (ValueError, RecursionError) as error:
        if isinstance(error, AuthorizationError):
            raise
        raise AuthorizationError('artifact_json_invalid') from None


def canonical_payload_bytes(payload_json):
    """Synthetic signature input: DOMAIN + existing canonical JSON encoded UTF-8.

    Whitespace/key order on input are insignificant. Float syntax is forbidden in
    this profile. This helper does not validate approval semantics or grant trust.
    """
    payload = _load(payload_json)
    _object(payload, PAYLOAD)
    return DOMAIN + canonical(payload).encode('utf-8')


def _base64(value, size):
    _text(value)
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise AuthorizationError('artifact_base64_invalid') from None
    _require(len(raw) == size and base64.b64encode(raw).decode('ascii') == value,
             'artifact_base64_invalid')
    return raw


def _strings(value):
    _require(type(value) is list and all(type(x) is str and x.strip() for x in value),
             'artifact_string_list_invalid')
    _require(len(value) == len(set(value)), 'artifact_duplicate_value')


@dataclass(frozen=True)
class ValidatedArtifact:
    """An immutable snapshot of checked synthetic data, NOT an Authority/Authorization."""

    canonical_json: str
    sha256: str


class SyntheticArtifactVerifier:
    """Test-only trust context; cannot adopt an existing directory or grant writes.

    Public keys and identity/action grants are supplied explicitly by tests. No
    environment/file loader, callback, default key or production mode exists.
    """

    def __init__(self, trust_json):
        trust = _load(trust_json)
        _object(trust, {'keys', 'host_id', 'deployment_id', 'revocation_registry_id',
                        'max_registry_age_seconds', 'minimum_registry_sequence'})
        for name in ('host_id', 'deployment_id', 'revocation_registry_id'):
            _text(trust[name])
        _integer(trust['max_registry_age_seconds'], 1)
        _integer(trust['minimum_registry_sequence'])
        _require(type(trust['keys']) is list and bool(trust['keys']), 'synthetic_keys_required')
        ids, public_keys = set(), set()
        for key in trust['keys']:
            _object(key, {'key_id', 'issuer_id', 'public_key', 'grants'})
            for field in ('key_id', 'issuer_id'):
                _text(key[field])
            raw = _base64(key['public_key'], 32)
            _require(key['key_id'] not in ids and raw not in public_keys, 'synthetic_duplicate_key')
            ids.add(key['key_id'])
            public_keys.add(raw)
            _require(type(key['grants']) is list and bool(key['grants']), 'synthetic_grants_required')
            seen = set()
            for grant in key['grants']:
                _object(grant, {'approver_id', 'family', 'permission', 'action', 'max_lifetime_seconds'})
                for field in ('approver_id', 'family', 'permission', 'action'):
                    _text(grant[field])
                triple = tuple(grant[k] for k in ('family', 'permission', 'action'))
                _require(triple in MATRIX, 'synthetic_grant_invalid')
                identity = (grant['approver_id'], *triple)
                _require(identity not in seen, 'synthetic_duplicate_grant')
                seen.add(identity)
                _integer(grant['max_lifetime_seconds'], 1)
        self._trust_json = canonical(trust)
        self._temporary = tempfile.TemporaryDirectory(prefix='recognition-artifact-test-')
        self._root = Path(self._temporary.name).resolve()
        root_stat = self._root.stat()
        self._root_identity = (root_stat.st_dev, root_stat.st_ino)
        self._sequence = trust['minimum_registry_sequence']
        self._last_time = None
        self._registry_at_sequence = None
        self._closed = False

    @property
    def directory(self):
        return self._root

    def cleanup(self):
        self._closed = True
        self._temporary.cleanup()


def _context(verifier):
    _require(type(verifier) is SyntheticArtifactVerifier and not verifier._closed,
             'production_trust_configuration_unavailable')
    return _load(verifier._trust_json)


def validate_enrollment(enrollment_json, *, expected_sha256, enrollment_id,
                        enrollment_generation, trusted_now_utc, verifier=None):
    """Validate supplied synthetic enrollment against independent expected identity.

    Stats only new verifier-owned files. Does not open SQLite, register a target,
    authenticate an administrator, or produce writer authority.
    """
    trust = _context(verifier)
    value = _load(enrollment_json)
    _object(value, ENROLLMENT)
    _hash(expected_sha256)
    _text(enrollment_id)
    _integer(enrollment_generation, 1)
    for field in ENROLLMENT - {'enrollment_generation', 'device', 'inode', 'parent_device',
                                'parent_inode', 'required_link_count'}:
        _text(value[field])
    for field in ('device', 'inode', 'parent_device', 'parent_inode'):
        _integer(value[field])
    _integer(value['enrollment_generation'], 1)
    _integer(value['required_link_count'], 1)
    _require(value['required_link_count'] == 1, 'enrollment_link_count_invalid')
    _require(value['environment'] == 'production', 'enrollment_environment_mismatch')
    _require(value['host_id'] == trust['host_id'] and value['hostname'] == socket.gethostname(),
             'enrollment_host_mismatch')
    _require(value['deployment_id'] == trust['deployment_id'], 'enrollment_deployment_mismatch')
    _require(value['enrollment_id'] == enrollment_id and
             value['enrollment_generation'] == enrollment_generation, 'enrollment_generation_mismatch')
    _require(_time(value['issued_at_utc']) <= _time(trusted_now_utc), 'enrollment_future_issuance')
    _require(digest(value) == expected_sha256, 'enrollment_hash_mismatch')
    path = Path(value['database_absolute_path'])
    parent = Path(value['parent_directory_absolute_path'])
    _require(path.is_absolute() and parent.is_absolute() and path.parent == parent,
             'enrollment_path_invalid')
    # Reject outside targets lexically before even statting them.
    _require(path.is_relative_to(verifier.directory) and '..' not in path.parts,
             'synthetic_workspace_required')
    try:
        root_stat = verifier.directory.stat()
        _require((root_stat.st_dev, root_stat.st_ino) == verifier._root_identity,
                 'synthetic_root_changed')
        for item in (path, *path.parents):
            _require(not item.is_symlink() and not getattr(item, 'is_junction', lambda: False)(),
                     'enrollment_alias_rejected')
        _require(str(path.resolve(strict=True)) == value['database_absolute_path'] and
                 str(parent.resolve(strict=True)) == value['parent_directory_absolute_path'],
                 'enrollment_path_noncanonical')
        observed, parent_stat = path.stat(), parent.stat()
        _require(stat.S_ISREG(observed.st_mode), 'enrollment_regular_file_required')
        _require((observed.st_dev, observed.st_ino, observed.st_nlink) ==
                 (value['device'], value['inode'], 1), 'enrollment_file_identity_mismatch')
        _require((parent_stat.st_dev, parent_stat.st_ino) ==
                 (value['parent_device'], value['parent_inode']), 'enrollment_parent_identity_mismatch')
    except OSError:
        raise AuthorizationError('enrollment_target_unavailable') from None
    return ValidatedArtifact(canonical(value), digest(value))


def _binding(payload):
    triple = tuple(payload[k] for k in ('family', 'permission', 'action'))
    _require(triple in MATRIX, 'artifact_action_invalid')
    action = payload['action']
    nulls = {'snapshot_sha256'}
    if action in ('enqueue', 'install'):
        nulls |= {'population_sha256', 'manifest_sha256'}
    if action == 'install':
        nulls.add('rule_sha256')
    if action == 'process_delivery':
        nulls.add('manifest_sha256')
    if payload['family'] == 'geography_steward':
        nulls.remove('snapshot_sha256')
    for field in ('operation_sha256', 'policy_sha256', 'rule_sha256',
                  'population_sha256', 'manifest_sha256', 'snapshot_sha256'):
        if field in nulls:
            _require(payload[field] is None, 'artifact_null_binding_required')
        else:
            _hash(payload[field])
    if payload['manifest_sha256'] is not None:
        _require(payload['operation_sha256'] == payload['manifest_sha256'], 'artifact_manifest_mismatch')
    if action == 'install':
        _require(payload['operation_sha256'] == payload['policy_sha256'], 'artifact_schema_mismatch')
    if action == 'finalize':
        _require(payload['rule_sha256'] == payload['policy_sha256'], 'artifact_rule_mismatch')
    evidence = payload['evidence']
    schema = dict(EVIDENCE[action])
    if payload['family'] == 'geography_steward':
        schema.update(certification_approval_ids='strings', evaluation_at_utc='time')
    _object(evidence, schema)
    for field, kind in schema.items():
        value = evidence[field]
        if kind == 'hash':
            _hash(value)
        elif kind == 'time':
            _time(value)
        elif kind == 'positive':
            _integer(value, 1)
        elif kind == 'ids':
            _require(type(value) is list, 'artifact_ids_invalid')
            for item in value:
                _integer(item, 1)
            _require(value == sorted(set(value)), 'artifact_ids_invalid')
        elif kind == 'strings':
            _strings(value)
            _require(bool(value), 'artifact_certification_required')
        elif kind != 'optional_text' or value is not None:
            _text(value)
    if action in ('enqueue', 'approve_closed_population'):
        activation = _time(evidence['activation_at_utc'])
        if action == 'enqueue':
            _require(_time(evidence['historical_cutoff_utc']) <= activation, 'artifact_activation_invalid')
        else:
            _require(activation < _time(evidence['frontier_at_utc']), 'artifact_frontier_invalid')
    usage = payload['usage']
    if action == 'enqueue':
        _object(usage, {'mode', 'starts_at_utc', 'ends_at_utc'})
        _require(usage['mode'] == 'bounded_capture', 'artifact_usage_invalid')
        _require(_time(payload['not_before_utc']) <= _time(usage['starts_at_utc']) <
                 _time(usage['ends_at_utc']) <= _time(payload['expires_at_utc']), 'artifact_capture_window_invalid')
    else:
        _object(usage, {'mode', 'integrity_only_retries'})
        _require(usage['mode'] == 'exact_operation' and usage['integrity_only_retries'] is True,
                 'artifact_usage_invalid')


def _registry(registry_json, payload, key_id, trust, verifier, now):
    _require(registry_json is not None, 'revocation_registry_unavailable')
    registry = _load(registry_json)
    _object(registry, {'registry_id', 'sequence', 'issued_at_utc', 'expires_at_utc',
                      'revoked_approvals', 'revoked_issuers', 'revoked_keys',
                      'revoked_enrollments', 'revoked_deployments'})
    _text(registry['registry_id'])
    _integer(registry['sequence'])
    _require(registry['registry_id'] == payload['revocation_registry_id'] == trust['revocation_registry_id'],
             'revocation_registry_mismatch')
    _require(registry['sequence'] >= max(verifier._sequence, payload['minimum_revocation_sequence']),
             'revocation_registry_rollback')
    issued, expires = _time(registry['issued_at_utc']), _time(registry['expires_at_utc'])
    _require(issued <= now < expires and
             (now - issued).total_seconds() <= trust['max_registry_age_seconds'], 'revocation_registry_stale')
    frozen = canonical(registry)
    if registry['sequence'] == verifier._sequence and verifier._registry_at_sequence is not None:
        _require(frozen == verifier._registry_at_sequence, 'revocation_registry_equivocation')
    checks = {'revoked_approvals': payload['approval_id'], 'revoked_issuers': payload['issuer_id'],
              'revoked_keys': key_id, 'revoked_enrollments': payload['enrollment_id'],
              'revoked_deployments': payload['deployment_id']}
    for field in checks:
        _strings(registry[field])
    # Remember observed state even if it revokes this approval.
    verifier._sequence, verifier._registry_at_sequence = registry['sequence'], frozen
    for field, identity in checks.items():
        _require(identity not in registry[field], 'artifact_revoked')
    dependencies = []
    for name in ('finality_approval_id', 'delivery_approval_id'):
        if name in payload['evidence']:
            dependencies.append(payload['evidence'][name])
    dependencies.extend(payload['evidence'].get('certification_approval_ids', []))
    _require(not set(dependencies).intersection(registry['revoked_approvals']), 'artifact_dependency_revoked')


def validate_artifact(artifact_json, *, enrollment_json, enrollment_sha256, enrollment_id,
                      enrollment_generation, expected_binding_json, trusted_now_utc,
                      registry_json, verifier=None):
    """Check synthetic signature, supplied independent bindings, enrollment and status.

    No default clock/registry/trust, network, SQL, artifact file loading or authority
    conversion. Expected bindings and registry are test-harness inputs, not proof
    of independently authenticated production evidence.
    """
    trust = _context(verifier)
    now = _time(trusted_now_utc)
    _require(verifier._last_time is None or now >= verifier._last_time, 'trusted_clock_rollback')
    verifier._last_time = now
    envelope = _load(artifact_json)
    _object(envelope, ENVELOPE)
    _require(envelope['format'] == FORMAT and envelope['algorithm'] == ALGORITHM,
             'artifact_format_or_algorithm_invalid')
    _text(envelope['key_id'])
    payload = envelope['payload']
    _object(payload, PAYLOAD)
    for field in PAYLOAD - {'target', 'enrollment_generation', 'minimum_revocation_sequence',
                            'usage', 'evidence', 'rule_sha256', 'population_sha256',
                            'manifest_sha256', 'snapshot_sha256'}:
        _text(payload[field])
    _integer(payload['enrollment_generation'], 1)
    _integer(payload['minimum_revocation_sequence'])
    _hash(payload['enrollment_sha256'])
    _object(payload['target'], TARGET)
    for field in ('hostname', 'database'):
        _text(payload['target'][field])
    for field in ('device', 'inode'):
        _integer(payload['target'][field])
    _binding(payload)
    key = next((key for key in trust['keys'] if key['key_id'] == envelope['key_id']), None)
    _require(key is not None, 'artifact_untrusted_key')
    _require(payload['issuer_id'] == key['issuer_id'], 'artifact_issuer_mismatch')
    grant = next((grant for grant in key['grants'] if all(
        grant[k] == payload[k] for k in ('approver_id', 'family', 'permission', 'action'))), None)
    _require(grant is not None, 'artifact_approver_or_action_not_authorized')
    # Lazy import: the existing app and writers do not acquire a crypto dependency.
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(_base64(key['public_key'], 32)).verify(
            _base64(envelope['signature'], 64), canonical_payload_bytes(canonical(payload)))
    except InvalidSignature:
        raise AuthorizationError('artifact_signature_invalid') from None
    issued = _time(payload['issued_at_utc'])
    start, expiry = _time(payload['not_before_utc']), _time(payload['expires_at_utc'])
    _require(issued <= start < expiry and issued <= now and start <= now < expiry,
             'artifact_lifetime_invalid')
    _require((expiry - issued).total_seconds() <= grant['max_lifetime_seconds'], 'artifact_lifetime_excessive')
    if payload['action'] == 'enqueue':
        _require(_time(payload['usage']['starts_at_utc']) <= now < _time(payload['usage']['ends_at_utc']),
                 'artifact_capture_window_inactive')
    expected = _load(expected_binding_json)
    _object(expected, BINDINGS)
    _require(canonical({k: payload[k] for k in BINDINGS}) == canonical(expected),
             'artifact_binding_mismatch')
    validated = validate_enrollment(enrollment_json, expected_sha256=enrollment_sha256,
        enrollment_id=enrollment_id, enrollment_generation=enrollment_generation,
        trusted_now_utc=trusted_now_utc, verifier=verifier)
    enrollment = _load(validated.canonical_json)
    for field in ('enrollment_id', 'enrollment_generation', 'environment', 'deployment_id'):
        _require(payload[field] == enrollment[field], 'artifact_enrollment_mismatch')
    _require(payload['enrollment_sha256'] == validated.sha256, 'artifact_enrollment_hash_mismatch')
    _require(payload['target'] == dict(hostname=enrollment['hostname'],
        database=enrollment['database_absolute_path'], device=enrollment['device'], inode=enrollment['inode']),
        'artifact_target_mismatch')
    _registry(registry_json, payload, envelope['key_id'], trust, verifier, now)
    return ValidatedArtifact(canonical(envelope), digest(envelope))
