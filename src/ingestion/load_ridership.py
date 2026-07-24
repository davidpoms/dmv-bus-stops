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
        value
        .replace(",", "")
        .strip()
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
        encoding="utf-8"
    ) as csv_file:


        reader = csv.reader(
            csv_file,
            delimiter="\t"
        )


        # Skip title row
        next(reader)


        # Header row
        header = next(reader)


        for row in reader:

            if not row:
                continue


            route_id = row[0].strip()


            # Ignore summary rows
            if route_id in [
                "Grand Total",
                ""
            ]:
                continue


            weekday = clean_number(row[1])
            sunday = clean_number(row[2])
            saturday = clean_number(row[3])
            monthly_total = clean_number(row[4])


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
                    monthly_total,
                    weekday,
                    saturday,
                    sunday,
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
