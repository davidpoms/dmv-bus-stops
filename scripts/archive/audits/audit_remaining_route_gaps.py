import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

rows = c.execute("""
SELECT
    p.id AS physical_stop_id,
    p.member_count,
    COUNT(DISTINCT psm.bus_stop_id) AS members,
    COUNT(DISTINCT ste.stop_id) AS transit_evidence_members,
    COALESCE(MAX(ste.route_count),0) AS max_route_count
FROM physical_stops p
LEFT JOIN physical_stop_members psm
    ON p.id = psm.physical_stop_id
LEFT JOIN stop_transit_evidence ste
    ON psm.bus_stop_id = ste.stop_id
LEFT JOIN stop_routes sr
    ON psm.bus_stop_id = sr.stop_id
WHERE sr.id IS NULL
GROUP BY p.id
ORDER BY transit_evidence_members DESC, p.id
""").fetchall()

print("Remaining gaps:", len(rows))

print("\n=== WITH TRANSIT EVIDENCE ===")
count = 0
for r in rows:
    if r["transit_evidence_members"]:
        print(dict(r))
        count += 1

print("Count:", count)

print("\n=== WITHOUT TRANSIT EVIDENCE ===")
count = 0
for r in rows:
    if not r["transit_evidence_members"]:
        print(dict(r))
        count += 1

print("Count:", count)