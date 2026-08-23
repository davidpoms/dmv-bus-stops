import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()


rows = cur.execute(
    """
    SELECT
        ps.id,
        ps.primary_name,
        aw.wmata_stop_id,
        ps.latitude,
        ps.longitude
    FROM active_wmata_evidence aw

    JOIN physical_stops ps
        ON ps.id = aw.physical_stop_id

    LEFT JOIN physical_stop_members psm
        ON ps.id = psm.physical_stop_id

    LEFT JOIN bus_stops bs
        ON psm.bus_stop_id = bs.id

    LEFT JOIN stop_routes sr
        ON bs.id = sr.stop_id

    GROUP BY ps.id

    HAVING COUNT(sr.stop_id)=0

    ORDER BY ps.latitude DESC
    """
).fetchall()


print("Active WMATA stops missing routes:", len(rows))

for r in rows[:50]:
    print(dict(r))