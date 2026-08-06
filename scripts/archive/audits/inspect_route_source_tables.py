import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("\n=== TABLES WITH ROUTE-LIKE COLUMNS ===")

tables = cur.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name
""").fetchall()

for t in tables:
    name = t["name"]

    cols = cur.execute(
        f"PRAGMA table_info({name})"
    ).fetchall()

    colnames = [c["name"] for c in cols]

    if any(
        "route" in c.lower()
        or "trip" in c.lower()
        for c in colnames
    ):
        print("\nTABLE:", name)
        print(colnames)


print("\n=== STOP ROUTES SAMPLE ===")

for r in cur.execute("""
SELECT *
FROM stop_routes
LIMIT 5
"""):
    print(dict(r))