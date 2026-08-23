import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
cur = conn.cursor()

print("Direct:")
print(cur.execute("""
SELECT COUNT(*)
FROM stop_priority_snapshots
WHERE stop_id IN (
    SELECT physical_stop_id
    FROM stop_wmata_evidence
    WHERE wmata_status='PRS'
)
""").fetchone())

print("Through physical members:")
print(cur.execute("""
SELECT COUNT(*)
FROM stop_priority_snapshots s
JOIN physical_stop_members pm
    ON pm.bus_stop_id = s.stop_id
JOIN stop_wmata_evidence w
    ON w.physical_stop_id = pm.physical_stop_id
WHERE w.wmata_status='PRS'
""").fetchone())

conn.close()