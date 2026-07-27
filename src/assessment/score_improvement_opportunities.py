"""
Score physical bus stop improvement opportunities.

Creates a review priority ranking based on:

- passenger demand
- route connectivity
- missing rider amenities

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

    """
    Log normalization prevents extreme outliers
    from crushing all other scores.
    """

    if not value or maximum == 0:
        return 0


    return (
        math.log1p(value)
        /
        math.log1p(maximum)
    ) * 100



def calculate_amenity_gap(
    osm_bench,
    osm_shelter,
    consensus_bench,
    consensus_shelter
):

    """
    Higher score means greater missing amenity need.
    """

    score = 0


    # Bench evidence
    if (
        not osm_bench
        and consensus_bench != 1
    ):
        score += 50


    # Shelter evidence
    if (
        not osm_shelter
        and consensus_shelter != 1
    ):
        score += 50


    return score



def score_opportunities():

    conn = sqlite3.connect(
        DATABASE_PATH
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

            oa.combined_route_weekday_boardings,

            oa.highest_route_weekday_boardings,

            oa.routes_served,

            oa.wmata_stop_records,

            COALESCE(ose.osm_bench,0),

            COALESCE(ose.osm_shelter,0),

            COALESCE(sc.has_bench,NULL),

            COALESCE(sc.has_shelter,NULL)


        FROM opportunity_assessments oa


        LEFT JOIN stop_osm_evidence ose

            ON ose.stop_id = oa.physical_stop_id


        LEFT JOIN stop_consensus sc

            ON sc.stop_id = oa.physical_stop_id;

        """
    )


    rows = cursor.fetchall()


    if not rows:

        print(
            "No assessments found."
        )

        return



    max_daily = max(
        row[1]
        for row in rows
    )


    max_routes = max(
        row[3]
        for row in rows
    )


    max_records = max(
        row[4]
        for row in rows
    )



    scored = []



    for row in rows:


        (
            physical_stop_id,

            total_daily,

            highest_route,

            routes,

            records,

            osm_bench,

            osm_shelter,

            consensus_bench,

            consensus_shelter

        ) = row



        route_exposure_score = normalize(
            total_daily,
            max_daily
        )


        connectivity_score = normalize(
            routes,
            max_routes
        )


        physical_score = normalize(
            records,
            max_records
        )


        amenity_gap_score = calculate_amenity_gap(
            osm_bench,
            osm_shelter,
            consensus_bench,
            consensus_shelter
        )



        # Rider exposure is the primary driver.
        # Amenity gaps refine priorities but should not dominate
        # because missing OSM data is common.

        #
        # Opportunity score:
        # Measures where improvements matter most.
        #
        # Rider exposure dominates.
        # Amenity uncertainty is a smaller modifier.
        #

        opportunity_score = (

            route_exposure_score * 0.65

            +

            connectivity_score * 0.20

            +

            amenity_gap_score * 0.15

        )


        #
        # Verification priority:
        # Determines where volunteers should review stops.
        #
        # High ridership + incomplete amenity evidence
        # gets prioritized.
        #

        verification_priority_score = (

            route_exposure_score * 0.50

            +

            amenity_gap_score * 0.50

        )


        factors = {

            "verification_priority": {

                "score":
                    round(
                        verification_priority_score,
                        2
                    ),

                "reason":
                    "High rider exposure combined with incomplete amenity evidence"

            },



            "route_exposure": {

                "combined_route_weekday_boardings":
                    round(total_daily,2),

                "highest_route_weekday_boardings":
                    round(highest_route,2),

                "score":
                    round(route_exposure_score,2)

            },


            "network": {

                "routes_served":
                    routes,

                "score":
                    round(connectivity_score,2)

            },


            "physical": {

                "wmata_stop_records":
                    records,

                "score":
                    round(physical_score,2)

            },


            "amenity_gap": {

                "osm_bench":
                    bool(osm_bench),

                "osm_shelter":
                    bool(osm_shelter),

                "consensus_bench":
                    consensus_bench,

                "consensus_shelter":
                    consensus_shelter,

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



    for rank, item in enumerate(
        scored,
        start=1
    ):


        cursor.execute(
            """
            INSERT INTO improvement_opportunities

            (

                physical_stop_id,

                opportunity_score,

                priority_rank,

                factors

            )

            VALUES (?, ?, ?, ?);

            """,

            (

                item[0],

                round(
                    item[1],
                    2
                ),

                rank,

                json.dumps(
                    item[2]
                )

            )
        )



    conn.commit()


    conn.close()



    print(
        f"Scored {len(scored):,} physical stops"
    )


    print(
        "Top 10 opportunities:"
    )


    for item in scored[:10]:

        print(
            item[0],
            round(item[1],2)
        )



if __name__ == "__main__":

    score_opportunities()

