"""Transparent evidence-gap cohorts for volunteer review routing."""

COHORT_ORDER = (
    "presence_conflict",
    "near_consensus",
    "longitudinal_follow_up",
    "adequacy_unknown",
    "clearance_unknown",
    "presence_unknown",
    "documented_need",
)

# A deterministic hybrid rotation. Repeated entries are quotas, not scores.
COHORT_ROTATION = (
    "presence_conflict",
    "presence_unknown",
    "adequacy_unknown",
    "clearance_unknown",
    "presence_unknown",
    "near_consensus",
    "adequacy_unknown",
    "clearance_unknown",
    "presence_unknown",
    "longitudinal_follow_up",
    "presence_conflict",
    "documented_need",
)

COHORT_CAMPAIGN = {
    "presence_conflict": "presence_verification",
    "presence_unknown": "presence_verification",
    "adequacy_unknown": "seating_adequacy",
    "clearance_unknown": "bench_clearance",
    "near_consensus": "presence_verification",
    "longitudinal_follow_up": "presence_verification",
    "documented_need": "planning_review",
}


def classification_sql(seating="sio", bench="bs", shelter="ss", observations="obs"):
    """Return the canonical SQL CASE equivalent of :func:`primary_cohort`."""
    return f"""CASE
        WHEN {bench}.derived_status='conflicting'
          OR {shelter}.derived_status='conflicting' THEN 'presence_conflict'
        WHEN (({bench}.community_observation_count BETWEEN 1 AND 2
               AND NOT ({bench}.community_yes_count>0 AND {bench}.community_no_count>0))
           OR ({shelter}.community_observation_count BETWEEN 1 AND 2
               AND NOT ({shelter}.community_yes_count>0 AND {shelter}.community_no_count>0)))
          THEN 'near_consensus'
        WHEN COALESCE({observations}.prior_observations,0)>0 THEN 'longitudinal_follow_up'
        WHEN {seating}.bench_status IN ('likely_yes','confirmed_yes')
          AND {seating}.adequacy_status='unknown' THEN 'adequacy_unknown'
        WHEN {seating}.bench_status IN ('likely_no','confirmed_no')
          AND {seating}.clearance_status='unknown' THEN 'clearance_unknown'
        WHEN {seating}.bench_status='unknown' THEN 'presence_unknown'
        WHEN {seating}.adequacy_status='limitation_observed'
          OR {seating}.workflow_state IN ('planning_review','constrained_or_special_review')
          THEN 'documented_need'
    END"""

COHORT_REASON = {
    "presence_conflict": (
        "Our sources disagree about whether seating or shelter is present. "
        "A current observation can help clarify that uncertainty."
    ),
    "presence_unknown": (
        "We do not yet have reliable information about seating at this stop. "
        "A current observation would help."
    ),
    "adequacy_unknown": (
        "A bench appears to be present, but we do not yet know whether the "
        "seating is comfortable or adequate."
    ),
    "clearance_unknown": (
        "Our records suggest this stop may not have a bench. A preliminary "
        "look at the available waiting space would be useful."
    ),
    "near_consensus": (
        "Other reviewers have already contributed observations here. Another "
        "current review could strengthen the community record."
    ),
    "longitudinal_follow_up": (
        "This stop has been reviewed before. A new dated observation can help "
        "show whether conditions have changed."
    ),
    "documented_need": (
        "Previous observations identify a seating or comfort concern. A current "
        "review can add useful detail for future planning."
    ),
}


def classify_cohorts(item):
    """Return every applicable evidence cohort without ranking them."""
    cohorts = set(item.get("evidence_gap_cohorts", ()))
    if not cohorts:
        bench = item.get("bench_status")
        shelter = item.get("shelter_status")
        if bench == "conflicting" or shelter == "conflicting":
            cohorts.add("presence_conflict")
        if item.get("near_consensus"):
            cohorts.add("near_consensus")
        if item.get("prior_observation_count", 0):
            cohorts.add("longitudinal_follow_up")
        if bench in ("likely_yes", "confirmed_yes") and item.get("adequacy_status") == "unknown":
            cohorts.add("adequacy_unknown")
        if bench in ("likely_no", "confirmed_no") and item.get("clearance_status") == "unknown":
            cohorts.add("clearance_unknown")
        if bench == "unknown":
            cohorts.add("presence_unknown")
        if item.get("adequacy_status") == "limitation_observed" or item.get("workflow_state") in (
            "planning_review", "constrained_or_special_review"
        ):
            cohorts.add("documented_need")
    return tuple(name for name in COHORT_ORDER if name in cohorts)


def primary_cohort(item):
    """Apply deterministic precedence to overlapping evidence cohorts."""
    return next(iter(classify_cohorts(item)), None)


def campaign_for_cohort(cohort, item=None, fallback=None):
    """Map a cohort to the most relevant existing survey focus."""
    item = item or {}
    if cohort in ("near_consensus", "longitudinal_follow_up", "documented_need"):
        if item.get("bench_status") in ("unknown", "conflicting") or item.get("shelter_status") == "conflicting":
            return "presence_verification"
        if item.get("adequacy_status") in ("unknown", "limitation_observed") and item.get("bench_status") in ("likely_yes", "confirmed_yes"):
            return "seating_adequacy"
        if item.get("clearance_status") == "unknown" and item.get("bench_status") in ("likely_no", "confirmed_no"):
            return "bench_clearance"
    return COHORT_CAMPAIGN.get(cohort, fallback)
