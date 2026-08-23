from pathlib import Path
import shutil


FILE = Path(
    "src/assessment/create_opportunity_assessments.py"
)


def main():

    backup = FILE.with_suffix(
        ".backup_priority"
    )

    print("Creating backup...")
    shutil.copy(
        FILE,
        backup
    )


    text = FILE.read_text()


    start = text.index(
        "        cursor.execute(\n        \"\"\"\n        SELECT"
    )


    end = text.index(
        "        rows = cursor.fetchall()",
        start
    )


    replacement = r'''
        cursor.execute(
            """
            SELECT

                oa.physical_stop_id,

                COALESCE(
                    sps.factors,
                    '{}'
                ),

                COALESCE(
                    json_extract(
                        sps.factors,
                        '$.combined_route_weekday_boardings'
                    ),
                    0
                ),

                COALESCE(
                    json_extract(
                        sps.factors,
                        '$.highest_route_weekday_boardings'
                    ),
                    0
                ),

                COALESCE(
                    json_extract(
                        sps.factors,
                        '$.routes_served'
                    ),
                    0
                ),

                oa.wmata_stop_records


            FROM opportunity_assessments oa

            LEFT JOIN stop_priority_snapshots sps

                ON sps.stop_id =
                   oa.physical_stop_id;

            """
        )

'''


    text = (
        text[:start]
        +
        replacement
        +
        text[end:]
    )


    FILE.write_text(text)


    print(
        "Patch complete"
    )


if __name__ == "__main__":
    main()