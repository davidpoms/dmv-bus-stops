"""
Complete volunteer stop review records.

Takes reviewed observations and stores them in stop_reviews.
This layer captures field validation only.
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


def complete_stop_review(
    stop_id,
    reviewer_id,
    has_shelter,
    has_bench,
    bench_condition,
    waiting_area_type,
    notes
):

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM stop_reviews

        WHERE stop_id = ?
        AND reviewer_id = ?;
        """,
        (
            stop_id,
            reviewer_id
        )
    )


    cursor.execute(
        """
        INSERT INTO stop_reviews
        (
            stop_id,
            reviewer_id,
            has_shelter,
            has_bench,
            bench_condition,
            waiting_area_type,
            notes
        )

        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (
            stop_id,
            reviewer_id,
            has_shelter,
            has_bench,
            bench_condition,
            waiting_area_type,
            notes
        )
    )

    conn.commit()
    conn.close()

    print(
        f"Saved review for stop {stop_id}"
    )


if __name__ == "__main__":

    complete_stop_review(
        stop_id=5478,
        reviewer_id="demo_volunteer",
        has_shelter=False,
        has_bench=False,
        bench_condition="none",
        waiting_area_type="sidewalk",
        notes="High ridership stop with no existing seating."
    )
