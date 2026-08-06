import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

print("=== PHYSICAL MEMBERS ===")
print(
    c.execute("""
        SELECT *
        FROM physical_stop_members
        WHERE physical_stop_id = 173
    """).fetchall()
)

print()

print("=== ROUTES FOR BUS STOP 174 ===")
print(
    c.execute("""
        SELECT *
        FROM stop_routes
        WHERE stop_id = 174
    """).fetchall()
)

print()

print("=== TRANSIT EVIDENCE ===")
print(
    c.execute("""
        SELECT *
        FROM stop_transit_evidence
        WHERE stop_id = 174
    """).fetchall()
)

conn.close()