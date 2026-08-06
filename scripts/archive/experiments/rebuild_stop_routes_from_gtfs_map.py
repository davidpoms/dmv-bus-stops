import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

print("Existing stop_routes:")
print(
    c.execute(
        "SELECT COUNT(*) FROM stop_routes"
    ).fetchone()[0]
)


print("Backing up current stop_routes...")

c.execute("""
CREATE TABLE IF NOT EXISTS stop_routes_before_gtfs_map_rebuild
AS
SELECT * FROM stop_routes
""")


print("Clearing stop_routes...")

c.execute("""
DELETE FROM stop_routes
""")


print("Rebuilding stop_routes through gtfs_stop_map...")


c.execute("""
INSERT OR IGNORE INTO stop_routes
(
    stop_id,
    route_id
)

SELECT DISTINCT
    gm.bus_stop_id,
    r.id

FROM stop_routes_backup sr

JOIN gtfs_stop_map gm
    ON CAST(sr.stop_id AS TEXT)
       = gm.gtfs_stop_id

JOIN routes r
    ON r.route_id = sr.route_id
""")


print(
    "Inserted:",
    c.rowcount
)


conn.commit()


print("\nNew stop_routes:")
print(
    c.execute(
        "SELECT COUNT(*) FROM stop_routes"
    ).fetchone()[0]
)


conn.close()

print("done")