from pathlib import Path


FILE = Path("src/review/assignment_router.py")


def main():

    text = FILE.read_text(
        encoding="utf-8"
    )


    bad = """
            ORDER BY

                oa.combined_route_weekday_boardings DESC,


                rq.priority_rank ASC


            LIMIT 1
"""


    if bad not in text:
        raise Exception(
            "Could not find updated ordering block"
        )


    # Add the JOIN immediately after FROM review_queue rq
    old_from = """
            FROM review_queue rq


            WHERE rq.review_status='pending'
"""


    new_from = """
            FROM review_queue rq


            LEFT JOIN opportunity_assessments oa

                ON oa.physical_stop_id = rq.physical_stop_id


            WHERE rq.review_status='pending'
"""


    if old_from not in text:
        raise Exception(
            "Could not find review_queue FROM block"
        )


    text = text.replace(
        old_from,
        new_from,
        1
    )


    FILE.write_text(
        text,
        encoding="utf-8"
    )


    print(
        "Fixed assignment router JOIN placement"
    )


if __name__ == "__main__":
    main()