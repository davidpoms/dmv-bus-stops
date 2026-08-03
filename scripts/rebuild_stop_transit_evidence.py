import sqlite3
from datetime import datetime
from pathlib import Path


DB = Path("src/database/dmv_bus_stops.db")


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()


backup = DB.with_name(
    f"before_transit_evidence_rebuild_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
)

print("Creating backup:", backup)

dest = sqlite3.connect(backup)
conn.backup(dest)
dest.close()



print("\nBefore evidence rows:")
print(
    c.execute(
        "SELECT COUNT(*) FROM stop_transit_evidence"
    ).fetchone()[0]
)



print("\nRebuilding route counts...")


# Preserve existing evidence metadata but refresh route_count
c.execute("""
UPDATE stop_transit_evidence
SET route_count = (
    SELECT COUNT(DISTINCT sr.route_id)
    FROM stop_routes sr
    WHERE sr.stop_id = stop_transit_evidence.stop_id
)
WHERE gtfs_bus_stop = 1
""")


updated = c.rowcount

print("Updated evidence rows:", updated)



print("\nFixing source labels...")


c.execute("""
UPDATE stop_transit_evidence
SET source = 'GTFS stop_routes repaired'
WHERE gtfs_bus_stop = 1
""")


conn.commit()



print("\nAfter:")

print(
    c.execute(
        """
        SELECT COUNT(*)
        FROM stop_transit_evidence
        WHERE gtfs_bus_stop=1
        """
    ).fetchone()[0]
)


print(
    "\nStops with zero routes but GTFS evidence:"
)

rows = c.execute("""
SELECT
    stop_id,
    route_count
FROM stop_transit_evidence
WHERE gtfs_bus_stop=1
AND route_count=0
LIMIT 20
""").fetchall()


for r in rows:
    print(dict(r))


conn.close()

print("\nDone.")