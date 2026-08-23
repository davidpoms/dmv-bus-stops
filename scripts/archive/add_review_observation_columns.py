import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

columns = [
    ("bench_type", "TEXT"),
    ("bench_condition", "TEXT"),
    ("shelter_type", "TEXT"),
    ("rider_comfort_category", "TEXT"),
    ("accessibility_status", "TEXT"),
    ("reviewer_relationship", "TEXT"),
]

existing = {
    row[1]
    for row in cur.execute(
        "PRAGMA table_info(stop_observations)"
    ).fetchall()
}

for name, dtype in columns:
    if name not in existing:
        print("Adding", name)
        cur.execute(
            f"""
            ALTER TABLE stop_observations
            ADD COLUMN {name} {dtype}
            """
        )
    else:
        print("Already exists:", name)

conn.commit()
conn.close()

print("Review observation schema updated.")