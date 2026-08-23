import sqlite3
from pathlib import Path


DB = Path(
    "src/database/dmv_bus_stops.db"
)


conn = sqlite3.connect(DB)
cur = conn.cursor()


rows = cur.execute(
    """
    SELECT
        stop_id,
        bench_feasible,
        confidence,
        reviewer_count,
        consensus_status

    FROM stop_consensus
    """
).fetchall()


updated = 0


for (
    stop_id,
    bench_feasible,
    confidence,
    reviewer_count,
    consensus_status
) in rows:


    if consensus_status == "verified":

        if bench_feasible:

            status = "resolved"

            reason = (
                "Consensus confirms "
                "bench installation feasible"
            )

        else:

            status = "resolved"

            reason = (
                "Consensus confirms "
                "bench installation not feasible"
            )


    else:

        status = "pending"

        reason = None


    cur.execute(
        """
        UPDATE review_queue

        SET
            review_status=?,
            consensus_status=?,
            resolution_reason=?,
            verification_needed=?,
            community_review_available=?

        WHERE physical_stop_id=?
        """,
        (
            status,
            consensus_status,
            reason,
            0 if consensus_status == "verified" else 1,
            1,
            stop_id
        )
    )


    updated += cur.rowcount


conn.commit()
conn.close()


print(
    "Updated rows:",
    updated
)

print(
    "✓ Synced consensus state"
)
