import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
cur = conn.cursor()

print("Queue count:")
print(cur.execute("""
SELECT COUNT(*)
FROM review_queue
""").fetchone())

print("\nNon-PRS latest statuses:")
print(cur.execute("""
WITH latest_wmata AS (
    SELECT
        w1.physical_stop_id,
        w1.wmata_status
    FROM stop_wmata_evidence w1
    WHERE w1.id = (
        SELECT MAX(w2.id)
        FROM stop_wmata_evidence w2
        WHERE w2.physical_stop_id = w1.physical_stop_id
    )
)

SELECT
    w.wmata_status,
    COUNT(*)

FROM review_queue rq

JOIN latest_wmata w
    ON rq.physical_stop_id = w.physical_stop_id

GROUP BY w.wmata_status;
""").fetchall())

print("\nMissing latest WMATA:")
print(cur.execute("""
WITH latest_wmata AS (
    SELECT
        w1.physical_stop_id,
        w1.wmata_status
    FROM stop_wmata_evidence w1
    WHERE w1.id = (
        SELECT MAX(w2.id)
        FROM stop_wmata_evidence w2
        WHERE w2.physical_stop_id = w1.physical_stop_id
    )
)

SELECT COUNT(*)

FROM review_queue rq

LEFT JOIN latest_wmata w
    ON rq.physical_stop_id = w.physical_stop_id

WHERE w.physical_stop_id IS NULL;
""").fetchone())