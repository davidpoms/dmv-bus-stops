import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

cur = conn.cursor()

print("Queue summary:")

print(
    cur.execute(
        """
        SELECT
            COUNT(*),
            MIN(priority_rank),
            MAX(priority_rank),
            AVG(opportunity_score)
        FROM review_queue;
        """
    ).fetchone()
)


print("\nTop 10 stops:")

for row in cur.execute(
    """
    SELECT
        priority_rank,
        opportunity_score,
        location_name
    FROM review_queue
    ORDER BY priority_rank
    LIMIT 10;
    """
):
    print(row)


print("\nWMATA status breakdown:")

for row in cur.execute(
    """
    SELECT
        w.wmata_status,
        COUNT(*)
    FROM review_queue rq
    JOIN stop_wmata_evidence w
        ON rq.physical_stop_id = w.physical_stop_id
    GROUP BY w.wmata_status;
    """
):
    print(row)


conn.close()