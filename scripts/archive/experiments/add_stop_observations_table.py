import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS stop_observations (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    stop_id INTEGER NOT NULL,

    reviewer_id INTEGER,

    source TEXT NOT NULL,

    observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    bench_present BOOLEAN,

    shelter_present BOOLEAN,

    waiting_area_type TEXT,

    concrete_pad_present BOOLEAN,

    bench_location_feasible BOOLEAN,

    sun_exposure TEXT,

    accessibility_notes TEXT,

    notes TEXT,

    confidence REAL,

    FOREIGN KEY(stop_id)
        REFERENCES physical_stops(id),

    FOREIGN KEY(reviewer_id)
        REFERENCES community_reviewers(id)

)
""")

conn.commit()
conn.close()

print("Created stop_observations table")
