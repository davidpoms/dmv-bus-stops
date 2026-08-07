import sqlite3
from pathlib import Path


DB = Path("src/database/dmv_bus_stops.db")


def column_exists(cursor, table, column):
    rows = cursor.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return any(
        row[1] == column
        for row in rows
    )


def main():

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    table = "stop_amenity_evidence"


    print("Checking existing schema...")


    new_columns = {
        "jurisdiction": "TEXT",
        "value": "TEXT",
        "raw_value": "TEXT",
    }


    for column, datatype in new_columns.items():

        if not column_exists(
            cursor,
            table,
            column
        ):

            print(
                f"Adding column: {column}"
            )

            cursor.execute(
                f"""
                ALTER TABLE {table}
                ADD COLUMN {column} {datatype}
                """
            )

        else:

            print(
                f"Column already exists: {column}"
            )


    print("Backfilling existing records...")


    if column_exists(
        cursor,
        table,
        "present"
    ):

        cursor.execute(
            """
            UPDATE stop_amenity_evidence

            SET value =
                CASE
                    WHEN present = 1
                        THEN 'yes'
                    WHEN present = 0
                        THEN 'no'
                    ELSE NULL
                END,

                raw_value =
                CAST(present AS TEXT)

            WHERE value IS NULL
            """
        )


        print(
            f"Updated {cursor.rowcount} records"
        )


    conn.commit()

    print(
        "Migration complete."
    )


    print("\nCurrent schema:")

    for row in cursor.execute(
        "PRAGMA table_info(stop_amenity_evidence)"
    ):
        print(row)


    conn.close()


if __name__ == "__main__":
    main()