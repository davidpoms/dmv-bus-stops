import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("\n=== TABLES ===")

tables = cur.execute("""
SELECT name 
FROM sqlite_master 
WHERE type='table'
ORDER BY name
""").fetchall()

for t in tables:
    print(t["name"])


print("\n=== WMATA RELATED TABLES ===")

for t in tables:
    name = t["name"]

    if "wmata" in name.lower() or "route" in name.lower():
        print("\nTABLE:", name)

        cols = cur.execute(
            f"PRAGMA table_info({name})"
        ).fetchall()

        for c in cols:
            print(" ", c["name"])


print("\n=== SAMPLE WMATA RECORD ===")

rows = cur.execute("""
SELECT *
FROM stop_wmata_evidence
LIMIT 3
""").fetchall()

for r in rows:
    print(dict(r))


conn.close()