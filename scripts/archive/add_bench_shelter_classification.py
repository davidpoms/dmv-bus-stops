from pathlib import Path
import sqlite3

db = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(db)
cur = conn.cursor()

columns = [
    ("shelter_type", "TEXT"),
    ("bench_type", "TEXT"),
    ("bench_back", "BOOLEAN"),
    ("bench_hostile_features", "BOOLEAN"),
    ("rider_comfort_category", "TEXT"),
]

for col, dtype in columns:
    try:
        cur.execute(
            f"ALTER TABLE stop_validation ADD COLUMN {col} {dtype}"
        )
        print("Added", col)
    except sqlite3.OperationalError:
        print("Already exists:", col)

conn.commit()
conn.close()

print("Bench/shelter classification fields ready")
