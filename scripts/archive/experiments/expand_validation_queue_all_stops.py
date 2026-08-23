import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

before = cur.execute("""
    SELECT COUNT(*)
    FROM stop_validation
""").fetchone()[0]

cur.execute("""
INSERT OR IGNORE INTO stop_validation (physical_stop_id)
SELECT id
FROM physical_stops
""")

conn.commit()

after = cur.execute("""
    SELECT COUNT(*)
    FROM stop_validation
""").fetchone()[0]

validated = cur.execute("""
    SELECT COUNT(*)
    FROM stop_validation
    WHERE status='validated'
""").fetchone()[0]

pending = cur.execute("""
    SELECT COUNT(*)
    FROM stop_validation
    WHERE status='needs_validation'
""").fetchone()[0]

conn.close()

print(f"Queue before: {before}")
print(f"Queue after: {after}")
print(f"Validated: {validated}")
print(f"Needs validation: {pending}")
