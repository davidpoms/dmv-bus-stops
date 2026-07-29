from pathlib import Path
import sqlite3
import json


BASE_DIR = Path(__file__).resolve().parents[1]

DB = (
    BASE_DIR
    /
    "src"
    /
    "database"
    /
    "dmv_bus_stops.db"
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


    updated = []


    for row in rows:

        record_id = row[0]
        factors = json.loads(row[1])
        opportunity_score = row[2]


        demand_score = (
            factors
            .get("route_exposure", {})
            .get("score",0)
        )


        amenity = factors.get(
            "amenity_evidence",
            {}
        )


        uncertainty = 0


        # Missing OSM evidence should increase verification need
        if amenity.get("bench_status") == "osm_absent":
            uncertainty += 25

        if amenity.get("shelter_status") == "osm_absent":
            uncertainty += 25


        # Consensus reduces uncertainty
        if amenity.get("bench_status") == "confirmed":
            uncertainty -= 25

        if amenity.get("shelter_status") == "confirmed":
            uncertainty -= 25


        uncertainty = max(
            0,
            min(
                uncertainty,
                50
            )
        )


        verification_priority = (
            demand_score * 0.70
            +
            uncertainty * 0.60
        )


        factors["verification_priority"] = {
            "score": round(
                verification_priority,
                2
            ),
            "demand_component": round(
                demand_score,
                2
            ),
            "uncertainty_component": round(
                uncertainty,
                2
            )
        }


        updated.append(
            (
                json.dumps(factors),
                record_id
            )
        )


    cursor.executemany(
        """
        UPDATE improvement_opportunities

        SET factors = ?

        WHERE id = ?;
        """,
        updated
    )


    conn.commit()

    print(
        f"Updated verification priorities for {len(updated):,} stops"
    )


    conn.close()


if __name__ == "__main__":
    main()
