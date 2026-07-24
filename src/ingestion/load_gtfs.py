"""
Load WMATA GTFS relationships into SQLite.

Populates:
- routes
- stop_routes
"""

import sqlite3
from pathlib import Path
import pandas as pd

from clients.gtfs_loader import download_gtfs


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)



def load_gtfs_tables():

    gtfs = download_gtfs()


    routes = pd.read_csv(
        gtfs.open("routes.txt")
    )


    trips = pd.read_csv(
        gtfs.open("trips.txt")
    )


    stop_times = pd.read_csv(
        gtfs.open("stop_times.txt")
    )


    return (
        routes,
        trips,
        stop_times
    )



def save_routes(
    routes
):

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    for _, row in routes.iterrows():

        cursor.execute(
            """
            INSERT INTO routes
            (
                route_id,
                route_name
            )
            VALUES (?, ?)

            ON CONFLICT(route_id)
            DO UPDATE SET

                route_name = excluded.route_name
            """,
            (
                str(row["route_short_name"]),
                row.get("route_long_name")
            )
        )


    conn.commit()
    conn.close()



def save_stop_routes(
    trips,
    stop_times
):

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    merged = stop_times.merge(
        trips[
            [
                "trip_id",
                "route_id"
            ]
        ],
        on="trip_id"
    )


    pairs = merged[
        [
            "stop_id",
            "route_id"
        ]
    ].drop_duplicates()


    for _, row in pairs.iterrows():

        cursor.execute(
            """
            INSERT INTO stop_routes
            (
                stop_id,
                route_id
            )
            VALUES (?, ?)
            """,
            (
                int(row["stop_id"]),
                str(row["route_id"])
            )
        )


    conn.commit()
    conn.close()



if __name__ == "__main__":

    routes, trips, stop_times = load_gtfs_tables()


    print(
        f"GTFS routes: {len(routes):,}"
    )

    print(
        f"GTFS trips: {len(trips):,}"
    )

    print(
        f"GTFS stop times: {len(stop_times):,}"
    )


    save_routes(
        routes
    )


    save_stop_routes(
        trips,
        stop_times
    )


    print(
        "GTFS load complete."
    )
