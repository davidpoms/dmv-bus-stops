"""
Validate stop review workflow tables.

The stop_observations table already stores volunteer field observations.
This script ensures required indexes exist.
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


def create_stop_observations():

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_stop_observations_stop
        ON stop_observations(
            physical_stop_id
        );
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_stop_observations_date
        ON stop_observations(
            observed_at
        );
        """
    )

    conn.commit()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM stop_observations;
        """
    )

    count = cursor.fetchone()[0]

    conn.close()

    print(
        f"stop_observations ready ({count} existing reviews)"
    )


if __name__ == "__main__":
    create_stop_observations()
