from pathlib import Path
import shutil


TARGET = Path(
    "src/scoring/calculate_stop_priority.py"
)

BACKUP = TARGET.with_suffix(
    ".py.backup"
)


def main():

    print("Backing up scoring script...")

    shutil.copy(
        TARGET,
        BACKUP
    )


    text = TARGET.read_text(
        encoding="utf-8"
    )


    old_query = """
FROM bus_stops b


JOIN gtfs_stop_map gm

    ON gm.bus_stop_id = b.id


JOIN stop_routes sr

    ON sr.stop_id = gm.gtfs_stop_id
"""


    new_query = """
FROM physical_stops ps


JOIN physical_stop_members pm

    ON pm.physical_stop_id = ps.id


JOIN stop_routes sr

    ON sr.stop_id = pm.bus_stop_id
"""


    if old_query not in text:

        raise Exception(
            "Could not find old stop query block"
        )


    text = text.replace(
        old_query,
        new_query
    )


    old_route_daily = """
LEFT JOIN route_daily rd

    ON sr.route_id = rd.route_id
"""


    new_route_daily = """
LEFT JOIN
(
    SELECT
        route_id,
        weekday_boardings / 21.0 AS daily_boardings,
        weekday_boardings
    FROM ridership_snapshots
) rd

ON sr.route_id = rd.route_id
"""


    if old_route_daily not in text:

        raise Exception(
            "Could not find route_daily join"
        )


    text = text.replace(
        old_route_daily,
        new_route_daily
    )


    TARGET.write_text(
        text,
        encoding="utf-8"
    )


    print(
        "Patched calculate_stop_priority.py"
    )

    print(
        f"Backup created: {BACKUP}"
    )


if __name__ == "__main__":
    main()