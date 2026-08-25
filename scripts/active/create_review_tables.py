import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB = Path(os.environ.get(
    "DMV_BUS_STOPS_DB",
    BASE_DIR / "src" / "database" / "dmv_bus_stops.db",
))

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
    campaign TEXT,
    status TEXT DEFAULT 'assigned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
)
""")

assignment_columns = {
    row[1] for row in cur.execute("PRAGMA table_info(stop_review_assignments)")
}
if "campaign" not in assignment_columns:
    cur.execute("ALTER TABLE stop_review_assignments ADD COLUMN campaign TEXT")


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
