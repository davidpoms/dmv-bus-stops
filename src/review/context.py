"""Plain-language review context derived from existing routing and evidence."""


WORKFLOW_CAMPAIGN = {
    "verify_presence": "presence_verification",
    "assess_adequacy": "seating_adequacy",
    "collect_clearance_observation": "bench_clearance",
    "planning_review": "planning_review",
    "constrained_or_special_review": "constrained_review",
}

CAMPAIGN_FIELDS = {
    "presence_verification": (
        "shelter_present", "seating_type", "streetview_imagery_month",
    ),
    "seating_adequacy": (
        "seating_type", "seating_limitations", "waiting_environment_rating",
        "riders_avoid_facilities", "weather_exposure", "accessibility_status",
    ),
    "bench_clearance": (
        "bench_feasible", "concrete_pad_needed", "seating_type",
        "seating_limitations",
    ),
    "planning_review": (),
    "constrained_review": (
        "bench_feasible", "accessibility_status", "notes",
    ),
}


def entry_explanation(scenario):
    return {
        "opportunity": (
            "Opportunity Review selected this stop because a current "
            "observation would be particularly useful here."
        ),
        "route": "This stop is on the route you chose to review.",
        "nearby": "This stop is near the area you chose to review.",
        "map": "You chose this stop to review.",
        "direct": "You chose this stop to review.",
    }.get(scenario)


def evidence_explanation(opportunity):
    if not opportunity:
        return (
            "We do not yet have enough reliable information about seating at "
            "this stop. A current observation would help."
        )

    bench = opportunity.get("bench_status")
    adequacy = opportunity.get("adequacy_status")
    clearance = opportunity.get("clearance_status")
    strongest = opportunity.get("strongest_need_signal")

    if clearance == "observed_constrained":
        message = (
            "A previous visual review found limited pass-through space. "
            "Additional review may be needed before considering seating improvements."
        )
    elif adequacy == "limitation_observed" or strongest in (
        "observed_seating_limitation", "poor_comfort_evidence"
    ):
        message = (
            "Previous observations suggest the seating may be limited or "
            "uncomfortable. A current observation can help us understand "
            "whether improvements are needed."
        )
    elif bench == "conflicting":
        message = (
            "Our sources disagree about whether a bench is present. A current "
            "observation can help resolve that uncertainty."
        )
    elif bench in ("confirmed_no", "likely_no"):
        qualifier = "show" if bench == "confirmed_no" else "suggest"
        message = (
            f"Our records {qualifier} this stop may not have a bench. A current "
            "observation can help confirm what seating is available."
        )
    elif bench in ("confirmed_yes", "likely_yes") and adequacy == "unknown":
        appears = "is recorded as present" if bench == "confirmed_yes" else "appears to be present"
        message = (
            f"A bench {appears}, but we do not yet know whether the seating is "
            "comfortable or adequate."
        )
    else:
        message = (
            "We do not yet have enough reliable information about seating at "
            "this stop. A current observation would help."
        )

    if (opportunity.get("workflow_state") == "collect_clearance_observation"
            and clearance == "unknown"):
        message += (
            " If seating is absent or could be improved, a preliminary visual "
            "check of the available waiting space would be useful."
        )
    return message


def build_review_context(scenario, opportunity, campaign=None):
    focus = campaign or WORKFLOW_CAMPAIGN.get(
        opportunity.get("workflow_state") if opportunity else None
    )
    return {
        "scenario": scenario,
        "entry_explanation": entry_explanation(scenario),
        "evidence_explanation": evidence_explanation(opportunity),
        "review_focus": focus,
        "emphasized_fields": list(CAMPAIGN_FIELDS.get(focus, ())),
    }
