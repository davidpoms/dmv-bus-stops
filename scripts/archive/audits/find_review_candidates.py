import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    """
    SELECT
        stop_id,
        osm_bench,
        osm_shelter,
        osm_tags

    FROM stop_osm_evidence

    WHERE osm_bus_stop = 1
      AND osm_bench = 0
      AND osm_shelter = 0

    LIMIT 10
    """
).fetchall()

for r in rows:
    print(
        r["stop_id"],
        "bench:",
        r["osm_bench"],
        "shelter:",
        r["osm_shelter"]
    )
    print(r["osm_tags"][:200])
    print("---")

conn.close()
