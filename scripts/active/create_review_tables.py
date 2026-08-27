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

reviewer_columns = {
    row[1] for row in cur.execute("PRAGMA table_info(community_reviewers)")
}
for column, declaration in (
    ("display_name", "TEXT"), ("profile_token", "TEXT"), ("email", "TEXT"),
    ("profile_created_at", "TIMESTAMP"),
    ("email_verified_at", "TIMESTAMP"), ("claimed_at", "TIMESTAMP"),
    ("role", "TEXT NOT NULL DEFAULT 'reviewer'"),
):
    if column not in reviewer_columns:
        cur.execute(f"ALTER TABLE community_reviewers ADD COLUMN {column} {declaration}")

cur.execute("DROP TRIGGER IF EXISTS community_reviewers_role_insert")
cur.execute("DROP TRIGGER IF EXISTS community_reviewers_role_update")
cur.execute("""CREATE TRIGGER community_reviewers_role_insert
BEFORE INSERT ON community_reviewers
WHEN NEW.role IS NULL OR NEW.role NOT IN ('reviewer','review_lead','owner')
BEGIN
    SELECT RAISE(ABORT, 'invalid community reviewer role');
END""")
cur.execute("""CREATE TRIGGER community_reviewers_role_update
BEFORE UPDATE OF role ON community_reviewers
WHEN NEW.role IS NULL OR NEW.role NOT IN ('reviewer','review_lead','owner')
BEGIN
    SELECT RAISE(ABORT, 'invalid community reviewer role');
END""")
invalid_roles = cur.execute(
    "SELECT COUNT(*) FROM community_reviewers "
    "WHERE role NOT IN ('reviewer','review_lead','owner') OR role IS NULL"
).fetchone()[0]
if invalid_roles:
    raise RuntimeError(
        f"community_reviewers contains {invalid_roles} invalid role value(s)"
    )

cur.execute("""CREATE TABLE IF NOT EXISTS pilot_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL CHECK (category IN (
        'confusing','stop_location','review_question','broken','other'
    )),
    message TEXT NOT NULL,
    physical_stop_id INTEGER,
    page_path TEXT,
    reviewer_id INTEGER,
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(physical_stop_id) REFERENCES physical_stops(id),
    FOREIGN KEY(reviewer_id) REFERENCES community_reviewers(id)
)""")
cur.execute("""CREATE INDEX IF NOT EXISTS idx_pilot_feedback_submitted
ON pilot_feedback(submitted_at DESC)""")

cur.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_community_reviewers_verified_email
ON community_reviewers(email) WHERE email_verified_at IS NOT NULL""")
cur.execute("""CREATE TABLE IF NOT EXISTS reviewer_login_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reviewer_id INTEGER NOT NULL,
    normalized_email TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    action TEXT NOT NULL CHECK (action IN ('claim','login','conflict')),
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(reviewer_id) REFERENCES community_reviewers(id)
)""")
cur.execute("""CREATE INDEX IF NOT EXISTS idx_reviewer_login_tokens_hash
ON reviewer_login_tokens(token_hash)""")
cur.execute("""CREATE TABLE IF NOT EXISTS reviewer_auth_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_key TEXT NOT NULL,
    source_key TEXT NOT NULL,
    outcome TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
)""")
cur.execute("""CREATE INDEX IF NOT EXISTS idx_reviewer_auth_attempts_email_time
ON reviewer_auth_attempts(email_key, created_at)""")
cur.execute("""CREATE INDEX IF NOT EXISTS idx_reviewer_auth_attempts_source_time
ON reviewer_auth_attempts(source_key, created_at)""")


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


observation_table = cur.execute(
    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='stop_observations'"
).fetchone()
if observation_table:
    observation_columns = {
        row[1] for row in cur.execute("PRAGMA table_info(stop_observations)")
    }
    for column, declaration in (
        (
            "assignment_id",
            "INTEGER REFERENCES stop_review_assignments(id)",
        ),
        ("weather_exposure", "TEXT"),
        ("riders_avoid_facilities", "TEXT"),
    ):
        if column not in observation_columns:
            cur.execute(
                f"ALTER TABLE stop_observations ADD COLUMN {column} {declaration}"
            )


cur.execute("""
CREATE INDEX IF NOT EXISTS idx_review_assignments_stop
ON stop_review_assignments(stop_id)
""")


cur.execute("""
CREATE INDEX IF NOT EXISTS idx_review_assignments_reviewer
ON stop_review_assignments(reviewer_id)
""")


if observation_table:
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_stop_observations_assignment
    ON stop_observations(assignment_id)
    """)


conn.commit()
conn.close()

print("Review tables created.")
