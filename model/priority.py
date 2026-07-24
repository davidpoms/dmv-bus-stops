"""
Bus stop priority scoring engine.

Combines multiple intelligence signals
into an explainable priority score.
"""


def calculate_priority_score(
    ridership_score=0,
    accessibility_score=0,
    community_score=0,
    infrastructure_score=0,
    review_confidence=0
):
    """
    Calculate overall stop priority.

    All inputs are 0-100.

    Returns:
        score
        category
        explanation
    """


    score = (

        ridership_score * 0.40

        +

        accessibility_score * 0.20

        +

        community_score * 0.15

        +

        infrastructure_score * 0.15

        +

        review_confidence * 0.10

    )


    score = round(score)


    if score >= 85:
        category = "urgent"

    elif score >= 70:
        category = "high"

    elif score >= 50:
        category = "medium"

    else:
        category = "low"


    return {

        "priority_score": score,

        "priority_category": category,

        "signals": {

            "ridership":
                ridership_score,

            "accessibility":
                accessibility_score,

            "community":
                community_score,

            "infrastructure":
                infrastructure_score,

            "review_confidence":
                review_confidence

        }

    }
