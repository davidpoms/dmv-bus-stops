from pathlib import Path
import sqlite3
import json


DB = Path(
    "src/database/dmv_bus_stops.db"
)


def evidence_score(status):

    if status == "osm_present":
        return 0

    if status == "osm_absent":
        return 20

    if status == "consensus_present":
        return -30

    return 10



def main():

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()


    rows = cursor.execute(
        """
        SELECT
            id,
            factors
        FROM improvement_opportunities;
        """
    ).fetchall()


    updated = 0


    for row in rows:

        row_id, factors_json = row

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


        uncertainty = (

            evidence_score(
                bench_status
            )

            +

            evidence_score(
                shelter_status
            )

        )


        demand = factors.get(
            "route_exposure",
            {}
        ).get(
            "score",
            0
        )


        opportunity = factors.get(
            "route_exposure",
            {}
        ).get(
            "score",
            0
        )


        verification_score = (

            demand * 0.75

            +

            uncertainty * 1.25

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

            "bench_status":
                bench_status,

            "shelter_status":
                shelter_status

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
        f"Updated {updated:,} verification scores"
    )



if __name__ == "__main__":
    main()
