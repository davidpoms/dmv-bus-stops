from pathlib import Path
import shutil


FILE = Path(
    "src/assessment/create_opportunity_assessments.py"
)


def main():

    print("Creating backup...")

    backup = FILE.with_suffix(
        ".py.backup_priority_source"
    )

    shutil.copy(
        FILE,
        backup
    )


    text = FILE.read_text(
        encoding="utf-8"
    )


    start_marker = """
        cursor.execute(
            """
    """


    # Replace the whole route calculation area
    start = text.find(
        "        cursor.execute(\n            \"\"\"\n            SELECT DISTINCT"
    )


    if start == -1:

        raise Exception(
            "Could not find old route lookup block"
        )


    end = text.find(
        "\n\n\n        if not routes:",
        start
    )


    if end == -1:

        raise Exception(
            "Could not find end of route block"
        )


    replacement = r'''
        cursor.execute(
            """
            SELECT
                factors

            FROM stop_priority_snapshots

            WHERE stop_id = ?

            ORDER BY calculated_date DESC

            LIMIT 1;
            """,
            (
                physical_stop_id,
            )
        )


        priority_row = cursor.fetchone()


        combined_route_weekday = 0
        highest_route_weekday = 0
        routes_served = 0
        routes = []
        priority_factors = {}


        if priority_row:

            import json

            priority_factors = json.loads(
                priority_row[0]
            )


            combined_route_weekday = (
                priority_factors.get(
                    "combined_route_weekday_boardings",
                    0
                )
            )


            highest_route_weekday = (
                priority_factors.get(
                    "highest_route_weekday_boardings",
                    0
                )
            )


            routes_served = (
                priority_factors.get(
                    "routes_served",
                    0
                )
            )


            routes = (
                priority_factors.get(
                    "routes",
                    []
                )
            )

'''

    text = (
        text[:start]
        +
        replacement
        +
        text[end:]
    )


    # Replace old len(routes) references
    text = text.replace(
        "len(routes)",
        "routes_served"
    )


    # Replace average_daily references
    text = text.replace(
        "average_daily",
        "combined_route_weekday"
    )


    text = text.replace(
        "highest_route_daily",
        "highest_route_weekday"
    )


    FILE.write_text(
        text,
        encoding="utf-8"
    )


    print("Patch complete")
    print("Backup:", backup)


if __name__ == "__main__":
    main()