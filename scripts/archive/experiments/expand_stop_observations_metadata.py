import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

columns = [
    ("source", "TEXT DEFAULT 'unknown'"),
    ("reviewer_id", "INTEGER"),
    ("confidence", "REAL"),
    ("streetview_checked", "BOOLEAN"),
    ("osm_checked", "BOOLEAN")
]

for name, definition in columns:
    try:
        cur.execute(
            f"""
            ALTER TABLE stop_observations
            ADD COLUMN {name} {definition}
            """
        )
        print("Added", name)

    except sqlite3.OperationalError:
        print("Already exists:", name)


conn.commit()
conn.close()
