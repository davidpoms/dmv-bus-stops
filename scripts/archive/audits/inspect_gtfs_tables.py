import sqlite3

db="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(db)
conn.row_factory=sqlite3.Row
cur=conn.cursor()

print("=== TABLES WITH GTFS-LOOKING NAMES ===")

tables = cur.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name
""")

for t in tables:
    name=t["name"]
    if "gtfs" in name.lower() or "stop" in name.lower() or "route" in name.lower():
        print(name)


print("\n=== TABLE SIZES ===")

for name in [
    "gtfs_stop_map",
    "stop_routes",
    "routes",
    "bus_stops"
]:
    try:
        count=cur.execute(
            f"SELECT COUNT(*) FROM {name}"
        ).fetchone()[0]
        print(name,count)
    except:
        pass


conn.close()