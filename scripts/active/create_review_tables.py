import sqlite3
from pathlib import Path

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()


cur.execute("""
CREATE TABLE IF NOT EXISTS community_reviewers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reviewer_key TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")


cur.execute("""
CREATE TABLE IF NOT EXISTS stop_review_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stop_id INTEGER NOT NULL,
    reviewer_id INTEGER NOT NULL,
    scenario TEXT NOT NULL,
    status TEXT DEFAULT 'assigned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
)
""")


cur.execute("""
CREATE INDEX IF NOT EXISTS idx_review_assignments_stop
ON stop_review_assignments(stop_id)
""")


cur.execute("""
CREATE INDEX IF NOT EXISTS idx_review_assignments_reviewer
ON stop_review_assignments(reviewer_id)
""")


conn.commit()
conn.close()

print("Review tables created.")