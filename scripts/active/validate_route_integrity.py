import sqlite3

db="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(db)
conn.row_factory=sqlite3.Row
cur=conn.cursor()

print("stop_routes total")
print(cur.execute("""
SELECT COUNT(*) FROM stop_routes
""").fetchone()[0])


print("\nstop_routes without matching routes")

print(cur.execute("""
SELECT COUNT(*)
FROM stop_routes sr
LEFT JOIN routes r
ON sr.route_id=r.id
WHERE r.id IS NULL
""").fetchone()[0])


print("\nphysical stops with routes")

print(cur.execute("""
SELECT COUNT(DISTINCT ps.id)
FROM physical_stops ps
JOIN physical_stop_members psm
ON ps.id=psm.physical_stop_id
JOIN stop_routes sr
ON psm.bus_stop_id=sr.stop_id
""").fetchone()[0])


print("\nphysical stops total")

print(cur.execute("""
SELECT COUNT(*) FROM physical_stops
""").fetchone()[0])