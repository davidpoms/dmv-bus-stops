import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
cur = conn.cursor()

tables = cur.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
    """
).fetchall()

print("Tables:")
for t in tables:
    print(t[0])

print("\nJurisdiction tables:")
for t in tables:
    if "jurisdiction" in t[0]:
        print(t[0])

conn.close()