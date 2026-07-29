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
            io.physical_stop_id,
            io.opportunity_score,
            io.factors,

            COALESCE(ose.osm_bench,-1),
            COALESCE(ose.osm_shelter,-1),

            COALESCE(sc.has_bench,-1),
            COALESCE(sc.has_shelter,-1)

        FROM improvement_opportunities io

        LEFT JOIN stop_osm_evidence ose
        ON ose.stop_id = io.physical_stop_id

        LEFT JOIN stop_consensus sc
        ON sc.stop_id = io.physical_stop_id;
        """
    ).fetchall()


    for row in rows:

        (
            stop_id,
            opportunity,
            factors_json,
            osm_bench,
            osm_shelter,
            consensus_bench,
            consensus_shelter
        ) = row


        factors = json.loads(factors_json)


        verification = 0


        # Bench verification logic
        if consensus_bench == 1:
            bench_status = "confirmed_present"

        elif consensus_bench == 0:
            bench_status = "confirmed_absent"
            verification += 25

        elif osm_bench == 1:
            bench_status = "osm_present"
            verification += 5

        elif osm_bench == 0:
            bench_status = "osm_absent"
            verification += 20

        else:
            bench_status = "unknown"
            verification += 15



        # Shelter verification logic
        if consensus_shelter == 1:
            shelter_status = "confirmed_present"

        elif consensus_shelter == 0:
            shelter_status = "confirmed_absent"
            verification += 25

        elif osm_shelter == 1:
            shelter_status = "osm_present"
            verification += 5

        elif osm_shelter == 0:
            shelter_status = "osm_absent"
            verification += 20

        else:
            shelter_status = "unknown"
            verification += 15



        factors["amenity_evidence"] = {

            "bench_status":
                bench_status,

            "shelter_status":
                shelter_status,

            "verification_score":
                verification

        }


        # combine rider importance with evidence uncertainty
        verification_priority = (

            opportunity * 0.75

            +

            verification * 0.25

        )


        factors["verification_priority"] = {

            "score":
                round(
                    verification_priority,
                    2
                )

        }


        cursor.execute(
            """
            UPDATE improvement_opportunities

            SET factors = ?

            WHERE physical_stop_id = ?

            """,
            (
                json.dumps(factors),
                stop_id
            )
        )


    conn.commit()
    conn.close()


    print(
        "Added evidence confidence scoring."
    )


if __name__ == "__main__":
    main()
