import sqlite3
from pathlib import Path

db = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(db)

conn.execute("""
CREATE TABLE IF NOT EXISTS community_actions (

    id INTEGER PRIMARY KEY,

    physical_stop_id INTEGER NOT NULL,

    status TEXT NOT NULL DEFAULT 'none',

    project_type TEXT,

    steward TEXT,

    installed_date TEXT,

    notes TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (physical_stop_id)
        REFERENCES physical_stops(id)
);
""")

conn.commit()
conn.close()

print("community_actions table created")
