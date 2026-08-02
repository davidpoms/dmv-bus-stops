import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
c = conn.cursor()

tables = c.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    AND name LIKE '%priority%';
    """
).fetchall()

print("Priority tables:")
for t in tables:
    print(t[0])


for table in tables:
    name = table[0]

    print("\nTABLE:", name)

    rows = c.execute(
        f"PRAGMA table_info({name});"
    ).fetchall()

    for r in rows:
        print(r)