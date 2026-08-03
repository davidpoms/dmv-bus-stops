import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
cur = conn.cursor()

count = cur.execute(
    """
    SELECT COUNT(*)
    FROM review_queue rq
    JOIN stop_routes sr
        ON sr.stop_id = rq.physical_stop_id
    WHERE sr.route_id = 'A11'
    AND rq.review_status = 'pending'
    AND rq.community_review_available = 1
    """
).fetchone()

print("Eligible A11 review stops:", count[0])

conn.close()