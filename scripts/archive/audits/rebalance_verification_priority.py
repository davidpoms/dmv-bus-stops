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
            factors
        FROM improvement_opportunities;
        """
    ).fetchall()


    for row_id, factors_json in rows:

        factors = json.loads(
            factors_json
        )


        demand = factors.get(
            "route_exposure",
            {}
        ).get(
            "score",
            0
        )


        amenity = factors.get(
            "amenity_evidence",
            {}
        )


        uncertainty = 0


        for field in [
            "bench_status",
            "shelter_status"
        ]:

            status = amenity.get(
                field,
                "unknown"
            )


            if status == "osm_absent":
                uncertainty += 20

            elif status == "osm_present":
                uncertainty += 0

            elif status == "consensus_present":
                uncertainty -= 20

            else:
                uncertainty += 10


        verification_score = (
            demand * 0.50
            +
            uncertainty * 0.50
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

            "demand_component":
                round(
                    demand,
                    2
                ),

            "uncertainty_component":
                uncertainty

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


    conn.commit()

    print(
        "Rebalanced verification priorities."
    )


if __name__ == "__main__":
    main()
