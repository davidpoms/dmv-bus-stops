"""
Volunteer review feedback processing.

Converts human observations into
structured stop intelligence.
"""


def process_review_feedback(
    stop_id,
    answers
):
    """
    Process a volunteer review.

    Example:

    answers = {
        "bench_present": False,
        "shelter_present": False,
        "space_available": True,
        "image_clear": True
    }

    """


    confidence = 0


    if answers.get(
        "image_clear",
        False
    ):
        confidence += 30


    if "bench_present" in answers:
        confidence += 25


    if "shelter_present" in answers:
        confidence += 20


    if "space_available" in answers:
        confidence += 25



    return {

        "stop_id": stop_id,

        "bench_present":
            answers.get(
                "bench_present"
            ),

        "shelter_present":
            answers.get(
                "shelter_present"
            ),

        "space_available":
            answers.get(
                "space_available"
            ),

        "review_confidence":
            min(
                confidence,
                100
            )

    }
