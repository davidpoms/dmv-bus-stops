import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

rows = cur.execute("""
SELECT COUNT(*) AS missing
FROM gtfs_stop_map gsm
LEFT JOIN stop_routes sr
    ON sr.stop_id = gsm.bus_stop_id
WHERE sr.stop_id IS NULL
""").fetchone()

print("GTFS mapped bus stops missing routes:")
print(rows["missing"])


rows = cur.execute("""
SELECT
    gsm.bus_stop_id,
    gsm.gtfs_stop_id
FROM gtfs_stop_map gsm
LEFT JOIN stop_routes sr
    ON sr.stop_id = gsm.bus_stop_id
WHERE sr.stop_id IS NULL
LIMIT 20
""").fetchall()

print("\nSamples:")
for r in rows:
    print(dict(r))