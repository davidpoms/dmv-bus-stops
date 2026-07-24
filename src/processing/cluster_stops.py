"""
DMV Bus Stops Intelligence Platform

Create physical stop locations by clustering
nearby WMATA stop records.

Purpose:
- Collapse duplicate stop records
- Preserve all source stop IDs
- Create physical locations for scoring

Distance threshold:
~50 feet
"""

import sqlite3
import math
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    /
    "src"
    /
    "database"
    /
    "dmv_bus_stops.db"
)


CLUSTER_DISTANCE_METERS = 15



def distance_meters(
    lat1,
    lon1,
    lat2,
    lon2
):

    """
    Haversine distance.
    """

    earth_radius = 6371000


    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)


    d_phi = math.radians(
        lat2 - lat1
    )

    d_lambda = math.radians(
        lon2 - lon1
    )


    a = (
        math.sin(d_phi / 2) ** 2
        +
        math.cos(phi1)
        *
        math.cos(phi2)
        *
        math.sin(d_lambda / 2) ** 2
    )


    return (
        earth_radius
        *
        2
        *
        math.atan2(
            math.sqrt(a),
            math.sqrt(1-a)
        )
    )



def create_tables(cursor):

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stop_locations (

            id INTEGER PRIMARY KEY,

            latitude REAL NOT NULL,

            longitude REAL NOT NULL,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stop_location_members (

            location_id INTEGER NOT NULL,

            stop_id INTEGER NOT NULL,

            FOREIGN KEY(location_id)
                REFERENCES stop_locations(id),

            FOREIGN KEY(stop_id)
                REFERENCES bus_stops(id)
        );
        """
    )



def cluster_stops():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    create_tables(
        cursor
    )


    cursor.execute(
        """
        DELETE FROM stop_location_members;

        DELETE FROM stop_locations;
        """
    )


    cursor.execute(
        """
        SELECT
            id,
            latitude,
            longitude

        FROM bus_stops;
        """
    )


    stops = cursor.fetchall()


    clusters = []


    for stop in stops:

        stop_id, lat, lon = stop


        assigned = False


        for cluster in clusters:

            distance = distance_meters(
                lat,
                lon,
                cluster["latitude"],
                cluster["longitude"]
            )


            if distance <= CLUSTER_DISTANCE_METERS:

                cluster["stops"].append(
                    stop_id
                )

                assigned = True

                break


        if not assigned:

            clusters.append(
                {
                    "latitude": lat,
                    "longitude": lon,
                    "stops": [
                        stop_id
                    ]
                }
            )


    for cluster in clusters:


        cursor.execute(

            """
            INSERT INTO stop_locations
            (
                latitude,
                longitude
            )

            VALUES (?, ?)

            """,

            (
                cluster["latitude"],
                cluster["longitude"]
            )

        )


        location_id = cursor.lastrowid


        for stop_id in cluster["stops"]:

            cursor.execute(

                """
                INSERT INTO stop_location_members

                (
                    location_id,
                    stop_id
                )

                VALUES (?, ?)

                """,

                (
                    location_id,
                    stop_id
                )

            )


    conn.commit()


    print(
        f"Created {len(clusters):,} physical stop locations"
    )


    print(
        f"Clustered {len(stops):,} WMATA stop records"
    )


    conn.close()



if __name__ == "__main__":

    cluster_stops()
