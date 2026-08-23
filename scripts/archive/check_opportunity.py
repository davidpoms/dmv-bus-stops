import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

print("IMPROVEMENT OPPORTUNITIES")

for row in conn.execute(
    "pragma table_info(improvement_opportunities)"
):
    print(row)

print("\nSAMPLE")

print(
    conn.execute(
        "select * from improvement_opportunities limit 3"
    ).fetchall()
)

conn.close()