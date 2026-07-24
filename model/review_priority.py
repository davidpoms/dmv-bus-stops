"""
Adjust stop priority using volunteer-confirmed conditions.
"""


def apply_review_adjustment(
    base_score,
    review_summary
):
    """
    Increase priority when reviews
    confirm unmet needs.

    base_score:
        existing demand priority

    review_summary:
        output from summarize_reviews()

    """


    adjustment = 0


    if review_summary.get(
        "review_count",
        0
    ) == 0:

        return base_score


    confidence = review_summary.get(
        "confidence",
        0
    )


    if (
        review_summary.get(
            "bench_present"
        )
        is False
    ):

        adjustment += 10


    if (
        review_summary.get(
            "shelter_present"
        )
        is False
    ):

        adjustment += 5


    # only apply full adjustment
    # when volunteers are confident

    adjustment = (
        adjustment
        *
        confidence
        /
        100
    )


    return round(
        base_score + adjustment
    )
