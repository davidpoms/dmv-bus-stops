import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)

count = conn.execute(
    """
    SELECT COUNT(*)
    FROM review_queue rq
    JOIN stop_routes sr
        ON sr.stop_id = rq.physical_stop_id
    WHERE rq.review_status = 'pending'
    AND rq.community_review_available = 1
    """
).fetchone()

print("Eligible route matches:", count[0])

count2 = conn.execute(
    """
    SELECT COUNT(*)
    FROM review_queue rq
    JOIN stop_routes sr
        ON sr.stop_id = rq.physical_stop_id
    WHERE rq.review_status = 'pending'
    AND rq.community_review_available = 1
    AND rq.physical_stop_id NOT IN (
        SELECT stop_id
        FROM stop_review_assignments
        WHERE status='assigned'
    )
    """
).fetchone()

print("Available after reviewer exclusion:", count2[0])

conn.close()