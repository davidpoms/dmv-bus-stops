import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)

conn.execute("""
CREATE TABLE IF NOT EXISTS community_stewardships (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    reviewer_id INTEGER NOT NULL,

    stop_id INTEGER NOT NULL,

    status TEXT DEFAULT 'active',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(reviewer_id, stop_id),

    FOREIGN KEY(reviewer_id)
        REFERENCES community_reviewers(id)

)
""")

conn.commit()

print("Created community_stewardships")