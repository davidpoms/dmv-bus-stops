import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
c = conn.cursor()


rows = c.execute(
    """
    SELECT
        ps.id,
        sps.stop_id,
        sps.priority_score,
        sps.factors

    FROM physical_stops ps

    JOIN stop_priority_snapshots sps

        ON sps.stop_id = ps.id

    WHERE ps.id IN (2685,2694,2735)

    ORDER BY sps.calculated_date DESC;
    """
).fetchall()


for r in rows:
    print(r)