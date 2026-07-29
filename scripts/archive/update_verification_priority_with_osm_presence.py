from pathlib import Path
import sqlite3
import json


DB = Path(
    "src/database/dmv_bus_stops.db"
)


def main():

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()


    rows = cursor.execute(
        """
        SELECT
            id,
            factors,
            opportunity_score
        FROM improvement_opportunities;
        """
    ).fetchall()


    updated = 0


    for row in rows:

        (
            row_id,
            factors_json,
            opportunity_score

        ) = row


        factors = json.loads(
            factors_json
        )


        amenity = factors.get(
            "amenity_evidence",
            {}
        )


        bench_status = amenity.get(
            "bench_status",
            "unknown"
        )

        shelter_status = amenity.get(
            "shelter_status",
            "unknown"
        )


        #
        # Evidence uncertainty
        #

        uncertainty = 0


        if bench_status == "osm_absent":
            uncertainty += 25

        elif bench_status == "osm_present":
            uncertainty -= 25


        if shelter_status == "osm_absent":
            uncertainty += 25

        elif shelter_status == "osm_present":
            uncertainty -= 25



        #
        # Demand component
        #

        demand = factors.get(
            "route_exposure",
            {}
        ).get(
            "score",
            0
        )


        #
        # Final verification priority
        #
        # High demand + uncertain evidence
        # = best field validation targets
        #

        verification_score = (

            demand * 0.70

            +

            uncertainty * 0.60

        )


        verification_score = max(
            0,
            min(
                100,
                verification_score
            )
        )


        factors[
            "verification_priority"
        ] = {

            "score":
                round(
                    verification_score,
                    2
                ),

            "uncertainty_component":
                uncertainty,

            "reason":

                "High demand with uncertain amenity evidence"

        }


        cursor.execute(
            """
            UPDATE improvement_opportunities

            SET factors = ?

            WHERE id = ?

            """,
            (
                json.dumps(factors),
                row_id
            )
        )


        updated += 1



    conn.commit()

    print(
        f"Updated verification priorities for {updated:,} stops"
    )



if __name__ == "__main__":
    main()
