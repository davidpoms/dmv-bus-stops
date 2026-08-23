import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

print("RIDERSHIP COLUMNS")

for row in conn.execute(
    "pragma table_info(ridership_snapshots)"
):
    print(row)


print("\nSAMPLE ROW")

print(
    conn.execute(
        "select * from ridership_snapshots limit 3"
    ).fetchall()
)

conn.close()