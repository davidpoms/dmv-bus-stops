import sqlite3

DB = "src/database/dmv_bus_stops.db"

tables = [
    "stop_amenity_evidence",
    "stop_routes",
    "routes",
    "physical_stop_members",
    "physical_stops",
    "bus_stops"
]

conn = sqlite3.connect(DB)

for table in tables:
    print("\n================")
    print("TABLE:", table)
    print("================")

    try:
        for row in conn.execute(f"PRAGMA table_info({table})"):
            print(
                row[1],
                row[2]
            )
    except Exception as e:
        print("ERROR:", e)

conn.close()