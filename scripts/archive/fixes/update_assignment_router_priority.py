from pathlib import Path


FILE = Path("src/review/assignment_router.py")


def main():

    text = FILE.read_text(
        encoding="utf-8"
    )


    old = """
            ORDER BY rq.priority_rank


            LIMIT 1
"""


    new = """
            LEFT JOIN opportunity_assessments oa

                ON oa.physical_stop_id = rq.physical_stop_id


            ORDER BY

                oa.combined_route_weekday_boardings DESC,


                rq.priority_rank ASC


            LIMIT 1
"""


    if old not in text:
        raise Exception(
            "Could not find priority ordering block"
        )


    text = text.replace(
        old,
        new,
        1
    )


    FILE.write_text(
        text,
        encoding="utf-8"
    )


    print(
        "Updated review priority ordering"
    )


if __name__ == "__main__":
    main()