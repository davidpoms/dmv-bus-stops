"""
Shared interpretation logic.

This module converts evidence into transparent interpretations.

Evidence = observed facts.
Interpretation = what the system concludes from those facts.
"""

STATUS_WORDING = {
    "confirmed_yes": "Community consensus indicates {article} {amenity} is present.",
    "confirmed_no": "Community consensus indicates no {amenity} is present.",
    "likely_yes": (
        "Available evidence suggests {article} {amenity} is present, but "
        "community consensus has not been reached."
    ),
    "likely_no": (
        "Available evidence suggests no {amenity} is present, but community "
        "consensus has not been reached."
    ),
    "conflicting": (
        "Available evidence about {amenity} presence conflicts; verification "
        "is recommended."
    ),
    "unknown": (
        "Current evidence is insufficient to determine whether {article} "
        "{amenity} is present."
    ),
}


def amenity_status_sentence(amenity, status):
    article = "a" if amenity == "bench" else "a"
    return STATUS_WORDING[status].format(amenity=amenity, article=article)


def _canonical_status(evidence, amenity):
    statuses = evidence.get("amenity_status") or {}
    if isinstance(statuses, dict):
        value = statuses.get(amenity)
        return value.get("derived_status") if isinstance(value, dict) else value
    for row in statuses:
        if row.get("amenity_type") == amenity:
            return row.get("derived_status")
    return "unknown"


def interpret_bench_status(evidence):
    status = _canonical_status(evidence, "bench")
    return {
        "status": status,
        "label": status.replace("_", " ").title(),
        "confidence": "high" if status.startswith("confirmed_") else "medium",
        "observed": [amenity_status_sentence("bench", status)],
        "inferred": (
            ["Physical verification recommended"]
            if status in ("likely_yes", "likely_no", "conflicting", "unknown")
            else []
        ),
    }



def interpret_review_priority(evidence, bench_status, context=None):
    status = bench_status["status"]
    if status in ("confirmed_yes", "confirmed_no"):
        return {
            "level": "low",
            "reasons": [amenity_status_sentence("bench", status)]
        }
    if status == "conflicting":
        return {
            "level": "high",
            "reasons": [amenity_status_sentence("bench", status)]
        }
    return {
        "level": "medium",
        "reasons": [amenity_status_sentence("bench", status)]
    }


def summarize_stop_evidence(evidence):

    osm = evidence.get("osm") or {}
    transit = evidence.get("transit") or {}
    ddot = evidence.get("ddot") or []
    reviews = evidence.get("reviews") or []

    return {
        "transit_confirmed":
            transit.get("gtfs_bus_stop", 0) == 1,

        "canonical_amenity_status": {
            "bench": _canonical_status(evidence, "bench"),
            "shelter": _canonical_status(evidence, "shelter"),
        },

        "community_reviews":
            len(reviews),


        "ddot_shelter": {

            "records":
                len(ddot),

            "confirmed_active": False,

            "possible_new":
                any(
                    r.get("lifecycle_status")
                    == "POSSIBLE_NEW_DDOT_SHELTER"
                    for r in ddot
                ),

            "removed":
                any(
                    r.get("lifecycle_status")
                    == "MATCHED_REMOVED"
                    for r in ddot
                ),

            "routes":
                sorted(
                    {
                        route
                        for r in ddot
                        for route in
                        (r.get("route_ids") or "").split(",")
                        if route
                    }
                )
        },


        "data_sources": [
            source
            for source, present in [
                ("GTFS", transit.get("gtfs_bus_stop", 0)),
                ("OSM", osm.get("osm_feature_id")),
                ("Community Review", len(reviews))
            ]
            if present
        ]
    }



def generate_review_action_summary(evidence, review_priority):
    actions = []
    for amenity in ("bench", "shelter"):
        if _canonical_status(evidence, amenity) in (
            "likely_yes", "likely_no", "conflicting", "unknown"
        ):
            actions.append(f"Confirm whether {amenity} exists")

    if not evidence.get("reviews"):
        actions.append(
            "Collect first community observation"
        )

    return {
        "priority": review_priority["level"],
        "recommended_actions": actions
    }






def interpret_ddot_evidence(ddot_records):

    results = []

    for record in ddot_records or []:

        status = record.get(
            "lifecycle_status"
        )

        evidence_class = "quarantined_legacy"
        public_status = "Quarantined legacy DDOT reconciliation record"
        finding = (
            "This historical reconciliation record is retained for audit "
            "only and is not used to determine current shelter status."
        )


        source_label = (
            "DDOT API shelter asset record"
            if record.get("api_id")
            else
            "DDOT shelter procurement inventory July 2026"
        )


        results.append(
            {
                "source":
                    source_label,

                "source_type":
                    (
                        "api"
                        if record.get("api_id")
                        else
                        "procurement"
                    ),

                "source_record":
                    record.get("ddot_id")
                    or record.get("api_id"),

                "lifecycle_status":
                    status,

                "evidence_class":
                    evidence_class,

                "public_status":
                    public_status,

                "finding":
                    finding,

                "routes":
                    record.get("routes", []),

                "confidence":
                    record.get("confidence"),

                "details":
                    (
                        "Legacy route/lifecycle reconciliation; current "
                        "amenity authority disabled."
                    )
            }
        )


    return results
