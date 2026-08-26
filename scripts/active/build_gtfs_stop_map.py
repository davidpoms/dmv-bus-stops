import sqlite3
import sys
import os
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(BASE_DIR)
)

from clients.gtfs_loader import download_gtfs


DB = Path(os.environ.get(
    "DMV_BUS_STOPS_DB", BASE_DIR / "src" / "database" / "dmv_bus_stops.db"
))

MATCH_DISTANCE = 0.0005


def main():

    gtfs = download_gtfs()

    gtfs_stops = pd.read_csv(
        gtfs.open("stops.txt")
    )


    conn = sqlite3.connect(DB)


    bus_stops = pd.read_sql_query(
        """
        SELECT
            id,
            external_stop_id,
            latitude,
            longitude
        FROM bus_stops
        """,
        conn
    )


    conn.execute(
        """
        DROP TABLE IF EXISTS gtfs_stop_map
        """
    )


    conn.execute(
        """
        CREATE TABLE gtfs_stop_map
        (
            gtfs_stop_id TEXT PRIMARY KEY,
            bus_stop_id INTEGER NOT NULL,
            match_distance REAL,
            match_method TEXT
        )
        """
    )


    matches = []

    by_id = 0
    by_coordinate = 0


    for _, gtfs_stop in gtfs_stops.iterrows():

        match = None


        # --------------------------
        # FIRST: WMATA stop code match
        # --------------------------

        candidates = bus_stops[
            bus_stops.external_stop_id.astype(str)
            ==
            str(gtfs_stop.stop_code)
        ]


        if len(candidates):

            candidate = candidates.iloc[0]

            matches.append(
                (
                    str(gtfs_stop.stop_id),
                    int(candidate.id),
                    0,
                    "wmata_stop_code"
                )
            )

            by_id += 1
            continue



        # --------------------------
        # SECOND: coordinate fallback
        # --------------------------

        candidates = bus_stops[
            (
                abs(
                    bus_stops.latitude
                    -
                    gtfs_stop.stop_lat
                )
                < MATCH_DISTANCE
            )
            &
            (
                abs(
                    bus_stops.longitude
                    -
                    gtfs_stop.stop_lon
                )
                < MATCH_DISTANCE
            )
        ]


        if len(candidates):

            # choose closest, NOT first row

            candidates = candidates.copy()

            candidates["distance"] = (
                abs(
                    candidates.latitude
                    -
                    gtfs_stop.stop_lat
                )
                +
                abs(
                    candidates.longitude
                    -
                    gtfs_stop.stop_lon
                )
            )


            candidate = (
                candidates
                .sort_values("distance")
                .iloc[0]
            )


            matches.append(
                (
                    str(gtfs_stop.stop_id),
                    int(candidate.id),
                    float(candidate.distance),
                    "coordinate"
                )
            )

            by_coordinate += 1



    conn.executemany(
        """
        INSERT INTO gtfs_stop_map
        VALUES (?, ?, ?, ?)
        """,
        matches
    )


    conn.commit()


    print("GTFS stops:", len(gtfs_stops))
    print("Matched:", len(matches))
    print("By WMATA ID:", by_id)
    print("By coordinate:", by_coordinate)
    print(
        "Unmatched:",
        len(gtfs_stops)-len(matches)
    )


    conn.close()



if __name__ == "__main__":
    main()
