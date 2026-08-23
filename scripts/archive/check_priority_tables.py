import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

c = conn.cursor()

for table in [
    "stop_priority_snapshots",
    "improvement_opportunities",
    "opportunity_assessments"
]:

    print("\nTABLE:", table)

    try:
        print(
            c.execute(
                f"select count(*) from {table}"
            ).fetchone()
        )

        print(
            c.execute(
                f"select * from {table} limit 2"
            ).fetchall()
        )

    except Exception as e:
        print(e)