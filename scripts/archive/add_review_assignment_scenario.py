import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

columns = [
    row[1]
    for row in cur.execute(
        "PRAGMA table_info(stop_review_assignments)"
    )
]

if "scenario" not in columns:
    cur.execute(
        """
        ALTER TABLE stop_review_assignments
        ADD COLUMN scenario TEXT
        """
    )

conn.commit()
conn.close()

print("Added scenario column")
