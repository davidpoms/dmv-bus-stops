"""Production-format verification contracts, disconnected from writer authority.

Only an explicitly synthetic public-key provider exists. No signing, enrollment,
production trust loader, database access, authentication or execution is provided.
"""

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from uuid import UUID

from .operations import CONTRACT, ENROLLED_CONTRACT
from .rules import canonical, digest


AUTHORIZATION_FORMAT = "recognition-authorization-v1"
AUTHORIZATION_DOMAIN = b"DMV-recognition-authorization-v1\x00"
ALGORITHM = "Ed25519"
OPERATION_FIELDS = frozenset("""format synthetic_contract_only operation_id event_id event_sha256
    preparation_id preparation_sha256 parent_event_id dependencies_sha256 family action
    writer_manifest_sha256 target_observation enrollment rule rule_sha256 population_sha256
    member_ids accounting_policy created_at_utc frozen_at_utc provenance""".split())
PAYLOAD_FIELDS = frozenset("""artifact_id authority_id key_id registry_id operation
    issued_at_utc expires_at_utc""".split())
DIRECT_BINDINGS = """operation_id event_id preparation_id family action dependencies_sha256
    writer_manifest_sha256 enrollment rule_sha256 population_sha256 target_observation""".split()


class TrustError(ValueError):
    """Rejected verification data; never a writer capability."""


def require(value, code):
    if not value:
        raise TrustError(code)


def fields(value, names):
    require(type(value) is dict and set(value) == set(names), "invalid_fields")


def text(value):
    require(type(value) is str and bool(value.strip()), "invalid_text")


def integer(value, minimum=0):
    require(type(value) is int and minimum <= value <= 2**63 - 1, "invalid_integer")


def sha(value):
    require(type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None, "invalid_digest")


def identity(value):
    text(value)
    try:
        require(str(UUID(value)) == value, "invalid_artifact_identity")
    except ValueError:
        raise TrustError("invalid_artifact_identity") from None


def utc(value):
    require(type(value) is str, "invalid_time")
    try:
        result = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise TrustError("invalid_time") from None
    require(result.strftime("%Y-%m-%dT%H:%M:%SZ") == value, "noncanonical_time")
    return result


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def _number(value):
    raise TrustError("unsupported_json_number")


def load(serialized):
    require(type(serialized) is str and len(serialized) <= 1_000_000, "serialized_json_required")
    try:
        return json.loads(serialized, object_pairs_hook=_pairs, parse_float=_number, parse_constant=_number)
    except TrustError:
        raise
    except (ValueError, RecursionError):
        raise TrustError("invalid_json") from None


def decoded(value, length):
    text(value)
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise TrustError("invalid_base64") from None
    require(len(raw) == length and base64.b64encode(raw).decode("ascii") == value, "invalid_base64")
    return raw


def verify_signature(public_key, signature, message):
    # Optional test dependency, loaded only on explicit cryptographic verification.
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(decoded(public_key, 32)).verify(decoded(signature, 64), message)
    except InvalidSignature:
        raise TrustError("invalid_signature") from None


@dataclass(frozen=True)
class VerificationFacts:
    """Immutable checked data, NOT Authority, Authorization, or execution admission."""

    canonical_json: str
    sha256: str


@dataclass(frozen=True, init=False)
class SyntheticTrustProvider:
    """Explicit test public keys/grants only; no production mode or callback loader.

    Historical keys remain in authority_keys. Status signers are configured
    separately, and public-key reuse across identities/purposes is rejected.
    """

    configuration_json: str
    max_status_age_seconds: int
    minimum_sequence: int

    def __init__(self, configuration_json, *, max_status_age_seconds=48*60*60, minimum_sequence=0):
        config = load(configuration_json)
        fields(config, {"registry_id", "authority_keys", "status_keys"})
        text(config["registry_id"])
        integer(max_status_age_seconds, 1)
        integer(minimum_sequence)
        public_keys, key_ids = set(), set()
        for kind in ("authority_keys", "status_keys"):
            require(type(config[kind]) is list and bool(config[kind]), "public_keys_required")
            for entry in config[kind]:
                fields(entry, {"key_id", "public_key", "authority_id", "grants"} if kind == "authority_keys"
                       else {"key_id", "public_key"})
                text(entry["key_id"])
                raw = decoded(entry["public_key"], 32)
                require(raw not in public_keys and entry["key_id"] not in key_ids, "duplicate_trust_key")
                public_keys.add(raw)
                key_ids.add(entry["key_id"])
                if kind == "authority_keys":
                    text(entry["authority_id"])
                    require(type(entry["grants"]) is list and bool(entry["grants"]), "grants_required")
                    grants = set()
                    for grant in entry["grants"]:
                        fields(grant, {"family", "action"})
                        require(grant["family"] in ("first_look", "geography_steward")
                                and grant["action"] == "finalize", "unsupported_grant")
                        pair = (grant["family"], grant["action"])
                        require(pair not in grants, "duplicate_grant")
                        grants.add(pair)
        # One key per authority identity: rotation creates both a new identity and key.
        identities = [k["authority_id"] for k in config["authority_keys"]]
        require(len(identities) == len(set(identities)), "rotation_requires_new_authority_identity")
        object.__setattr__(self, "configuration_json", canonical(config))
        object.__setattr__(self, "max_status_age_seconds", max_status_age_seconds)
        object.__setattr__(self, "minimum_sequence", minimum_sequence)


def configuration(provider):
    require(type(provider) is SyntheticTrustProvider, "production_trust_configuration_unavailable")
    return load(provider.configuration_json)


def operation_binding(operation_json):
    """Bind the existing Slice 3 envelope, not an alternative execution operation."""
    operation = load(operation_json)
    fields(operation, OPERATION_FIELDS)
    require(operation["format"] in (CONTRACT, ENROLLED_CONTRACT) and operation["synthetic_contract_only"] is True,
            "unsupported_operation_contract")
    for key in ("operation_id", "event_id", "preparation_id"):
        text(operation[key])
        try:
            require(str(UUID(operation[key])) == operation[key], "invalid_operation_identity")
        except ValueError:
            raise TrustError("invalid_operation_identity") from None
    for key in ("event_sha256", "preparation_sha256", "dependencies_sha256", "writer_manifest_sha256",
                "rule_sha256", "population_sha256"):
        sha(operation[key])
    require(operation["family"] in ("first_look", "geography_steward") and operation["action"] == "finalize",
            "unsupported_operation_action")
    if operation["format"] == CONTRACT:
        require(operation["enrollment"] == {"enrollment_id": None, "generation": None},
                "enrollment_contract_not_implemented")
    else:
        from .enrollment import validate_reference
        validate_reference(operation["enrollment"])
    require(digest(operation["rule"]) == operation["rule_sha256"], "operation_rule_mismatch")
    result = {key: operation[key] for key in DIRECT_BINDINGS}
    result.update(envelope_sha256=digest(operation), accounting_policy_sha256=digest(operation["accounting_policy"]))
    return result


def authorization_payload(operation_json, *, artifact_id, authority_id, key_id, registry_id,
                          issued_at_utc, expires_at_utc):
    """Construct unsigned canonical data only; no signing capability is present."""
    payload = dict(artifact_id=artifact_id, authority_id=authority_id, key_id=key_id, registry_id=registry_id,
                   operation=operation_binding(operation_json), issued_at_utc=issued_at_utc,
                   expires_at_utc=expires_at_utc)
    _payload(payload)
    return canonical(payload)


def _payload(payload):
    fields(payload, PAYLOAD_FIELDS)
    for key in ("artifact_id", "authority_id", "key_id", "registry_id"):
        text(payload[key])
    identity(payload["artifact_id"])
    require(utc(payload["issued_at_utc"]) < utc(payload["expires_at_utc"]), "invalid_authorization_interval")
    fields(payload["operation"], {*DIRECT_BINDINGS, "envelope_sha256", "accounting_policy_sha256"})


def authorization_signing_bytes(payload_json):
    payload = load(payload_json)
    _payload(payload)
    return AUTHORIZATION_DOMAIN + canonical(payload).encode("utf-8")


def signed_envelope(serialized, expected_format):
    value = load(serialized)
    fields(value, {"format", "algorithm", "payload", "signature"})
    require(value["format"] == expected_format, "unsupported_artifact_version")
    require(value["algorithm"] == ALGORITHM, "unsupported_signature_algorithm")
    return value


def verify_historical_authorization(artifact_json, *, operation_json, provider=None):
    """Signature, exact binding, static grant and well-formed interval; no current permission.

    Expiry/revocation do not erase this historical cryptographic fact. No current
    clock or current-status checkpoint is read or updated by this API.
    """
    config = configuration(provider)
    value = signed_envelope(artifact_json, AUTHORIZATION_FORMAT)
    p = value["payload"]
    _payload(p)
    require(p["registry_id"] == config["registry_id"], "unknown_registry")
    key = next((k for k in config["authority_keys"] if k["authority_id"] == p["authority_id"]
                and k["key_id"] == p["key_id"]), None)
    require(key is not None, "unknown_authority_key")
    verify_signature(key["public_key"], value["signature"], authorization_signing_bytes(canonical(p)))
    require(canonical(p["operation"]) == canonical(operation_binding(operation_json)), "operation_binding_mismatch")
    require({"family": p["operation"]["family"], "action": p["operation"]["action"]} in key["grants"],
            "authority_grant_mismatch")
    return VerificationFacts(canonical(value), digest(value))


def verify_authorization_time(artifact_json, *, trusted_now_utc):
    """Time validity only: does not check a signature or establish trust."""
    value = signed_envelope(artifact_json, AUTHORIZATION_FORMAT)
    _payload(value["payload"])
    p = value["payload"]
    require(utc(p["issued_at_utc"]) <= utc(trusted_now_utc) < utc(p["expires_at_utc"]),
            "authorization_not_current")


def verify_current_authorization(artifact_json, *, operation_json, snapshot_json,
                                 checkpoint_conn, trusted_now_utc, provider=None):
    """Combine independent verification facts; never authorize a writer or execute.

    This is a test-only verification result, not execution admission. It cannot
    consume an authorization or close any authorization-to-commit race.
    """
    from .status import verify_current_status
    artifact = verify_historical_authorization(artifact_json, operation_json=operation_json, provider=provider)
    verify_authorization_time(artifact_json, trusted_now_utc=trusted_now_utc)
    current = verify_current_status(snapshot_json, provider=provider, checkpoint_conn=checkpoint_conn,
                                    trusted_now_utc=trusted_now_utc)
    p = load(artifact.canonical_json)["payload"]
    s = load(current.canonical_json)["payload"]
    row = next(k for k in s["authorities"] if k["authority_id"] == p["authority_id"])
    require(row["state"] == "ENABLED" and row["key_state"] == "ENABLED", "authority_revoked")
    facts = dict(artifact_sha256=artifact.sha256, operation_id=p["operation"]["operation_id"],
                 status_sha256=current.sha256, status_sequence=s["sequence"],
                 checked_at_utc=trusted_now_utc, synthetic_verification_only=True)
    return VerificationFacts(canonical(facts), digest(facts))
