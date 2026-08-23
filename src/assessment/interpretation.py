"""
Shared interpretation logic.

This module converts evidence into transparent interpretations.

Evidence = observed facts.
Interpretation = what the system concludes from those facts.
"""



def interpret_bench_status(evidence):

    osm = evidence.get("osm")
    transit = evidence.get("transit")

    if not osm:
        return {
            "status": "unknown",
            "label": "No evidence yet",
            "confidence": "low",
            "observed": [],
            "inferred": [
                "Bench status cannot be determined"
            ]
        }

    if osm.get("osm_bench") == 1:
        return {
            "status": "confirmed_bench",
            "label": "Confirmed bench",
            "confidence": "high",
            "observed": [
                "Bench mapped in OSM"
            ],
            "inferred": []
        }

    if osm.get("osm_shelter") == 1:
        return {
            "status": "bench_unknown_shelter_present",
            "label": "Shelter present, bench needs verification",
            "confidence": "medium",
            "observed": [
                "Shelter mapped in OSM"
            ],
            "inferred": [
                "Bench may exist but requires verification"
            ]
        }

    observed = [
        "No bench mapped in OSM"
    ]

    if transit and transit.get("gtfs_bus_stop") == 1:
        observed.append(
            "Transit stop confirmed by GTFS"
        )

    return {
        "status": "needs_review",
        "label": "Needs bench review",
        "confidence": "medium",
        "observed": observed,
        "inferred": [
            "Physical verification recommended"
        ]
    }



def interpret_review_priority(evidence, bench_status, context=None):

    osm = evidence.get("osm")
    transit = evidence.get("transit")

    if bench_status["status"] == "confirmed_bench":
        return {
            "level": "low",
            "reasons": [
                "Bench already mapped"
            ]
        }

    if osm and osm.get("osm_shelter") == 1:
        return {
            "level": "medium",
            "reasons": [
                "Shelter mapped",
                "Bench status requires verification"
            ]
        }

    reasons = [
        "No bench evidence",
        "Volunteer review needed"
    ]

    if transit and transit.get("gtfs_bus_stop") == 1:
        reasons.insert(
            0,
            "Active transit stop confirmed"
        )

    return {
        "level": "high",
        "reasons": reasons
    }


def summarize_stop_evidence(evidence):

    osm = evidence.get("osm") or {}
    transit = evidence.get("transit") or {}
    ddot = evidence.get("ddot") or []
    reviews = evidence.get("reviews") or []

    return {
        "transit_confirmed":
            transit.get("gtfs_bus_stop", 0) == 1,

        "osm_features": {
            "bench":
                osm.get("osm_bench", 0) == 1,

            "shelter":
                osm.get("osm_shelter", 0) == 1
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

    transit = evidence.get("transit") or {}
    osm = evidence.get("osm") or {}

    actions = []

    if transit.get("gtfs_bus_stop") == 1:
        actions.append(
            "Verify physical stop amenities"
        )

    if osm.get("osm_bench", 0) == 0:
        actions.append(
            "Confirm whether bench exists"
        )

    if osm.get("osm_shelter", 0) == 0:
        actions.append(
            "Confirm whether shelter exists"
        )

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
