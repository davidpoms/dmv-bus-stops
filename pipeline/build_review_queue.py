"""
Build volunteer review queues.

Prioritizes stops where human review
will create the most value.
"""


def calculate_review_priority(
    priority_score,
    image_available=True,
    review_count=0,
    confidence=0
):
    """
    Calculate how useful a review would be.

    Higher score means:
    - important stop
    - available imagery
    - little existing review
    - low confidence
    """


    if not image_available:

        return 0


    score = priority_score


    # Encourage reviewing unknown stops
    if review_count == 0:
        score += 20

    elif review_count < 3:
        score += 10


    # Prioritize uncertainty
    score += (100 - confidence) * 0.20


    return round(score)



def build_review_queue(stops, limit=500):
    """
    Build ranked volunteer queue.

    Input:

    [
        {
            "stop_id": "700123",
            "priority_score": 85,
            "review_count": 0,
            "confidence": 30
        }
    ]

    """


    ranked = []


    for stop in stops:

        review_score = calculate_review_priority(
            priority_score=
                stop["priority_score"],

            image_available=
                stop.get(
                    "image_available",
                    True
                ),

            review_count=
                stop.get(
                    "review_count",
                    0
                ),

            confidence=
                stop.get(
                    "confidence",
                    0
                )
        )


        ranked.append(
            {
                **stop,
                "review_priority":
                    review_score
            }
        )


    ranked.sort(
        key=lambda x:
            x["review_priority"],
        reverse=True
    )


    return ranked[:limit]
