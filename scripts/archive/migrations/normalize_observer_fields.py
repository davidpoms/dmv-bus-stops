"""
Normalize legacy observer values.

Moves legacy observer categories into review_mode
when review_mode is empty.
"""

import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)
cur = conn.cursor()


updated = cur.execute(
    """
    UPDATE stop_observations
    SET review_mode = observer
    WHERE
        (review_mode IS NULL OR review_mode = '')
        AND observer IN (
            'rider',
            'nearby',
            'reviewer'
        )
    """
)


conn.commit()

conn.close()


print(
    f"Moved {updated.rowcount} legacy observer values into review_mode"
)
