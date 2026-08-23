import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

bad = cur.execute("""
SELECT COUNT(*)
FROM review_queue rq
JOIN stop_wmata_evidence w
ON w.physical_stop_id = rq.physical_stop_id
WHERE w.id = (
    SELECT MAX(w2.id)
    FROM stop_wmata_evidence w2
    WHERE w2.physical_stop_id = w.physical_stop_id
)
AND w.wmata_status != 'PRS'
""").fetchone()[0]

missing = cur.execute("""
SELECT COUNT(*)
FROM review_queue rq
LEFT JOIN stop_wmata_evidence w
ON w.physical_stop_id = rq.physical_stop_id
WHERE w.id IS NULL
""").fetchone()[0]

print("Bad non-PRS queue entries:", bad)
print("Missing WMATA evidence:", missing)

if bad == 0 and missing == 0:
    print("PASS: Review queue contains only active PRS stops")
else:
    print("FAIL: Review queue needs investigation")