import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
c = conn.cursor()

for table in [
    "stop_routes",
    "routes",
    "ridership_snapshots",
    "stop_priority_snapshots"
]:

    print("\nTABLE:", table)

    rows = c.execute(
        f"PRAGMA table_info({table});"
    ).fetchall()

    for row in rows:
        print(row)