from pathlib import Path
import sqlite3

DB = Path("src/database/dmv_bus_stops.db")

print(f"Database: {DB}")
print(f"Exists: {DB.exists()}")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("\n=== Review Tables ===")

tables = conn.execute("""
SELECT name 
FROM sqlite_master 
WHERE type='table'
AND name LIKE '%review%';
""").fetchall()

for t in tables:
    print("-", t["name"])


for table in [
    "review_queue",
    "stop_review_assignments",
    "stop_observations",
    "stop_reviews"
]:
    print(f"\n=== {table} ===")

    try:
        count = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print("Rows:", count)

        rows = conn.execute(
            f"SELECT * FROM {table} LIMIT 3"
        ).fetchall()

        for row in rows:
            print(dict(row))

    except Exception as e:
        print("ERROR:", e)


conn.close()
