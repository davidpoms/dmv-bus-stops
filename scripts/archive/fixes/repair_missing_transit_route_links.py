import sqlite3
from pathlib import Path
from datetime import datetime

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

backup = DB.with_name(
    f"dmv_bus_stops_before_transit_route_repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
)

print("Creating backup:", backup)
conn.commit()

# sqlite backup
dest = sqlite3.connect(backup)
conn.backup(dest)
dest.close()

print("\nBefore repair:")
print(
    c.execute(
        "SELECT COUNT(*) FROM stop_routes"
    ).fetchone()[0]
)


print("\nRecovering missing stop_routes from backups...")

# Recover routes where backup has GTFS route codes
c.execute(
"""
INSERT OR IGNORE INTO stop_routes(stop_id, route_id)
SELECT
    s.stop_id,
    r.id
FROM stop_routes_backup s
JOIN routes r
    ON r.route_id = CAST(s.route_id AS TEXT)
LEFT JOIN stop_routes existing
    ON existing.stop_id = s.stop_id
    AND existing.route_id = r.id
WHERE existing.id IS NULL
"""
)

backup_added = c.rowcount
print("Recovered from stop_routes_backup:", backup_added)


c.execute(
"""
INSERT OR IGNORE INTO stop_routes(stop_id, route_id)
SELECT
    s.stop_id,
    r.id
FROM stop_routes_failed_rebuild_backup s
JOIN routes r
    ON r.route_id = CAST(s.route_id AS TEXT)
LEFT JOIN stop_routes existing
    ON existing.stop_id = s.stop_id
    AND existing.route_id = r.id
WHERE existing.id IS NULL
"""
)

failed_added = c.rowcount
print("Recovered from failed rebuild backup:", failed_added)


print("\nChecking transit evidence gaps...")

rows = c.execute(
"""
SELECT
    ste.stop_id,
    ste.route_count,
    COUNT(sr.id) AS current_routes
FROM stop_transit_evidence ste
LEFT JOIN stop_routes sr
    ON sr.stop_id = ste.stop_id
WHERE ste.gtfs_bus_stop = 1
GROUP BY ste.stop_id
HAVING current_routes = 0
"""
).fetchall()


print("Remaining GTFS stops without routes:", len(rows))

for row in rows[:20]:
    print(dict(row))


conn.commit()


print("\nAfter repair:")
print(
    c.execute(
        "SELECT COUNT(*) FROM stop_routes"
    ).fetchone()[0]
)

conn.close()

print("\nRepair complete.")