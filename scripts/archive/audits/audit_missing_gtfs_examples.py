import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()


print("=== MISSING BUS STOP EXAMPLES ===")

cur.execute("""
SELECT
    b.id,
    b.external_stop_id,
    b.latitude,
    b.longitude
FROM bus_stops b
LEFT JOIN gtfs_stop_map g
    ON g.bus_stop_id = b.id
WHERE g.bus_stop_id IS NULL
LIMIT 20
""")

missing = cur.fetchall()

for r in missing:
    print(dict(r))


print("\n=== LOOK FOR WMATA IDS ===")

for r in missing[:5]:

    ext = r["external_stop_id"]

    print("\nBUS STOP:", ext)

    cur.execute("""
    SELECT *
    FROM gtfs_stop_map g
    JOIN bus_stops b
        ON b.id = g.bus_stop_id
    WHERE b.external_stop_id LIKE ?
    """, ("%"+ext+"%",))

    for x in cur.fetchall():
        print(dict(x))


conn.close()