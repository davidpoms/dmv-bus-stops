import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

rows = c.execute("""
SELECT
    b.stop_id,
    b.route_id AS route_name,
    r.id AS route_pk
FROM stop_routes_bad_key_backup b
JOIN routes r
    ON r.route_id = b.route_id
LEFT JOIN stop_routes sr
    ON sr.stop_id = b.stop_id
    AND sr.route_id = r.id
WHERE sr.id IS NULL
""").fetchall()

print("Rows recoverable:", len(rows))

stops = {r["stop_id"] for r in rows}
print("Stops affected:", len(stops))

print("\nSample recoveries:")
for r in rows[:30]:
    print(dict(r))


missing_routes = c.execute("""
SELECT DISTINCT b.route_id
FROM stop_routes_bad_key_backup b
LEFT JOIN routes r
    ON r.route_id = b.route_id
WHERE r.id IS NULL
""").fetchall()

print("\nBackup route names missing from routes table:")
print(len(missing_routes))

for r in missing_routes[:20]:
    print(r[0])