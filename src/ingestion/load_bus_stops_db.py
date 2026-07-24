"""
Load normalized bus stops into SQLite.

Uses upsert behavior so the loader
can safely be rerun.
"""

import sqlite3
from pathlib import Path

from src.ingestion.load_bus_stops import load_bus_stops


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)



def save_bus_stops(
    stops
):

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()


    for stop in stops:

        cursor.execute(
            """
            INSERT INTO bus_stops
            (
                external_stop_id,
                latitude,
                longitude,
                stop_name,
                direction
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(external_stop_id)
            DO UPDATE SET

                latitude = excluded.latitude,

                longitude = excluded.longitude,

                stop_name = excluded.stop_name,

                direction = excluded.direction,

                updated_at = CURRENT_TIMESTAMP
            """,
            (
                str(stop["stop_id"]),
                stop["latitude"],
                stop["longitude"],
                stop.get("stop_name"),
                stop.get("direction")
            )
        )


    connection.commit()

    connection.close()



if __name__ == "__main__":

    stops = load_bus_stops()


    print(
        f"Loaded {len(stops):,} stops from API."
    )


    save_bus_stops(
        stops
    )


    print(
        "Database upsert complete."
    )
