"""
Load WMATA Metrobus ridership data.

Handles WMATA tab-delimited export format and
stores daily and monthly ridership metrics.
"""

import csv
import sqlite3
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR /
    "src" /
    "database" /
    "dmv_bus_stops.db"
)

RIDERSHIP_FOLDER = (
    BASE_DIR /
    "data" /
    "raw" /
    "ridership"
)


def find_latest_ridership_file():

    files = list(
        RIDERSHIP_FOLDER.glob("*.csv")
    )

    if not files:
        raise FileNotFoundError(
            "No ridership file found."
        )

    return max(
        files,
        key=lambda f: f.stat().st_mtime
    )


def clean_number(value):

    if not value:
        return 0

    return float(
        value.replace(",", "").strip()
    )


def load_ridership(file_path):

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    records_loaded = 0


    with open(
        file_path,
        "r",
        encoding="utf-8-sig"
    ) as csv_file:


        reader = csv.DictReader(
            csv_file,
            delimiter="\t"
        )


        for row in reader:

            route_id = row["Route"].strip()

            if not route_id:
                continue


            cursor.execute(
                """
                INSERT INTO ridership_snapshots
                (
                    route_id,
                    service_type,
                    period,
                    monthly_boardings,
                    weekday_boardings,
                    saturday_boardings,
                    sunday_boardings,
                    source
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?)

                """,

                (
                    route_id,
                    "Metrobus",
                    datetime.now().strftime(
                        "%Y-%m-%d"
                    ),
                    clean_number(
                        row["Monthly Total"]
                    ),
                    clean_number(
                        row["Weekday"]
                    ),
                    clean_number(
                        row["Saturday"]
                    ),
                    clean_number(
                        row["Sunday"]
                    ),
                    "WMATA Metrobus Ridership Summary"
                )

            )

            records_loaded += 1


    cursor.execute(
        """
        INSERT INTO data_refresh_log
        (
            dataset,
            status,
            records_loaded,
            notes
        )

        VALUES (?, ?, ?, ?)

        """,

        (
            "WMATA ridership",
            "SUCCESS",
            records_loaded,
            file_path.name
        )
    )


    connection.commit()
    connection.close()


    print(
        f"Loaded {records_loaded} ridership records."
    )


if __name__ == "__main__":

    file = find_latest_ridership_file()

    print(
        f"Using ridership file: {file}"
    )

    load_ridership(file)