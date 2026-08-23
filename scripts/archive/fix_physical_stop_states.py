import sqlite3
from pathlib import Path

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Show current mismatch count
cur.execute("""
SELECT COUNT(*)
FROM physical_stops ps
JOIN stop_jurisdiction sj
    ON ps.id = sj.stop_id
WHERE ps.state != sj.state
""")

before = cur.fetchone()[0]

print("Mismatches before:", before)


# Update physical_stops from jurisdiction table
cur.execute("""
UPDATE physical_stops
SET state = (
    SELECT sj.state
    FROM stop_jurisdiction sj
    WHERE sj.stop_id = physical_stops.id
)
WHERE id IN (
    SELECT ps.id
    FROM physical_stops ps
    JOIN stop_jurisdiction sj
        ON ps.id = sj.stop_id
    WHERE ps.state != sj.state
)
""")

print("Rows updated:", cur.rowcount)

conn.commit()


# Verify
cur.execute("""
SELECT state, COUNT(*)
FROM physical_stops
GROUP BY state
ORDER BY state
""")

print("\nphysical_stops after:")
for row in cur.fetchall():
    print(row)


cur.execute("""
SELECT COUNT(*)
FROM physical_stops ps
JOIN stop_jurisdiction sj
    ON ps.id = sj.stop_id
WHERE ps.state != sj.state
""")

print("\nRemaining mismatches:", cur.fetchone()[0])

conn.close()