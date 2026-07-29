"""
Generate stop improvement recommendations from verified consensus.
"""

import sqlite3
import json


DB = "src/database/dmv_bus_stops.db"


def truthy(value):
    return value in (
        1,
        "1",
        True,
        "true",
        "yes",
        "YES"
    )


conn = sqlite3.connect(DB)
cur = conn.cursor()


rows = cur.execute(
    """
    SELECT
        stop_id,
        reviewer_count,
        has_bench,
        bench_feasible,
        ada_accessible,
        confidence

    FROM stop_consensus

    WHERE consensus_status='verified'
    """
).fetchall()


created = 0


for row in rows:

    (
        stop_id,
        reviewer_count,
        has_bench,
        bench_feasible,
        ada_accessible,
        confidence

    ) = row


    has_bench_bool = truthy(has_bench)
    feasible_bool = truthy(bench_feasible)
    ada_bool = truthy(ada_accessible)


    recommendations = []


    if not has_bench_bool and feasible_bool:

        recommendations.append(
            (
                "install_bench",
                "medium",
                {
                    "reason": "Stop has no bench but location is feasible",
                    "reviewers": reviewer_count
                }
            )
        )


    if not ada_bool:

        recommendations.append(
            (
                "improve_ada_access",
                "high",
                {
                    "reason": "ADA accessibility concern identified",
                    "reviewers": reviewer_count
                }
            )
        )


    for (
        recommendation_type,
        priority,
        evidence

    ) in recommendations:


        cur.execute(
            """
            INSERT INTO improvement_recommendations
            (
                physical_stop_id,
                recommendation_type,
                priority,
                reasons,
                confidence,
                evidence
            )

            VALUES
            (?, ?, ?, ?, ?, ?)

            """,
            (
                stop_id,
                recommendation_type,
                priority,
                json.dumps(evidence),
                str(confidence),
                json.dumps(evidence)
            )
        )


        created += 1



conn.commit()
conn.close()


print(
    f"Recommendations created: {created}"
)
