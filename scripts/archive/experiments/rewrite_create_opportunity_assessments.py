from pathlib import Path
import shutil


FILE = Path(
    "src/assessment/create_opportunity_assessments.py"
)


BACKUP = FILE.with_suffix(
    ".py.backup"
)


def main():

    print("Creating backup...")

    shutil.copy(
        FILE,
        BACKUP
    )


    text = FILE.read_text(
        encoding="utf-8"
    )


    start = text.index(
        "        cursor.execute(\n        \"\"\"\n        SELECT"
    )


    end = text.index(
        "        \"\"\"\n    )",
        start
    ) + len(
        "        \"\"\"\n    )"
    )


    replacement = """
        cursor.execute(
            \"\"\"
            SELECT

                oa.physical_stop_id,

                oa.combined_route_weekday_boardings,

                oa.highest_route_weekday_boardings,

                oa.routes_served,

                oa.wmata_stop_records,

                COALESCE(
                    GROUP_CONCAT(
                        DISTINCT sr.route_id
                    ),
                    ''
                ) AS routes


            FROM physical_stops ps


            LEFT JOIN opportunity_assessments oa

                ON oa.physical_stop_id = ps.id


            LEFT JOIN physical_stop_members pm

                ON pm.physical_stop_id = ps.id


            LEFT JOIN stop_routes sr

                ON sr.stop_id = pm.bus_stop_id


            GROUP BY ps.id;

            \"\"\"
        )
"""


    new_text = (
        text[:start]
        +
        replacement
        +
        text[end:]
    )


    FILE.write_text(
        new_text,
        encoding="utf-8"
    )


    print(
        "Rewrite complete"
    )

    print(
        f"Backup: {BACKUP}"
    )


if __name__ == "__main__":
    main()