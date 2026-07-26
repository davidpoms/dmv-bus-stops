import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
INSERT INTO stop_observations
(
    physical_stop_id,
    observer,
    shelter_present,
    bench_present,
    bench_feasible,
    notes
)

SELECT

    stop_id,

    COALESCE(
        CAST(reviewer_id AS TEXT),
        CAST(user_id AS TEXT),
        anonymous_email,
        'anonymous'
    ),

    CASE
        WHEN has_shelter = 1 THEN 'yes'
        WHEN has_shelter = 0 THEN 'no'
        ELSE NULL
    END,

    CASE
        WHEN has_bench = 1 THEN 'yes'
        WHEN has_bench = 0 THEN 'no'
        ELSE NULL
    END,

    CASE
        WHEN bench_location_feasible = 1 THEN 'yes'
        WHEN bench_location_feasible = 0 THEN 'no'
        ELSE NULL
    END,

    notes

FROM stop_reviews

WHERE NOT EXISTS (

    SELECT 1
    FROM stop_observations o

    WHERE o.physical_stop_id = stop_reviews.stop_id
    AND o.observer =
        COALESCE(
            CAST(reviewer_id AS TEXT),
            CAST(user_id AS TEXT),
            anonymous_email,
            'anonymous'
        )

)

""")

conn.commit()

print("Observations created:", cur.rowcount)

conn.close()
