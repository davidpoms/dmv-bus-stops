"""Unwired closed-population finality policy. No production approval or clock.

Policy, population inspection and independent authorization are separate inputs.
The trusted authorization verifier must come from a separately reviewed operator
control plane; no permissive verifier, file loader, gate or scheduler ships here.
"""

from dataclasses import asdict
import json
import re

from . import permanent
from .geography import _utc
from .live_first_looks import Configuration, _sealed_baseline
from .rules import canonical, digest


HISTORICAL_CUTOFF = "2026-09-30T00:00:00Z"
HISTORICAL_COUNT = 55
CANDIDATE_ARTIFACT_SHA256 = "c6c2c5d9aa51c24c129bbe1e9f0e24fed735c1e9debdb8afbb8940f27ce94a50"
FINALITY = {"mode": "reviewed-closed-population-v1",
            "late_arrivals": "quarantine-and-review", "existing_claims": "verify-never-reassign"}
POLICY_FIELDS = {"format", "reference", "activation_at_utc", "historical_cutoff_utc",
                 "historical_qualified_count", "candidate_artifact_sha256", "historical_operation_id",
                 "historical_qualified_sha256", "sqlite_utc_provenance", "gap_assignment_ids",
                 "gap_review_reference", "finality"}
AUTH_FIELDS = {"format", "reference", "policy_sha256", "population_sha256", "baseline_link_review_reference"}


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _policy(policy):
    permanent.require(isinstance(policy, dict) and set(policy) == POLICY_FIELDS, "incomplete_launch_policy")
    permanent.require(policy["format"] == "first-look-launch-policy-v1", "invalid_launch_policy")
    permanent.require(policy["finality"] == FINALITY, "reviewed_finality_policy_required")
    permanent.require(permanent.text(policy["reference"]) and permanent.text(policy["gap_review_reference"]), "launch_review_references_required")
    permanent.require(policy["historical_cutoff_utc"] == HISTORICAL_CUTOFF and
                      type(policy["historical_qualified_count"]) is int and policy["historical_qualified_count"] == HISTORICAL_COUNT and
                      policy["candidate_artifact_sha256"] == CANDIDATE_ARTIFACT_SHA256, "historical_launch_context_mismatch")
    permanent.require(_hash(policy["historical_operation_id"]) and _hash(policy["historical_qualified_sha256"]), "sealed_baseline_identity_required")
    permanent.require(_utc(policy["activation_at_utc"]) >= HISTORICAL_CUTOFF, "invalid_activation_boundary")
    permanent.require(policy["sqlite_utc_provenance"] is None or permanent.text(policy["sqlite_utc_provenance"]), "invalid_timestamp_provenance")
    gap = policy["gap_assignment_ids"]
    permanent.require(isinstance(gap, list) and all(type(n) is int and n > 0 for n in gap) and gap == sorted(set(gap)), "invalid_gap_population")


def configuration_for(policy):
    """Validate/copy admission parameters, not authorization to capture or issue."""
    policy = json.loads(canonical(policy))
    _policy(policy)
    return Configuration(activation_at_utc=policy["activation_at_utc"], historical_cutoff_utc=HISTORICAL_CUTOFF,
                         policy_reference=policy["reference"], policy_sha256=digest(policy),
                         sqlite_utc_provenance=policy["sqlite_utc_provenance"])


def build_guard(policy=None, reviewed_population=None, authorization=None, *, authorization_verifier=None):
    """Return None when unconfigured, otherwise a reviewed, read-only callback.

    reviewed_population is an independently inspected permanent.prepare() result,
    NOT an instruction to historical-finalize it. Its exact canonical digest is
    approved separately. authorization_verifier(authorization, policy_hash,
    population_hash) must return True; references/hashes alone are not approval.
    Returned guard.configuration can be used for future authorized admission.
    Creating this guard never enables a RecognitionGate or accesses a database.
    """
    if any(value is None for value in (policy, reviewed_population, authorization, authorization_verifier)):
        return None
    policy_json, population_json, auth_json = map(canonical, (policy, reviewed_population, authorization))
    policy, population, auth = map(json.loads, (policy_json, population_json, auth_json))
    _policy(policy)
    permanent.require(population.get("format") == "private-recognition-operation-v1" and population.get("family") == "first_look", "closed_population_inspection_required")
    permanent._validate_manifest(population)
    permanent.require(set(auth) == AUTH_FIELDS and auth["format"] == "first-look-launch-authorization-v1" and
                      permanent.text(auth["reference"]) and permanent.text(auth["baseline_link_review_reference"]), "independent_authorization_required")
    policy_hash, population_hash = digest(policy), digest(population)
    permanent.require(auth["policy_sha256"] == policy_hash and auth["population_sha256"] == population_hash, "authorization_hash_mismatch")
    permanent.require(callable(authorization_verifier), "independent_verifier_required")

    def authorized():
        permanent.require(authorization_verifier(json.loads(auth_json), policy_hash, population_hash) is True,
                          "launch_not_independently_authorized")

    authorized()
    configuration = configuration_for(policy)
    config = asdict(configuration)
    inputs = population["inputs"]
    frontier = _utc(inputs["cutoff_utc"])
    evaluation = _utc(population["evaluation_at_utc"])
    permanent.require(policy["activation_at_utc"] < frontier <= evaluation and
                      inputs.get("sqlite_utc_provenance") == policy["sqlite_utc_provenance"], "invalid_finality_boundary")

    def guard(conn, context):
        authorized()  # independent authorization may be withdrawn between calls
        permanent.require(context["configuration"] == config, "launch_configuration_mismatch")
        completion = context["completion"]
        permanent.require(completion["completed_at_utc"] >= config["activation_at_utc"], "completion_before_activation")
        # New completions at/after this exclusive frontier wait for a separately
        # reviewed population; never infer finality from elapsed wall-clock time.
        if completion["completed_at_utc"] >= frontier:
            return None
        baseline = _sealed_baseline(conn, policy["historical_operation_id"], config)
        facts = baseline["report"]["qualified"]
        permanent.require(len(facts) == HISTORICAL_COUNT and digest(facts) == policy["historical_qualified_sha256"] and
                          all(f["completed_at_utc"] < HISTORICAL_CUTOFF for f in facts), "historical_population_mismatch")
        fresh = permanent._prepare(conn, "first_look", inputs, evaluation, population["authorization_reference"])
        permanent.require(fresh == json.loads(population_json), "closed_population_changed")
        # A reviewed gap inventory is not permission to award that inventory.
        # Existing live claim checks still reject an unclaimed preactivation winner.
        gap = sorted(f["assignment_id"] for f in fresh["report"]["qualified"]
                     if HISTORICAL_CUTOFF <= f["completed_at_utc"] < policy["activation_at_utc"])
        permanent.require(gap == policy["gap_assignment_ids"], "preactivation_population_unreconciled")
        permanent.require(any(f == completion for f in fresh["report"]["qualified"]), "completion_not_in_closed_population")
        return {"historical_operation_id": policy["historical_operation_id"], "evaluation_at_utc": evaluation,
                "inputs": json.loads(canonical(inputs)), "reference": auth["reference"]}

    guard.configuration = configuration
    return guard
