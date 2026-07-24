"""
Export pending bus stop review tasks.

Creates a JSON payload suitable for:
- volunteer web interface
- mobile app
- API endpoint
"""

import sqlite3
import json
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

OUTPUT_PATH = (
    BASE_DIR
    /
    "review_tasks.json"
)


def export_review_tasks():

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT

            rq.id,

            rq.physical_stop_id,

            rq.priority_rank,

            rq.opportunity_score,

            rq.location_name,

            rq.review_status,

            rq.review_questions

        FROM review_queue rq

        WHERE rq.review_status = 'pending'

        ORDER BY rq.priority_rank;

        """
    )

    rows = cursor.fetchall()

    tasks = []

    for row in rows:

        tasks.append(
            {
                "review_id": row["id"],
                "physical_stop_id": row["physical_stop_id"],
                "priority_rank": row["priority_rank"],
                "opportunity_score": row["opportunity_score"],
                "location_name": row["location_name"],
                "status": row["review_status"],
                "questions": json.loads(
                    row["review_questions"]
                )
                if row["review_questions"]
                else []
            }
        )

    OUTPUT_PATH.write_text(
        json.dumps(
            tasks,
            indent=2
        )
    )

    conn.close()

    print(
        f"Exported {len(tasks):,} review tasks"
    )

    print(
        f"Saved to {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    export_review_tasks()
