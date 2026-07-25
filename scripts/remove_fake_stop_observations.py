import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

before = cur.execute("""
    SELECT COUNT(*)
    FROM stop_observations
""").fetchone()[0]

cur.execute("""
DELETE FROM stop_observations
""")

conn.commit()

after = cur.execute("""
    SELECT COUNT(*)
    FROM stop_observations
""").fetchone()[0]

conn.close()

print(f"Observations before: {before}")
print(f"Observations after: {after}")
