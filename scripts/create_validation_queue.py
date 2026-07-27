import sqlite3
import csv
from pathlib import Path


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

OUTPUT = (
    BASE_DIR
    /
    "validation_queue.csv"
)


def main():

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT

            io.physical_stop_id,

            io.opportunity_score,

            json_extract(
                io.factors,
                '$.verification_priority.score'
            )
            AS verification_priority,

            json_extract(
                io.factors,
                '$.amenity_gap.osm_bench'
            )
            AS osm_bench,

            json_extract(
                io.factors,
                '$.amenity_gap.osm_shelter'
            )
            AS osm_shelter,

            ps.latitude,

            ps.longitude,

            ps.primary_name


        FROM improvement_opportunities io


        JOIN physical_stops ps

        ON ps.id = io.physical_stop_id


        LEFT JOIN stop_consensus sc

        ON sc.stop_id = io.physical_stop_id


        WHERE

            json_extract(
                io.factors,
                '$.verification_priority.score'
            ) >= 80


        AND

            COALESCE(
                sc.confidence,
                0
            ) < 1


        ORDER BY

            verification_priority DESC;

        """
    ).fetchall()


    conn.close()


    with open(
        OUTPUT,
        "w",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "stop_id",
                "name",
                "latitude",
                "longitude",
                "opportunity_score",
                "verification_priority",
                "osm_bench",
                "osm_shelter",
                "review_task"
            ]
        )


        writer.writeheader()


        for row in rows:

            writer.writerow(
                {
                    "stop_id":
                        row["physical_stop_id"],

                    "name":
                        row["primary_name"],

                    "latitude":
                        row["latitude"],

                    "longitude":
                        row["longitude"],

                    "opportunity_score":
                        row["opportunity_score"],

                    "verification_priority":
                        row["verification_priority"],

                    "osm_bench":
                        row["osm_bench"],

                    "osm_shelter":
                        row["osm_shelter"],

                    "review_task":
                        "Verify bench and shelter amenities"
                }
            )


    print(
        f"Created validation queue: {len(rows):,} stops"
    )

    print(
        OUTPUT
    )


if __name__ == "__main__":
    main()
