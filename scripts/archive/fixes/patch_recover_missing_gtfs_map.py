import sqlite3
from pathlib import Path
from datetime import datetime

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()


backup = DB.with_name(
    f"before_gtfs_map_repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
)

print("Creating backup:", backup)

dest = sqlite3.connect(backup)
conn.backup(dest)
dest.close()


print("\nMissing GTFS mappings")
print("====================")


rows = c.execute("""
SELECT DISTINCT
    s.stop_id,
    s.route_id
FROM stop_routes_backup s

LEFT JOIN gtfs_stop_map gm
    ON CAST(s.stop_id AS TEXT)=gm.gtfs_stop_id

WHERE gm.gtfs_stop_id IS NULL

ORDER BY s.stop_id
""").fetchall()


print("Missing GTFS stop IDs:", len(rows))


for r in rows[:50]:
    print(dict(r))


print("""
These stops require recovery from:
- WMATA stop codes
- external_stop_id
- spatial matching
""")

conn.close()