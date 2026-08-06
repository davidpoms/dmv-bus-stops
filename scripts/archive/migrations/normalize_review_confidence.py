"""
Normalize stop_observations.confidence values.

Converts historical categorical confidence values into numeric scores.
"""

import sqlite3


DB = "src/database/dmv_bus_stops.db"


MAPPING = {
    "high": 1.0,
    "excellent": 1.0,
    "good": 0.8,
    "medium": 0.5,
    "moderate": 0.5,
    "fair": 0.4,
    "low": 0.25,
    "poor": 0.2,
    "unknown": 0.0,
    "": 0.0,
}


conn = sqlite3.connect(DB)
cur = conn.cursor()


rows = cur.execute(
    """
    SELECT id, confidence
    FROM stop_observations
    WHERE typeof(confidence)='text'
    """
).fetchall()


updated = 0


for row_id, value in rows:

    if value is None:
        continue

    numeric = MAPPING.get(
        str(value).lower(),
        0.0
    )

    cur.execute(
        """
        UPDATE stop_observations
        SET confidence=?
        WHERE id=?
        """,
        (
            numeric,
            row_id
        )
    )

    updated += 1


conn.commit()
conn.close()


print(
    f"Normalized {updated} confidence values"
)
