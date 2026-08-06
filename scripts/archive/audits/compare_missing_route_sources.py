import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

tables = [
    "stop_routes_backup",
    "stop_routes_bad_key_backup",
    "stop_routes_failed_rebuild_backup",
    "stop_routes_invalid_key_backup",
]

missing = c.execute("""
SELECT ste.stop_id, ste.route_count
FROM stop_transit_evidence ste
LEFT JOIN stop_routes sr
    ON ste.stop_id = sr.stop_id
WHERE ste.route_count > 0
GROUP BY ste.stop_id
HAVING COUNT(sr.route_id)=0
""").fetchall()

print("Missing stops:", len(missing))

results = []

for stop in missing:
    stop_id = stop["stop_id"]
    expected = stop["route_count"]

    row = {
        "stop_id": stop_id,
        "expected": expected
    }

    for table in tables:
        count = c.execute(
            f"""
            SELECT COUNT(*)
            FROM {table}
            WHERE stop_id=?
            """,
            (stop_id,)
        ).fetchone()[0]

        row[table] = count

    results.append(row)


for r in results[:50]:
    print(r)


print("\n=== SUMMARY ===")

for table in tables:
    total = sum(
        1 for r in results
        if r[table] > 0
    )
    print(table, total)

conn.close()