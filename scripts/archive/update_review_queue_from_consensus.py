import sqlite3
from pathlib import Path


DB = Path(
    "src/database/dmv_bus_stops.db"
)


conn = sqlite3.connect(DB)
cur = conn.cursor()


verified = cur.execute(
    """
    SELECT
        stop_id,
        bench_feasible,
        confidence
    FROM stop_consensus
    WHERE
        consensus_status='verified'
    """
).fetchall()


print(
    "Verified stops:",
    len(verified)
)


for stop_id, bench_feasible, confidence in verified:

    cur.execute(
        """
        UPDATE review_queue

        SET
            review_status='resolved'

        WHERE physical_stop_id=?
        """,
        (
            stop_id,
        )
    )


conn.commit()


print(
    "Updated queue entries:",
    cur.rowcount
)


conn.close()


print(
    "✓ Review queue synchronized with consensus"
)
