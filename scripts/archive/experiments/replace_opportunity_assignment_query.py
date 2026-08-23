from pathlib import Path


FILE = Path("src/review/assignment_router.py")


def main():

    text = FILE.read_text(
        encoding="utf-8"
    )


    start_marker = """
    else:

        row = cur.execute(
"""


    end_marker = """
        ).fetchone()



    if not row:
"""


    start = text.find(start_marker)

    if start == -1:
        raise Exception(
            "Could not find opportunity query start"
        )


    end = text.find(
        end_marker,
        start
    )

    if end == -1:
        raise Exception(
            "Could not find opportunity query end"
        )


    replacement = """
    else:

        row = cur.execute(
            \"\"\"
            SELECT
                rq.id,
                rq.physical_stop_id


            FROM review_queue rq


            LEFT JOIN opportunity_assessments oa

                ON oa.physical_stop_id = rq.physical_stop_id


            WHERE rq.review_status='pending'

            AND rq.community_review_available=1


            AND rq.physical_stop_id NOT IN (

                SELECT stop_id

                FROM stop_review_assignments

                WHERE reviewer_id=?

            )


            AND rq.physical_stop_id NOT IN (

                SELECT stop_id

                FROM stop_review_assignments

                WHERE status='assigned'

            )


            ORDER BY

                oa.combined_route_weekday_boardings DESC,

                rq.priority_rank ASC


            LIMIT 1

            \"\"\",
            (
                reviewer_id,
            )
        ).fetchone()



"""


    text = (
        text[:start]
        + replacement
        + text[end:]
    )


    FILE.write_text(
        text,
        encoding="utf-8"
    )


    print(
        "Replaced opportunity assignment query"
    )


if __name__ == "__main__":
    main()