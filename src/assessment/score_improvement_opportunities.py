"""
Score physical bus stop improvement opportunities.

Creates a review priority ranking based on:

- rider exposure from WMATA ridership
- route connectivity
- physical stop evidence
- missing amenity evidence

This is an evidence prioritization layer,
not a final recommendation engine.
"""

import sqlite3
import json
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



def setup_table(cursor):

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS improvement_opportunities (

            id INTEGER PRIMARY KEY,

            physical_stop_id INTEGER NOT NULL,

            opportunity_score REAL,

            priority_rank INTEGER,

            factors JSON,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP

        );
        """
    )


    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_opportunity_rank

        ON improvement_opportunities(
            priority_rank
        );
        """
    )



def normalize(value, maximum):

    if not value or maximum == 0:
        return 0


    return (
        math.log1p(value)
        /
        math.log1p(maximum)
    ) * 100



ABSENCE_STATUSES = {"confirmed_no", "likely_no"}
VERIFICATION_SIGNALS = {
    "confirmed_yes": 0,
    "confirmed_no": 0,
    "likely_yes": 0.5,
    "likely_no": 0.5,
    "conflicting": 1,
    "unknown": 1,
}


def amenity_features(status):
    """Translate canonical status without treating missing evidence as absence."""
    return {
        "status": status,
        "absence_signal": 1 if status in ABSENCE_STATUSES else 0,
        "verification_need": VERIFICATION_SIGNALS[status],
    }


def calculate_amenity_gap(bench_status, shelter_status):
    """Preserve the existing 50-points-per-amenity gap slot."""
    return 50 * sum(
        status in ABSENCE_STATUSES
        for status in (bench_status, shelter_status)
    )



def score_opportunities(database_path=None):

    conn = sqlite3.connect(
        database_path or DATABASE_PATH
    )

    cursor = conn.cursor()


    setup_table(
        cursor
    )


    cursor.execute(
        """
        DELETE FROM improvement_opportunities;
        """
    )



    cursor.execute(
        """
        SELECT

            oa.physical_stop_id,

            COALESCE(
                sps.factors,
                '{}'
            ) AS priority_factors,

            oa.routes_served,

            oa.wmata_stop_records,

            bench.derived_status,

            shelter.derived_status


        FROM opportunity_assessments oa


        JOIN stop_gtfs_status sgs

            ON sgs.physical_stop_id =
               oa.physical_stop_id

           AND sgs.current_gtfs = 1


        LEFT JOIN stop_priority_snapshots sps

            ON sps.stop_id =
               oa.physical_stop_id


        JOIN stop_amenity_status bench

            ON bench.physical_stop_id = oa.physical_stop_id

           AND bench.amenity_type = 'bench'


        JOIN stop_amenity_status shelter

            ON shelter.physical_stop_id = oa.physical_stop_id

           AND shelter.amenity_type = 'shelter'

        """
    )


    rows = cursor.fetchall()


    if not rows:

        print(
            "No assessments found."
        )

        conn.commit()
        conn.close()
        return



    max_routes = max(
        row[2]
        for row in rows
    )


    max_records = max(
        row[3]
        for row in rows
    )



    scored = []



    for row in rows:


        (
            physical_stop_id,

            priority_factors,

            routes_served,

            records,

            bench_status,

            shelter_status

        ) = row



        ridership_score = 0

        combined_weekday = 0

        highest_route = 0


        if priority_factors:

            factors = json.loads(
                priority_factors
            )


            ridership_score = factors.get(
                "route_exposure_score",
                0
            )


            combined_weekday = factors.get(
                "combined_route_weekday_boardings",
                0
            )


            highest_route = factors.get(
                "highest_route_weekday_boardings",
                0
            )



        connectivity_score = normalize(
            routes_served,
            max_routes
        )


        physical_score = normalize(
            records,
            max_records
        )


        amenity_gap_score = calculate_amenity_gap(
            bench_status,
            shelter_status
        )


        opportunity_score = (

            ridership_score * 0.65

            +

            connectivity_score * 0.20

            +

            amenity_gap_score * 0.15

        )


        factors = {

            "route_exposure": {

                "combined_route_weekday_boardings":
                    round(
                        combined_weekday,
                        2
                    ),

                "highest_route_weekday_boardings":
                    round(
                        highest_route,
                        2
                    ),

                "score":
                    round(
                        ridership_score,
                        2
                    )

            },


            "network": {

                "routes_served":
                    routes_served,

                "score":
                    round(
                        connectivity_score,
                        2
                    )

            },


            "physical": {

                "wmata_stop_records":
                    records,

                "score":
                    round(
                        physical_score,
                        2
                    )

            },


            "amenity_gap": {

                "bench": amenity_features(bench_status),

                "shelter": amenity_features(shelter_status),

                "score":
                    amenity_gap_score

            }

        }


        scored.append(
            (
                physical_stop_id,
                opportunity_score,
                factors
            )
        )



    scored.sort(
        key=lambda x: x[1],
        reverse=True
    )


    rank = 1


    for stop_id, score, factors in scored:

        cursor.execute(
            """
            INSERT INTO improvement_opportunities
            (
                physical_stop_id,
                opportunity_score,
                priority_rank,
                factors
            )

            VALUES (?, ?, ?, ?)

            """,

            (
                stop_id,
                round(
                    score,
                    2
                ),
                rank,
                json.dumps(
                    factors
                )
            )
        )


        rank += 1



    conn.commit()

    conn.close()


    print(
        f"Created {len(scored):,} improvement opportunities"
    )



if __name__ == "__main__":

    score_opportunities()
