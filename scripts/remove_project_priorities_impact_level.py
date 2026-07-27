import sqlite3
from pathlib import Path


DB = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)


conn = sqlite3.connect(DB)
cursor = conn.cursor()


cursor.execute("""
PRAGMA table_info(project_priorities);
""")

columns = [
    row[1]
    for row in cursor.fetchall()
]


if "impact_level" in columns:

    cursor.execute("""
        ALTER TABLE project_priorities
        RENAME TO project_priorities_old;
    """)


    cursor.execute("""
        CREATE TABLE project_priorities (

            id INTEGER PRIMARY KEY,

            physical_stop_id INTEGER NOT NULL,

            recommendation_type TEXT NOT NULL,

            location_name TEXT,

            opportunity_score REAL,

            priority_level TEXT,

            priority_rank INTEGER,

            justification TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        );
    """)


    cursor.execute("""
        INSERT INTO project_priorities
        (
            id,
            physical_stop_id,
            recommendation_type,
            location_name,
            opportunity_score,
            priority_level,
            priority_rank,
            justification,
            created_at
        )

        SELECT
            id,
            physical_stop_id,
            recommendation_type,
            location_name,
            opportunity_score,
            COALESCE(priority_level, impact_level),
            priority_rank,
            justification,
            created_at

        FROM project_priorities_old;
    """)


    cursor.execute("""
        DROP TABLE project_priorities_old;
    """)


    print("Removed impact_level from project_priorities")

else:

    print("impact_level already removed")


conn.commit()
conn.close()
