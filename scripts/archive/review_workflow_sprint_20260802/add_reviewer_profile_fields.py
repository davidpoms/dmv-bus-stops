import sqlite3
from pathlib import Path

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()

columns = [
    ("profile_token", "TEXT"),
    ("email", "TEXT"),
    ("profile_created_at", "TIMESTAMP")
]

existing = {
    row[1]
    for row in cur.execute(
        "PRAGMA table_info(community_reviewers)"
    )
}

for name, dtype in columns:
    if name not in existing:
        cur.execute(
            f"""
            ALTER TABLE community_reviewers
            ADD COLUMN {name} {dtype}
            """
        )

conn.commit()
conn.close()

print("Added reviewer profile fields")