import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

c = conn.cursor()

print(
    c.execute(
        "pragma table_info(stop_priority_snapshots)"
    ).fetchall()
)