import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

DB = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)


conn = sqlite3.connect(DB)

cur = conn.cursor()


cur.execute(
    """
    CREATE TABLE IF NOT EXISTS community_reviewer_routes (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        reviewer_id INTEGER NOT NULL,

        route_id TEXT NOT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(
            reviewer_id,
            route_id
        )

    )
    """
)


conn.commit()
conn.close()


print(
    "Created community_reviewer_routes table"
)