"""
Rebuild stop consensus from stop_observations.

Consensus requires:
- completed assignments
- unique reviewers
- real observations
"""


import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)
cur = conn.cursor()


cur.execute(
    """
    DELETE FROM stop_consensus;
    """
)


stops = cur.execute(
    """
    SELECT
        a.stop_id

    FROM stop_review_assignments a

    JOIN stop_observations o
        ON o.physical_stop_id = a.stop_id
        AND o.reviewer_id = a.reviewer_id

    WHERE a.status='completed'

    GROUP BY a.stop_id

    HAVING COUNT(
        DISTINCT a.reviewer_id
    ) >= 3

    """
).fetchall()


created = 0


for (stop_id,) in stops:


    rows = cur.execute(
        """
        SELECT

            bench_present,
            bench_feasible,
            ada_clearance_possible,
            confidence

        FROM stop_observations

        WHERE physical_stop_id=?

        AND reviewer_id IS NOT NULL

        """,
        (stop_id,)
    ).fetchall()


    if not rows:
        continue


    reviewer_count = len(
        set(
            cur.execute(
                """
                SELECT DISTINCT reviewer_id

                FROM stop_observations

                WHERE physical_stop_id=?

                AND reviewer_id IS NOT NULL
                """,
                (stop_id,)
            ).fetchall()
        )
    )


    bench_yes = sum(
        1 for r in rows
        if r[0] in ("yes","1",1,True,"true","full_bench")
    )


    feasible_yes = sum(
        1 for r in rows
        if r[1] in ("yes","1",1,True,"true","good")
    )


    ada_yes = sum(
        1 for r in rows
        if r[2] in ("yes","1",1,True,"true","good")
    )


    confidences = [
        r[3]
        for r in rows
        if isinstance(r[3], (int,float))
    ]


    confidence = (
        sum(confidences)/len(confidences)
        if confidences
        else 0.0
    )


    cur.execute(
        """
        INSERT INTO stop_consensus
        (
            stop_id,
            reviewer_count,
            has_bench,
            bench_feasible,
            ada_accessible,
            confidence,
            consensus_status
        )

        VALUES
        (?,?,?,?,?,?,?)

        """,
        (
            stop_id,
            reviewer_count,
            bench_yes >= reviewer_count/2,
            feasible_yes >= reviewer_count/2,
            ada_yes >= reviewer_count/2,
            confidence,
            "verified"
        )
    )


    created += 1


conn.commit()
conn.close()


print(
    f"Consensus records created: {created}"
)
