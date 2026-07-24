"""
Build physical bus stop locations.

Converts WMATA stop records into real-world
physical stop locations.

One physical stop may contain multiple WMATA
stop records.
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


MAX_DISTANCE_METERS = 20



def haversine(
    lat1,
    lon1,
    lat2,
    lon2
):

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
            math.sqrt(1 - a)
        )
    )



def setup_tables(cursor):

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS physical_stops (

            id INTEGER PRIMARY KEY,

            latitude REAL NOT NULL,

            longitude REAL NOT NULL,

            primary_name TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS physical_stop_members (

            physical_stop_id INTEGER NOT NULL,

            bus_stop_id INTEGER NOT NULL,

            FOREIGN KEY(
                physical_stop_id
            )
            REFERENCES physical_stops(id),

            FOREIGN KEY(
                bus_stop_id
            )
            REFERENCES bus_stops(id)

        );
        """
    )



def cluster_stops(stops):

    """
    Simple connected-component clustering.
    """

    remaining = {
        stop["id"]: stop
        for stop in stops
    }


    clusters = []


    while remaining:


        seed_id = next(
            iter(remaining)
        )


        queue = [
            remaining.pop(seed_id)
        ]


        cluster = []


        while queue:

            current = queue.pop()

            cluster.append(
                current
            )


            nearby = []


            for stop_id, stop in list(
                remaining.items()
            ):

                distance = haversine(

                    current["latitude"],
                    current["longitude"],

                    stop["latitude"],
                    stop["longitude"]

                )


                if distance <= MAX_DISTANCE_METERS:

                    nearby.append(
                        stop_id
                    )


            for stop_id in nearby:

                queue.append(
                    remaining.pop(
                        stop_id
                    )
                )


        clusters.append(
            cluster
        )


    return clusters



def build_physical_stops():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    setup_tables(
        cursor
    )


    cursor.execute(
        """
        DELETE FROM physical_stop_members;
        """
    )


    cursor.execute(
        """
        DELETE FROM physical_stops;
        """
    )


    cursor.execute(
        """
        SELECT
            id,
            latitude,
            longitude,
            stop_name

        FROM bus_stops;
        """
    )


    stops = []


    for row in cursor.fetchall():

        stops.append(
            {
                "id": row[0],
                "latitude": row[1],
                "longitude": row[2],
                "name": row[3]
            }
        )


    clusters = cluster_stops(
        stops
    )


    for cluster in clusters:


        latitude = sum(
            s["latitude"]
            for s in cluster
        ) / len(cluster)


        longitude = sum(
            s["longitude"]
            for s in cluster
        ) / len(cluster)


        names = [
            s["name"]
            for s in cluster
            if s["name"]
        ]


        primary_name = max(
            names,
            key=len
        ) if names else None



        cursor.execute(

            """
            INSERT INTO physical_stops
            (
                latitude,
                longitude,
                primary_name
            )

            VALUES (?, ?, ?)

            """,

            (
                latitude,
                longitude,
                primary_name
            )

        )


        physical_id = cursor.lastrowid



        for stop in cluster:


            cursor.execute(

                """
                INSERT INTO physical_stop_members

                (
                    physical_stop_id,
                    bus_stop_id
                )

                VALUES (?, ?)

                """,

                (
                    physical_id,
                    stop["id"]
                )

            )


    conn.commit()


    print(
        f"Processed {len(stops):,} WMATA stops"
    )

    print(
        f"Created {len(clusters):,} physical stops"
    )


    conn.close()



if __name__ == "__main__":

    build_physical_stops()
