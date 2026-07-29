import sqlite3
from pathlib import Path


DB = Path(
    "src/database/dmv_bus_stops.db"
)


conn = sqlite3.connect(DB)
cur = conn.cursor()


cur.execute(
    """
    UPDATE review_queue

    SET
        verification_needed =
        CASE
            WHEN physical_stop_id IN
            (
                SELECT stop_id
                FROM stop_consensus
                WHERE consensus_status='verified'
            )
            THEN 0

            ELSE 1
        END
    """
)


print(
    "Verification flags updated:",
    cur.rowcount
)


conn.commit()
conn.close()


print(
    "✓ Updated verification priority state"
)
