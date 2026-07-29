"""
Fill missing stop_observations confidence values.

Historical reviews without explicit confidence
are assigned a neutral confidence score.
"""

import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)
cur = conn.cursor()


result = cur.execute(
    """
    UPDATE stop_observations
    SET confidence = 0.0
    WHERE confidence IS NULL
    """
)


conn.commit()

updated = result.rowcount

conn.close()


print(
    f"Filled {updated} missing confidence values"
)
