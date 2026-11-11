"""Closed R22 issuer/action evidence codecs. Parsed DATA is never authority.

No installer, credential reader, writer, registration or transaction is exposed.
"""

from . import runtime_operation_contract as operation
from . import runtime_activation_authority_schema as source
from . import runtime_profile_schema as profile
from .rules import canonical, digest
from .trust import fields, identity, load, require, utc


ISSUER = 'recognition-runtime-finalization-issuer-v1'
ACTION = 'recognition-runtime-finalization-action-v1'
EFFECT = 'atomic_historical_family_effect_and_outcome_witness'
POLICY = 'recognition-g1-source-policy-v1'
ISSUER_ROLE = 'original-source-exact-family-witness'
ISSUER_FIELDS = ('format', 'mandate', 'governance_binding_sha256', 'adoption_sha256',
                 'appointment_sha256', 'approval_sha256', 'issuer_role', 'holder',
                 'intent', 'policy', 'issued_at_utc', 'expires_at_utc')
INTENT_FIELDS = ('operation_id', 'operation_sha256', 'writer_manifest_sha256',
                 'write_set_sha256', 'family', 'runtime_target', 'action')
HOLDER_FIELDS = ('actor_id', 'primary_sha256', 'session_sha256')
ACTION_FIELDS = ('format', 'issuer_sha256', 'authority_id', 'authority_sha256',
                 'holder', 'intent', 'policy', 'issued_at_utc', 'expires_at_utc')
MANDATE = 'dmv-bus-stops-g1-governance-mandate-4e-20-G13-v1'


def _holder(value):
    fields(value, HOLDER_FIELDS)
    operation._positive(value['actor_id'])
    for key in ('primary_sha256', 'session_sha256'):
        profile._check_sha(value[key])


def _intent(value):
    fields(value, INTENT_FIELDS)
    identity(value['operation_id'])
    for key in ('operation_sha256', 'writer_manifest_sha256', 'write_set_sha256'):
        profile._check_sha(value[key])
    require(value['family'] in ('first_look', 'geography_steward') and value['action'] == EFFECT,
            'finalization_action_scope')
    operation._shape(value['runtime_target'])  # Shape only; no live-scope claim.


def _policy(value):
    fields(value, ('format', 'policy_id', 'version', 'action', 'max_grants', 'lifetime_policy'))
    from .runtime_authority_lifetime_policy import seconds
    seconds(value['lifetime_policy'])  # Closed immutable IDs; never a duration input.
    require(value == dict(format=POLICY, policy_id=ISSUER_ROLE, version=1, action=EFFECT,
                          max_grants=1, lifetime_policy=value['lifetime_policy'])
            and type(value['version']) is int and type(value['max_grants']) is int,
            'finalization_policy')


def validate_issuer(value):
    operation._json(value); fields(value, ISSUER_FIELDS)
    require(value['format'] == ISSUER and value['mandate'] == MANDATE
            and value['issuer_role'] == ISSUER_ROLE, 'finalization_issuer_scope')
    for key in ('governance_binding_sha256', 'adoption_sha256', 'appointment_sha256', 'approval_sha256'):
        profile._check_sha(value[key])
    _holder(value['holder']); _intent(value['intent']); _policy(value['policy'])
    require(value['holder']['actor_id'] == value['intent']['runtime_target']['owner_id'],
            'finalization_holder_scope')
    require(utc(value['issued_at_utc']) < utc(value['expires_at_utc']), 'finalization_interval')
    # The owner must independently clip to actual original credential/consent/
    # appointment bounds. This codec cannot authenticate those referenced facts.
    return operation._copy(value)


def validate_action(value, *, issuer, authority):
    operation._json(value); fields(value, ACTION_FIELDS)
    issuer = validate_issuer(issuer)
    authority = source.validate_authority(authority)
    require(value['format'] == ACTION and value['issuer_sha256'] == digest(issuer),
            'finalization_issuer_mismatch')
    identity(value['authority_id']); profile._check_sha(value['authority_sha256'])
    require(value['authority_id'] == authority['authority_id']
            and value['authority_sha256'] == digest(authority), 'finalization_decision_mismatch')
    _holder(value['holder']); _intent(value['intent']); _policy(value['policy'])
    require(value['holder'] == issuer['holder'] == authority['authentication']
            and value['intent'] == issuer['intent'] and value['policy'] == issuer['policy'],
            'finalization_subject_mismatch')
    reference = authority['operation_reference']; intent = value['intent']
    require(all(intent[key] == reference[key] for key in
                ('operation_id', 'operation_sha256', 'writer_manifest_sha256'))
            and intent['family'] == reference['writer_family']
            and intent['runtime_target'] == authority['runtime_target'], 'finalization_target_mismatch')
    require(authority['lifetime_policy'] == value['policy']['lifetime_policy'], 'finalization_policy')
    require(utc(issuer['issued_at_utc']) <= utc(authority['issued_at_utc'])
            <= utc(value['issued_at_utc']) < utc(value['expires_at_utc'])
            <= min(utc(authority['expires_at_utc']), utc(issuer['expires_at_utc'])),
            'finalization_interval')
    return operation._copy(value)


def parse_issuer(serialized, *, expected_sha256):
    profile._check_sha(expected_sha256)
    value = validate_issuer(load(serialized))
    require(serialized == canonical(value) and expected_sha256 == digest(value),
            'finalization_noncanonical')
    return value


def parse_action(serialized, *, expected_sha256, issuer, authority):
    profile._check_sha(expected_sha256)
    value = validate_action(load(serialized), issuer=issuer, authority=authority)
    require(serialized == canonical(value) and expected_sha256 == digest(value),
            'finalization_noncanonical')
    return value
