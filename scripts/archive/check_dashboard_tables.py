import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

c = conn.cursor()

rows = c.execute(
    """
    SELECT name, type
    FROM sqlite_master
    WHERE type IN ('table','view')
    ORDER BY type,name;
    """
).fetchall()


for row in rows:
    print(row)