import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("TABLE CHECK")
print(
    c.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    AND name='gtfs_stop_map'
    """).fetchall()
)

print("\nCOUNT")
print(
    c.execute(
        "SELECT COUNT(*) FROM gtfs_stop_map"
    ).fetchone()[0]
)

print("\nSAMPLES")
for row in c.execute("""
    SELECT *
    FROM gtfs_stop_map
    LIMIT 10
"""):
    print(dict(row))

conn.close()