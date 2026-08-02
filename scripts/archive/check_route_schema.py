import sqlite3

c = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

print(
    c.execute(
        "pragma table_info(routes)"
    ).fetchall()
)