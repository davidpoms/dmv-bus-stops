"""
Migrate stop_improvement_impact terminology:
daily_riders -> daily_route_exposure
impact_level -> priority_level
"""

import sqlite3
from pathlib import Path


DB = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)


def migrate():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("""
        PRAGMA table_info(stop_improvement_impact);
    """)

    columns = {
        row[1]
        for row in cursor.fetchall()
    }

    print("Existing columns:", columns)

    if "daily_route_exposure" not in columns:
        cursor.execute("""
            ALTER TABLE stop_improvement_impact
            ADD COLUMN daily_route_exposure REAL;
        """)

        cursor.execute("""
            UPDATE stop_improvement_impact
            SET daily_route_exposure = daily_riders
            WHERE daily_route_exposure IS NULL;
        """)

        print("Added daily_route_exposure")

    if "priority_level" not in columns:
        cursor.execute("""
            ALTER TABLE stop_improvement_impact
            ADD COLUMN priority_level TEXT;
        """)

        cursor.execute("""
            UPDATE stop_improvement_impact
            SET priority_level = impact_level
            WHERE priority_level IS NULL;
        """)

        print("Added priority_level")

    conn.commit()
    conn.close()

    print("Migration complete.")


if __name__ == "__main__":
    migrate()
