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


# Refresh route counts using the current-GTFS mapping:
#
# physical_stop_members
#     -> gtfs_stop_map
#     -> stop_routes
#
# Stops without current GTFS are not given transit evidence.

c.execute("""
UPDATE stop_transit_evidence
SET route_count = (
    SELECT COUNT(DISTINCT sr.route_id)
    FROM physical_stop_members psm
    JOIN gtfs_stop_map gm
        ON gm.bus_stop_id = psm.bus_stop_id
    JOIN stop_routes sr
        ON sr.stop_id = gm.bus_stop_id
    WHERE psm.physical_stop_id = stop_transit_evidence.stop_id
)
WHERE gtfs_bus_stop = 1
""")


updated = c.rowcount

print("Updated evidence rows:", updated)


print("\nFixing source labels...")


c.execute("""
UPDATE stop_transit_evidence
SET source = 'WMATA current GTFS via gtfs_stop_map'
WHERE gtfs_bus_stop = 1
""")


conn.commit()


print("\nAfter:")

print(
    c.execute(
        """
        SELECT COUNT(*)
        FROM stop_transit_evidence
        WHERE gtfs_bus_stop = 1
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
WHERE gtfs_bus_stop = 1
AND route_count = 0
LIMIT 20
""").fetchall()


for r in rows:
    print(dict(r))


conn.close()


print("\nDone.")