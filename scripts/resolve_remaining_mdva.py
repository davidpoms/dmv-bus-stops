import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()


# Fix physical_stops remaining ambiguous record(s)
cur.execute("""
UPDATE physical_stops
SET state='MD'
WHERE state='MD/VA'
AND id IN (
    SELECT ps.id
    FROM physical_stops ps
    JOIN stop_jurisdiction sj
        ON ps.id = sj.stop_id
    WHERE sj.county IN (
        'Anne Arundel',
        'Montgomery',
        'Prince George''s'
    )
)
""")


# Resolve stop_jurisdiction MD/VA values
cur.execute("""
UPDATE stop_jurisdiction
SET state='MD'
WHERE state='MD/VA'
AND county IN (
    'Anne Arundel',
    'Montgomery',
    'Prince George''s'
)
""")


cur.execute("""
UPDATE stop_jurisdiction
SET state='VA'
WHERE state='MD/VA'
AND county IN (
    'Arlington',
    'Fairfax',
    'Alexandria',
    'Falls Church',
    'Loudoun'
)
""")


conn.commit()


print("physical_stops:")
for row in cur.execute("""
SELECT state, COUNT(*)
FROM physical_stops
GROUP BY state
ORDER BY state
"""):
    print(row)


print("\nstop_jurisdiction:")
for row in cur.execute("""
SELECT state, COUNT(*)
FROM stop_jurisdiction
GROUP BY state
ORDER BY state
"""):
    print(row)


print("\nRemaining MD/VA:")
for table in ["physical_stops", "stop_jurisdiction"]:
    result = cur.execute(
        f"SELECT COUNT(*) FROM {table} WHERE state='MD/VA'"
    ).fetchone()[0]
    print(table, result)


conn.close()