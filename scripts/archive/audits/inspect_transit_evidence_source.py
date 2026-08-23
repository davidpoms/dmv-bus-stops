import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== TRANSIT EVIDENCE SOURCE ===")

rows = c.execute("""
SELECT
    ste.stop_id,
    ste.route_count,
    ste.source
FROM stop_transit_evidence ste
WHERE ste.stop_id IN (
    245,248,515,1374,1618,2446,
    3376,3866,3897,3997,
    4967,5580,6442,6557,
    6641,7318
)
ORDER BY ste.stop_id
""").fetchall()

for r in rows:
    print(dict(r))


print("\n=== TABLES WITH ROUTE COUNTS ===")

tables = c.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
""").fetchall()

for t in tables:
    name=t["name"]

    cols=c.execute(
        f"PRAGMA table_info({name})"
    ).fetchall()

    names=[x["name"] for x in cols]

    if any(
        "route" in x.lower()
        or "trip" in x.lower()
        for x in names
    ):
        print(name, names)


conn.close()