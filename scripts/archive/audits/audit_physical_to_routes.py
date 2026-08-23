import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== PHYSICAL STOP MEMBERS ===")

cur.execute("""
SELECT *
FROM physical_stop_members
LIMIT 5
""")

for r in cur.fetchall():
    print(dict(r))


print("\n=== COUNTS ===")

for table in [
    "physical_stops",
    "physical_stop_members",
    "bus_stops",
    "stop_routes",
    "routes"
]:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    print(table, cur.fetchone()[0])


print("\n=== TEST PHYSICAL STOP 3765 ===")

cur.execute("""
SELECT
    p.id AS physical_stop_id,
    psm.bus_stop_id,
    sr.route_id
FROM physical_stops p
LEFT JOIN physical_stop_members psm
    ON p.id = psm.physical_stop_id
LEFT JOIN stop_routes sr
    ON psm.bus_stop_id = sr.stop_id
WHERE p.id = 3765
""")

for r in cur.fetchall():
    print(dict(r))


conn.close()