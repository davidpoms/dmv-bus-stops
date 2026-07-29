"""
Remove test review submissions.

Only removes stop_observations created by test accounts.
Does not modify reviewer records because schemas vary.
"""

import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)
cur = conn.cursor()


deleted = cur.execute(
    """
    DELETE FROM stop_observations
    WHERE observer LIKE 'test%'
    """
)


conn.commit()
conn.close()


print(
    f"Deleted {deleted.rowcount} test observations"
)

print(
    "Test observation cleanup complete"
)
