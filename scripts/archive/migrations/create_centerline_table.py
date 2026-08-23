import sqlite3
from pathlib import Path

db = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(db)

conn.execute("""
CREATE TABLE IF NOT EXISTS road_centerlines (

    id INTEGER PRIMARY KEY,

    source TEXT,

    road_name TEXT,

    road_class TEXT,

    speed_limit INTEGER,

    lanes INTEGER,

    geometry TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")

conn.commit()
conn.close()

print("Created road_centerlines")
