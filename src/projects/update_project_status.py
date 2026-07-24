"""
Update improvement project lifecycle status
and record status history.
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


VALID_STATUSES = [
    "identified",
    "review_pending",
    "approved",
    "funded",
    "completed"
]


def update_status(
    physical_stop_id,
    recommendation_type,
    new_status,
    changed_by="system",
    reason=None
):

    if new_status not in VALID_STATUSES:

        raise ValueError(
            f"Invalid status: {new_status}"
        )


    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT project_status

        FROM improvement_projects

        WHERE physical_stop_id = ?

        AND recommendation_type = ?;

        """,
        (
            physical_stop_id,
            recommendation_type
        )
    )


    row = cursor.fetchone()


    if not row:

        raise ValueError(
            "Project not found"
        )


    old_status = row[0]


    cursor.execute(
        """
        UPDATE improvement_projects

        SET project_status = ?

        WHERE physical_stop_id = ?

        AND recommendation_type = ?;

        """,
        (
            new_status,
            physical_stop_id,
            recommendation_type
        )
    )


    cursor.execute(
        """
        INSERT INTO project_status_history
        (
            physical_stop_id,
            recommendation_type,
            old_status,
            new_status,
            changed_by,
            change_reason
        )

        VALUES (?, ?, ?, ?, ?, ?);

        """,
        (
            physical_stop_id,
            recommendation_type,
            old_status,
            new_status,
            changed_by,
            reason
        )
    )


    conn.commit()

    conn.close()


    print(
        f"{recommendation_type}: {old_status} → {new_status}"
    )


if __name__ == "__main__":

    update_status(
        5478,
        "bench_installation",
        "approved",
        "demo_volunteer",
        "Field review confirmed improvement opportunity"
    )
