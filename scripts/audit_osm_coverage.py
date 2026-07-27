import sqlite3
from pathlib import Path


DB = Path(
    "src/database/dmv_bus_stops.db"
)


def main():

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()


    print("\n=== OSM Coverage Summary ===")

    rows = cursor.execute(
        """
        SELECT
            COUNT(*) total,
            SUM(osm_bench) benches,
            SUM(osm_shelter) shelters
        FROM stop_osm_evidence;
        """
    ).fetchone()

    print(dict(rows))


    print("\n=== Highest Demand Stops With No OSM Amenities ===")

    rows = cursor.execute(
        """
        SELECT
            ia.physical_stop_id,
            ROUND(
                ia.combined_route_weekday_boardings,
                0
            ) boardings,
            ia.routes_served,
            ose.osm_bench,
            ose.osm_shelter

        FROM opportunity_assessments ia

        LEFT JOIN stop_osm_evidence ose
            ON ose.stop_id = ia.physical_stop_id

        WHERE
            COALESCE(ose.osm_bench,0)=0
            AND
            COALESCE(ose.osm_shelter,0)=0

        ORDER BY
            ia.combined_route_weekday_boardings DESC

        LIMIT 50;
        """
    )


    for r in rows:
        print(dict(r))


    print("\n=== Stops With OSM Amenities ===")

    rows = cursor.execute(
        """
        SELECT
            stop_id,
            osm_bench,
            osm_shelter,
            osm_tags

        FROM stop_osm_evidence

        WHERE
            osm_bench=1
            OR osm_shelter=1

        LIMIT 25;
        """
    )


    for r in rows:
        print(dict(r))


if __name__ == "__main__":
    main()
