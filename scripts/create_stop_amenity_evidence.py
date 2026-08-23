import sqlite3
from pathlib import Path

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)

conn.execute("""
CREATE TABLE IF NOT EXISTS stop_amenity_evidence (

    id INTEGER PRIMARY KEY,

    physical_stop_id INTEGER,

    source TEXT,

    source_record_id TEXT,

    amenity_type TEXT,

    present INTEGER,

    confidence TEXT,

    match_distance_m REAL,

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")

conn.commit()

print("Created stop_amenity_evidence")

conn.close()