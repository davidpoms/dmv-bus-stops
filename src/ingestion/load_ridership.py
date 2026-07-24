"""
Load WMATA Metrobus ridership data into database.

Handles WMATA tab-delimited export format.
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

    files = list(RIDERSHIP_FOLDER.glob("*.csv"))

    if not files:
        raise FileNotFoundError(
            "No ridership file found."
        )

    return max(
        files,
        key=lambda f: f.stat().st_mtime
    )


def load_ridership(file_path):

    connection = sqlite3.connect(DATABASE_PATH)

    cursor = connection.cursor()

    records_loaded = 0


    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as csv_file:


        reader = csv.reader(
            csv_file,
            delimiter="\t"
        )


        # Skip first title/header row
        next(reader)


        header = next(reader)


        for row in reader:

            if not row:
                continue


            route = row[0].strip()


            # Skip totals row
            if route == "Grand Total":
                continue


            monthly_total = (
                row[4]
                .replace(",", "")
                .strip()
            )


            if not monthly_total:
                continue


            cursor.execute(
                """
                INSERT INTO ridership_snapshots
                (
                    route_id,
                    service_type,
                    period,
                    monthly_boardings,
                    source
                )

                VALUES (?, ?, ?, ?, ?)

                """,

                (
                    route,
                    "Monthly Total",
                    datetime.now().strftime("%Y-%m-%d"),
                    float(monthly_total),
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
