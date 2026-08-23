import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()


# Resolve MD/VA based on jurisdiction fields
cur.execute("""
UPDATE physical_stops
SET state =
    CASE
        WHEN id IN (
            SELECT stop_id
            FROM stop_jurisdiction
            WHERE state = 'MD/VA'
            AND county IN (
                'Arlington',
                'Fairfax',
                'Alexandria',
                'Falls Church',
                'Loudoun'
            )
        )
        THEN 'VA'

        WHEN id IN (
            SELECT stop_id
            FROM stop_jurisdiction
            WHERE state = 'MD/VA'
            AND county IN (
                'Montgomery',
                'Prince George''s'
            )
        )
        THEN 'MD'

        ELSE state
    END
WHERE state = 'MD/VA';
""")


conn.commit()


print("Updated:", cur.rowcount)


print("\nNew physical state counts:")
for row in cur.execute("""
SELECT state, COUNT(*)
FROM physical_stops
GROUP BY state
ORDER BY state;
"""):
    print(row)


print("\nRemaining MD/VA:")
for row in cur.execute("""
SELECT COUNT(*)
FROM physical_stops
WHERE state='MD/VA';
"""):
    print(row[0])


conn.close()