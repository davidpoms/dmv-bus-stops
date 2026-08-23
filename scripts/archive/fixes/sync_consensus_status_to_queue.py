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

    SET consensus_status =
    (
        SELECT consensus_status
        FROM stop_consensus
        WHERE stop_consensus.stop_id =
              review_queue.physical_stop_id
    )

    WHERE physical_stop_id IN
    (
        SELECT stop_id
        FROM stop_consensus
    )
    """
)


print(
    "Updated rows:",
    cur.rowcount
)


conn.commit()
conn.close()


print(
    "✓ Synced consensus status"
)
