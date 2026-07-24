"""
Aggregate multiple stop reviews
into a single confidence summary.
"""


def summarize_reviews(
    stop_id,
    reviews
):
    """
    Combine volunteer reviews.

    reviews example:

    [
        {
            "has_bench": 0,
            "has_shelter": 0,
            "reviewer_confidence": 90
        }
    ]

    """

    if not reviews:

        return {
            "stop_id": stop_id,
            "review_count": 0,
            "confidence": 0
        }


    bench_votes = []

    shelter_votes = []

    confidence_scores = []


    for review in reviews:

        bench_votes.append(
            review["has_bench"]
        )

        shelter_votes.append(
            review["has_shelter"]
        )

        confidence_scores.append(
            review[
                "reviewer_confidence"
            ]
        )


    bench_present = (
        sum(bench_votes)
        >
        len(bench_votes) / 2
    )


    shelter_present = (
        sum(shelter_votes)
        >
        len(shelter_votes) / 2
    )


    confidence = (
        sum(confidence_scores)
        /
        len(confidence_scores)
    )


    return {

        "stop_id": stop_id,

        "bench_present":
            bench_present,

        "shelter_present":
            shelter_present,

        "review_count":
            len(reviews),

        "confidence":
            round(confidence)

    }
