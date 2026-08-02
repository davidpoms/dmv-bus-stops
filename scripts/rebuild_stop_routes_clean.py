import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

print("Existing rows:")
print(
    c.execute(
        "SELECT COUNT(*) FROM stop_routes"
    ).fetchone()[0]
)

c.execute("""
DELETE FROM stop_routes
""")


c.execute("""
INSERT INTO stop_routes
(
    stop_id,
    route_id
)

SELECT DISTINCT
    gm.bus_stop_id,
    sr.route_id

FROM stop_routes_backup sr

JOIN gtfs_stop_map gm
    ON CAST(sr.stop_id AS TEXT)
       = gm.gtfs_stop_id
""")


conn.commit()


print(
    "New rows:",
    c.execute(
        "SELECT COUNT(*) FROM stop_routes"
    ).fetchone()[0]
)


conn.close()

print("done")