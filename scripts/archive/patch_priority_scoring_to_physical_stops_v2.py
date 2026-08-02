from pathlib import Path
import shutil
import re


TARGET = Path(
    "src/scoring/calculate_stop_priority.py"
)

BACKUP = TARGET.with_suffix(
    ".py.backup2"
)


def main():

    print("Creating backup...")

    shutil.copy(
        TARGET,
        BACKUP
    )


    text = TARGET.read_text(
        encoding="utf-8"
    )


    # Replace old stop joins
    pattern = re.compile(
        r"""
        FROM\s+bus_stops\s+b
        .*?
        JOIN\s+gtfs_stop_map\s+gm
        .*?
        ON\s+gm\.bus_stop_id\s*=\s*b\.id
        .*?
        JOIN\s+stop_routes\s+sr
        .*?
        ON\s+sr\.stop_id\s*=\s*gm\.gtfs_stop_id
        """,
        re.S | re.X
    )


    replacement = """
FROM physical_stops ps


JOIN physical_stop_members pm

    ON pm.physical_stop_id = ps.id


JOIN stop_routes sr

    ON sr.stop_id = pm.bus_stop_id
"""


    text, count = pattern.subn(
        replacement,
        text
    )


    if count == 0:

        raise Exception(
            "Could not replace stop join section"
        )


    # Replace route_daily dependency
    pattern2 = re.compile(
        r"""
        LEFT\s+JOIN\s+route_daily\s+rd

        \s+ON\s+sr\.route_id\s*=\s*rd\.route_id
        """,
        re.S | re.X
    )


    replacement2 = """
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


    text, count2 = pattern2.subn(
        replacement2,
        text
    )


    if count2 == 0:

        raise Exception(
            "Could not replace route_daily section"
        )


    TARGET.write_text(
        text,
        encoding="utf-8"
    )


    print("Patch complete")
    print(
        f"Backup: {BACKUP}"
    )


if __name__ == "__main__":
    main()