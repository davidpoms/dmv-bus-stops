"""
Calculate stop priority scores.

Version 1:
- ridership demand
- route connectivity
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)



def calculate_scores():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        DELETE FROM stop_priority_snapshots;
        """
    )


    cursor.execute(
        """
        WITH stop_demand AS (

            SELECT
                b.id AS stop_id,

                COUNT(
                    DISTINCT sr.route_id
                ) AS route_count,

                COALESCE(
                    SUM(
                        rs.weekday_boardings
                    ),
                    0
                ) AS weekday_boardings


            FROM bus_stops b

            LEFT JOIN stop_routes sr
                ON b.gtfs_stop_id = sr.stop_id

            LEFT JOIN ridership_snapshots rs
                ON sr.route_id = rs.route_id


            GROUP BY b.id
        )


        SELECT *
        FROM stop_demand;
        """
    )


    rows = cursor.fetchall()


    max_boardings = max(
        row[2]
        for row in rows
    )

    max_routes = max(
        row[1]
        for row in rows
    )


    ranked = []


    for stop_id, route_count, boardings in rows:

        ridership_score = (
            boardings / max_boardings * 100
            if max_boardings
            else 0
        )


        route_score = (
            route_count / max_routes * 100
            if max_routes
            else 0
        )


        priority = (
            ridership_score * 0.70
            +
            route_score * 0.30
        )


        ranked.append(
            (
                stop_id,
                priority,
                {
                    "weekday_boardings": boardings,
                    "routes_served": route_count,
                    "ridership_score": ridership_score,
                    "route_score": route_score
                }
            )
        )


    ranked.sort(
        key=lambda x: x[1],
        reverse=True
    )


    for rank, item in enumerate(
        ranked,
        start=1
    ):

        cursor.execute(
            """
            INSERT INTO stop_priority_snapshots
            (
                stop_id,
                priority_score,
                priority_rank,
                factors
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                item[0],
                item[1],
                rank,
                json.dumps(item[2])
            )
        )


    conn.commit()
    conn.close()


    print(
        f"Scored {len(ranked):,} stops"
    )



if __name__ == "__main__":
    calculate_scores()
