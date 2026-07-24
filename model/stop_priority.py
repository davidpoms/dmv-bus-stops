"""
Build stop priority recommendations.

Combines database-derived signals into
a ranked stop recommendation.
"""

from model.priority import calculate_priority_score


def build_stop_priority(
    stop_id,
    ridership_score=0,
    accessibility_score=0,
    community_score=0,
    infrastructure_score=0,
    review_confidence=0
):
    """
    Create a complete priority record
    for one bus stop.
    """


    result = calculate_priority_score(
        ridership_score=ridership_score,
        accessibility_score=accessibility_score,
        community_score=community_score,
        infrastructure_score=infrastructure_score,
        review_confidence=review_confidence
    )


    return {

        "stop_id": stop_id,

        "priority_score":
            result["priority_score"],

        "priority_category":
            result["priority_category"],

        "signals":
            result["signals"]

    }
