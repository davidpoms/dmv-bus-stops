import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

columns = [
    ("bench_back", "TEXT"),
    ("bench_hostile_features", "TEXT"),
    ("rider_comfort_category", "TEXT"),
]

for col, dtype in columns:
    try:
        cur.execute(
            f"ALTER TABLE stop_observations ADD COLUMN {col} {dtype}"
        )
        print("Added", col)
    except sqlite3.OperationalError:
        print("Already exists:", col)

conn.commit()
conn.close()

print("Observation bench fields ready.")
