from pathlib import Path


FILE = Path(
    "src/assessment/create_opportunity_assessments.py"
)


def main():

    text = FILE.read_text(
        encoding="utf-8"
    )


    old = """
            SELECT DISTINCT
                sr.route_id

            FROM physical_stop_members pm

            JOIN stop_routes sr

                ON sr.stop_id = pm.bus_stop_id

            WHERE pm.physical_stop_id = ?;
    """


    new = """
            SELECT DISTINCT
                sr.route_id

            FROM physical_stop_members pm

            JOIN bus_stops b

                ON b.id = pm.bus_stop_id

            JOIN gtfs_stop_map gm

                ON gm.bus_stop_id = b.id

            JOIN stop_routes sr

                ON sr.stop_id = gm.gtfs_stop_id

            WHERE pm.physical_stop_id = ?;
    """


    if old not in text:

        raise Exception(
            "Could not find old route query"
        )


    text = text.replace(
        old,
        new
    )


    FILE.write_text(
        text,
        encoding="utf-8"
    )


    print(
        "Patched opportunity assessment route matching"
    )


if __name__ == "__main__":
    main()