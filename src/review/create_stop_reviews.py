"""
Validate stop review workflow tables.

The stop_reviews table already stores volunteer field observations.
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


def create_stop_reviews():

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_stop_reviews_stop
        ON stop_reviews(
            stop_id
        );
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_stop_reviews_date
        ON stop_reviews(
            review_date
        );
        """
    )

    conn.commit()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM stop_reviews;
        """
    )

    count = cursor.fetchone()[0]

    conn.close()

    print(
        f"stop_reviews ready ({count} existing reviews)"
    )


if __name__ == "__main__":
    create_stop_reviews()
