"""Explicit, immutable Explorer definitions and pure candidate calculation."""

import hashlib
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


RULE_KEY = "explorer:v1"


def initial_definition():
    return {
        "algorithm": "earliest-distinct-physical-stop-v1",
        "qualification": "completed-single-matching-community-observation-v1",
        "timestamp_policy": "whole-second-offset-or-attested-sqlite-utc-v1",
        "thresholds": [5, 20, 50, 100],
        "scope": "global",
        "ordering": ["completed_at_utc", "assignment_id"],
    }


def load_rule(conn, rule_key):
    row = conn.execute(
        "SELECT family,definition_json,definition_sha256 FROM recognition_rule_versions "
        "WHERE rule_key=?", (rule_key,),
    ).fetchone()
    if row is None or row[0] != "explorer":
        raise ValueError("unknown_explorer_rule")
    definition = json.loads(row[1])
    if digest(definition) != row[2]:
        raise ValueError("rule_hash_mismatch")
    validate_definition(definition)
    return definition


def validate_definition(definition):
    supported = initial_definition()
    if any(definition.get(key) != value for key, value in supported.items() if key != "thresholds"):
        raise ValueError("unsupported_rule_algorithm")
    thresholds = definition.get("thresholds")
    if (not isinstance(thresholds, list) or not thresholds
            or any(type(n) is not int or n <= 0 for n in thresholds)
            or sorted(set(thresholds)) != thresholds):
        raise ValueError("invalid_thresholds")


def explorer_candidates(completions, rule_key, definition):
    """Input is immutable completion facts, never current progress projections."""
    validate_definition(definition)
    owners = {}
    for fact in sorted(completions, key=lambda c: (c["completed_at_utc"], c["assignment_id"])):
        owners.setdefault(fact["reviewer_id"], {}).setdefault(fact["physical_stop_id"], fact)
    result = []
    for reviewer, stops in sorted(owners.items()):
        ordered = list(stops.values())
        for threshold in definition["thresholds"]:
            if len(ordered) < threshold:
                continue
            witnesses = ordered[:threshold]
            evidence = {
                "algorithm": definition["algorithm"], "threshold": threshold,
                "rule_sha256": digest(definition),
                "witnesses": [{key: c[key] for key in (
                    "assignment_id", "observation_id", "physical_stop_id", "completed_at_utc"
                )} for c in witnesses],
            }
            result.append({
                "reviewer_id": reviewer, "family": "explorer", "scope_key": "global",
                "tier_key": str(threshold), "rule_key": rule_key,
                "earned_at_utc": witnesses[-1]["completed_at_utc"],
                "numerator": threshold, "evidence": evidence,
            })
    return result
