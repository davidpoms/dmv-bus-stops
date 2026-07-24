"""
Link WMATA GTFS stops to DC GIS bus stops.

Uses latitude/longitude matching to populate:
    bus_stops.gtfs_stop_id
"""

from pathlib import Path
import sqlite3
import pandas as pd

from clients.gtfs_loader import download_gtfs


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)


MATCH_DISTANCE = 0.0005
# roughly ~50 meters in latitude/longitude degrees



def load_gtfs_stops():

    gtfs = download_gtfs()

    return pd.read_csv(
        gtfs.open("stops.txt")
    )



def load_database_stops():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    df = pd.read_sql_query(
        """
        SELECT
            id,
            external_stop_id,
            latitude,
            longitude
        FROM bus_stops;
        """,
        conn
    )

    conn.close()

    return df



def link_stops():

    gtfs_stops = load_gtfs_stops()

    db_stops = load_database_stops()


    updates = []


    for _, stop in db_stops.iterrows():

        matches = gtfs_stops[
            (
                abs(
                    gtfs_stops.stop_lat
                    -
                    stop.latitude
                )
                <
                MATCH_DISTANCE
            )
            &
            (
                abs(
                    gtfs_stops.stop_lon
                    -
                    stop.longitude
                )
                <
                MATCH_DISTANCE
            )
        ]


        if len(matches):

            gtfs_id = str(
                matches.iloc[0].stop_id
            )

            updates.append(
                (
                    gtfs_id,
                    stop.id
                )
            )


    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    for gtfs_id, row_id in updates:

        cursor.execute(
            """
            UPDATE bus_stops
            SET gtfs_stop_id = ?
            WHERE id = ?;
            """,
            (
                gtfs_id,
                row_id
            )
        )


    conn.commit()
    conn.close()


    print(
        f"Matched {len(updates):,} stops"
    )



if __name__ == "__main__":

    link_stops()
