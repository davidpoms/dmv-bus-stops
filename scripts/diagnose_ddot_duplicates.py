import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row


rows = conn.execute("""
SELECT
    physical_stop_id,
    COUNT(*) AS count
FROM stop_amenity_evidence
WHERE source='DDOT'
AND amenity_type='shelter'
GROUP BY physical_stop_id
HAVING COUNT(*) > 1
ORDER BY count DESC
""").fetchall()


print("Duplicate physical stops:")
print(len(rows))

for r in rows[:20]:
    print(dict(r))


conn.close()