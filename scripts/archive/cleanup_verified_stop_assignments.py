from pathlib import Path
import sqlite3


DB = (
    Path(__file__).resolve()
    .parents[1]
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)


conn = sqlite3.connect(DB)

cur = conn.cursor()


rows = cur.execute(
    """
    SELECT
        sra.id,
        sra.stop_id,
        sc.consensus_status

    FROM stop_review_assignments sra

    JOIN stop_consensus sc
        ON sc.stop_id = sra.stop_id

    WHERE
        sra.status='assigned'
        AND sc.consensus_status='verified'
    """
).fetchall()


print(
    f"Found {len(rows)} stale assignments"
)


for row in rows:

    cur.execute(
        """
        UPDATE stop_review_assignments

        SET
            status='completed',
            completed_at=CURRENT_TIMESTAMP

        WHERE id=?
        """,
        (
            row[0],
        )
    )


conn.commit()

conn.close()


print(
    "✓ Cleaned verified stop assignments"
)
