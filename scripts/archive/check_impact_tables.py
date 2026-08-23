import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")

for table in [
    "improvement_opportunities",
    "improvement_recommendations",
    "opportunity_assessments",
    "stop_priority_snapshots"
]:
    print("\nTABLE:", table)
    try:
        for row in conn.execute(f"PRAGMA table_info({table})"):
            print(row)
    except Exception as e:
        print(e)

conn.close()