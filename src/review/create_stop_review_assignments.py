"""
Create volunteer assignments from review_queue.

Temporary demo assignment layer.
Uses existing community_reviewers table.
"""

from pathlib import Path
import sqlite3


DATABASE_PATH = (
    Path(__file__).resolve()
    .parents[1]
    / "database"
    / "dmv_bus_stops.db"
)


def create_assignments():

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("Creating stop review assignments...")

    reviewers = cur.execute("""
        SELECT id
        FROM community_reviewers
        ORDER BY id
    """).fetchall()

    if not reviewers:
        raise Exception("No reviewers found")


    tasks = cur.execute("""
        SELECT physical_stop_id
        FROM review_queue
        WHERE review_status = 'pending'
        ORDER BY priority_rank
    """).fetchall()


    created = 0
    skipped = 0


    for i, task in enumerate(tasks):

        reviewer = reviewers[i % len(reviewers)]

        try:
            cur.execute("""
                INSERT INTO stop_review_assignments
                (
                    stop_id,
                    reviewer_id,
                    status
                )
                VALUES (?, ?, 'assigned')
            """,
            (
                task["physical_stop_id"],
                reviewer["id"]
            ))

            created += 1

        except sqlite3.IntegrityError:
            skipped += 1


    conn.commit()


    total = cur.execute("""
        SELECT COUNT(*)
        FROM stop_review_assignments
    """).fetchone()[0]


    conn.close()

    print(f"Created: {created:,}")
    print(f"Already existed: {skipped:,}")
    print(f"Total assignments: {total:,}")


if __name__ == "__main__":
    create_assignments()
