"""
Create project status history tracking.
"""

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    /
    "src"
    /
    "database"
    /
    "dmv_bus_stops.db"
)


def create_history():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS project_status_history (

            id INTEGER PRIMARY KEY,

            physical_stop_id INTEGER NOT NULL,

            recommendation_type TEXT NOT NULL,

            old_status TEXT,

            new_status TEXT NOT NULL,

            changed_by TEXT,

            change_reason TEXT,

            changed_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


    conn.commit()

    conn.close()


    print(
        "Created project status history table"
    )


if __name__ == "__main__":

    create_history()
