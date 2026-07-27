import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
cur = conn.cursor()

columns = [
    row[1]
    for row in cur.execute(
        "PRAGMA table_info(stop_observations)"
    )
]

if "reviewer_relationship" not in columns:
    cur.execute(
        """
        ALTER TABLE stop_observations
        ADD COLUMN reviewer_relationship TEXT
        """
    )
    print("Added reviewer_relationship column")
else:
    print("Column already exists")

conn.commit()
conn.close()
