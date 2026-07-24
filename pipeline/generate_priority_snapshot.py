"""
Generate ranked stop priority snapshots.

Combines demand scores and review intelligence.
"""


from model.priority import calculate_priority_score
from model.review_priority import apply_review_adjustment



def generate_priority_snapshot(
    stops
):
    """
    Generate ranked priorities.

    Example input:

    [
        {
            "stop_id": "700123",
            "ridership_score": 90,
            "accessibility_score": 70,
            "community_score": 50,
            "infrastructure_score": 60,
            "review_summary": {...}
        }
    ]

    """


    results = []


    for stop in stops:


        base = calculate_priority_score(
            ridership_score=
                stop.get(
                    "ridership_score",
                    0
                ),

            accessibility_score=
                stop.get(
                    "accessibility_score",
                    0
                ),

            community_score=
                stop.get(
                    "community_score",
                    0
                ),

            infrastructure_score=
                stop.get(
                    "infrastructure_score",
                    0
                ),

            review_confidence=
                stop.get(
                    "review_summary",
                    {}
                ).get(
                    "confidence",
                    0
                )
        )


        final_score = apply_review_adjustment(
            base[
                "priority_score"
            ],

            stop.get(
                "review_summary",
                {}
            )
        )


        results.append(
            {
                "stop_id":
                    stop["stop_id"],

                "priority_score":
                    final_score,

                "priority_category":
                    (
                        "urgent"
                        if final_score >= 85
                        else
                        "high"
                        if final_score >= 70
                        else
                        "medium"
                    )
            }
        )


    return sorted(
        results,
        key=lambda x:
            x["priority_score"],
        reverse=True
    )
