import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS community_reviewers (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    reviewer_key TEXT UNIQUE NOT NULL,

    display_name TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS stop_review_assignments (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    stop_id INTEGER NOT NULL,

    reviewer_id INTEGER NOT NULL,

    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    completed_at TIMESTAMP,

    status TEXT DEFAULT 'assigned',

    FOREIGN KEY(stop_id)
        REFERENCES physical_stops(id),

    FOREIGN KEY(reviewer_id)
        REFERENCES community_reviewers(id),

    UNIQUE(stop_id, reviewer_id)

)
""")

conn.commit()

print("Added reviewer workflow tables")

conn.close()
