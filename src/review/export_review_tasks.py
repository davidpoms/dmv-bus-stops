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


def export_review_tasks(database_path=DATABASE_PATH, output_path=OUTPUT_PATH):

    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    columns = {row[1] for row in cursor.execute("PRAGMA table_info(review_queue)")}
    has_priority = "review_priority_score" in columns
    priority_select = (
        "rq.review_priority_score, rq.priority_amenity, "
        "rq.shelter_review_priority, rq.bench_review_priority, "
        "rq.rider_exposure_percentile, rq.priority_reason"
        if has_priority else
        "NULL review_priority_score,NULL priority_amenity,"
        "NULL shelter_review_priority,NULL bench_review_priority,"
        "NULL rider_exposure_percentile,NULL priority_reason"
    )
    order = "rq.review_priority_score DESC, rq.priority_rank" if has_priority else "rq.priority_rank"
    cursor.execute(
        f"""
        SELECT

            rq.id,

            rq.physical_stop_id,

            rq.priority_rank,

            rq.opportunity_score,

            rq.location_name,

            rq.review_status,

            rq.review_questions,
            {priority_select}

        FROM review_queue rq

        JOIN stop_gtfs_status sgs
            ON sgs.physical_stop_id = rq.physical_stop_id
           AND sgs.current_gtfs = 1

        WHERE rq.review_status = 'pending'

        ORDER BY {order};

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
                else [],
                "review_priority_score": row["review_priority_score"],
                "priority_amenity": row["priority_amenity"],
                "shelter_review_priority": row["shelter_review_priority"],
                "bench_review_priority": row["bench_review_priority"],
                "rider_exposure_percentile": row["rider_exposure_percentile"],
                "priority_reason": row["priority_reason"],
            }
        )

    Path(output_path).write_text(
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
        f"Saved to {output_path}"
    )


if __name__ == "__main__":
    export_review_tasks()
