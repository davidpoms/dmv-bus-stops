import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

checks = [
    ("bus_stops", "SELECT COUNT(*) FROM bus_stops"),
    ("physical_stops", "SELECT COUNT(*) FROM physical_stops"),
    ("gtfs_stop_map", "SELECT COUNT(*) FROM gtfs_stop_map"),
    ("stop_routes", "SELECT COUNT(*) FROM stop_routes"),
    ("routes", "SELECT COUNT(*) FROM routes"),
    ("stop_transit_evidence", "SELECT COUNT(*) FROM stop_transit_evidence"),
    ("gtfs_orphan_route_audit", "SELECT COUNT(*) FROM gtfs_orphan_route_audit"),
]

print("TRANSIT DATA SNAPSHOT")
print("====================")

for name, query in checks:
    print(
        f"{name}:",
        c.execute(query).fetchone()[0]
    )

print("\nActive route links:")
print(
    c.execute("""
        SELECT COUNT(*)
        FROM stop_routes sr
        JOIN routes r
        ON r.id = sr.route_id
    """).fetchone()[0]
)

print("\nGTFS stops without routes:")
print(
    c.execute("""
        SELECT COUNT(*)
        FROM stop_transit_evidence
        WHERE gtfs_bus_stop=1
        AND route_count=0
    """).fetchone()[0]
)

conn.close()