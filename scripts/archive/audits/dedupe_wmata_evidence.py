import sqlite3


DB="src/database/dmv_bus_stops.db"


conn=sqlite3.connect(DB)


conn.execute(
"""
DELETE FROM stop_wmata_evidence
WHERE id NOT IN
(
    SELECT id
    FROM
    (
        SELECT
            id,
            ROW_NUMBER() OVER
            (
                PARTITION BY physical_stop_id
                ORDER BY match_distance_m
            ) AS rn

        FROM stop_wmata_evidence
    )

    WHERE rn=1
)
"""
)


conn.commit()

print(
    "Removed duplicate WMATA matches"
)


conn.close()
