"""Service-level sealing checks; SQL alone does not seal a witness collection."""

import json

from .qualification import Quarantined
from .rules import digest, load_rule


WITNESS_FIELDS = ("assignment_id", "observation_id", "physical_stop_id", "completed_at_utc")


def stable_evidence(award, evidence):
    """Version-neutral earning facts; never labels or rule metadata."""
    return {"earned_at_utc": award["earned_at_utc"], "numerator": award["numerator"],
            "threshold": evidence["threshold"], "witnesses": evidence["witnesses"]}


def validate_evidence(award, evidence, definition):
    """Validate bounded shape, ordering and calculation before consulting rows."""
    try:
        threshold = evidence["threshold"]
        witnesses = evidence["witnesses"]
        if (type(threshold) is not int or threshold not in definition["thresholds"]
                or not 1 <= threshold <= 1000 or not isinstance(witnesses, list)
                or len(witnesses) != threshold or award["numerator"] != threshold
                or award["tier_key"] != str(threshold) or award["family"] != "explorer"
                or award["scope_key"] != "global" or evidence["rule_sha256"] != digest(definition)
                or evidence["algorithm"] != definition["algorithm"]):
            raise ValueError()
        if any(set(w) != set(WITNESS_FIELDS) for w in witnesses):
            raise ValueError()
        if (len({w["assignment_id"] for w in witnesses}) != threshold
                or len({w["physical_stop_id"] for w in witnesses}) != threshold
                or witnesses != sorted(witnesses, key=lambda w: (w["completed_at_utc"], w["assignment_id"]))
                or award["earned_at_utc"] != witnesses[-1]["completed_at_utc"]):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise Quarantined("invalid_award_evidence") from None


def check_award_integrity(conn, award_id):
    """Raise on missing/extra/mismatched witnesses or invalid evidence/hash/order.

    Bounded by the declared rule threshold plus one, not reviewer history. This
    checks the historical sealed evidence, never re-earns against current data.
    """
    award = conn.execute("SELECT * FROM recognition_awards WHERE award_id=?", (award_id,)).fetchone()
    if award is None:
        raise Quarantined("missing_award")
    try:
        evidence = json.loads(award["evidence_json"])
    except (ValueError, TypeError):
        raise Quarantined("invalid_award_evidence") from None
    definition = load_rule(conn, award["rule_key"])
    validate_evidence(award, evidence, definition)
    if digest(evidence) != award["evidence_sha256"]:
        raise Quarantined("award_evidence_hash_mismatch")
    rows = conn.execute("""SELECT w.assignment_id,c.observation_id,c.physical_stop_id,
        c.completed_at_utc,c.reviewer_id FROM recognition_award_witnesses w
        LEFT JOIN recognition_completions c USING(assignment_id)
        WHERE w.award_id=? ORDER BY w.assignment_id LIMIT ?""",
        (award_id, evidence["threshold"] + 1)).fetchall()
    if len(rows) != evidence["threshold"]:
        raise Quarantined("award_witness_count_mismatch")
    if any(r["reviewer_id"] != award["reviewer_id"] for r in rows):
        raise Quarantined("award_witness_identity_mismatch")
    actual = sorted([{k: row[k] for k in WITNESS_FIELDS} for row in rows],
                    key=lambda w: (w["completed_at_utc"], w["assignment_id"]))
    if actual != evidence["witnesses"]:
        raise Quarantined("award_witness_evidence_mismatch")
    return stable_evidence(award, evidence)
