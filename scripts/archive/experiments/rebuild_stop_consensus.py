"""
Rebuild stop consensus from stop_observations.

Consensus requires:
- completed assignments
- unique reviewers
- minimum reviewer threshold

Produces:
- factual amenity consensus
- rider comfort consensus
"""

import sqlite3
from collections import Counter


DB = "src/database/dmv_bus_stops.db"

MIN_REVIEWS = 4


def is_yes(value):
    return str(value).lower() in (
        "yes",
        "1",
        "true",
        "full_bench"
    )


def most_common(values):

    values = [
        v for v in values
        if v not in (None, "", "unknown")
    ]

    if not values:
        return None

    return Counter(values).most_common(1)[0][0]


conn = sqlite3.connect(DB)

cur = conn.cursor()


cur.execute(
    "DELETE FROM stop_consensus;"
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
    ) >= ?

    """,
    (MIN_REVIEWS,)
).fetchall()


created = 0


for (stop_id,) in stops:

    rows = cur.execute(
        """
        SELECT *
        FROM stop_observations

        WHERE id IN
        (
            SELECT MAX(id)

            FROM stop_observations

            WHERE physical_stop_id=?

            AND reviewer_id IS NOT NULL

            GROUP BY reviewer_id
        )

        """,
        (stop_id,)
    ).fetchall()


    if len(rows) < MIN_REVIEWS:
        continue


    cols = [
        d[0]
        for d in cur.description
    ]


    observations = [
        dict(zip(cols, row))
        for row in rows
    ]


    reviewer_count = len(observations)


    has_bench = (
        sum(
            is_yes(o["bench_present"])
            for o in observations
        )
        >= reviewer_count / 2
    )


    has_shelter = (
        sum(
            is_yes(o["shelter_present"])
            for o in observations
        )
        >= reviewer_count / 2
    )


    bench_feasible = (
        sum(
            is_yes(o["bench_feasible"])
            for o in observations
        )
        >= reviewer_count / 2
    )


    ada_accessible = (
        sum(
            is_yes(o["ada_clearance_possible"])
            for o in observations
        )
        >= reviewer_count / 2
    )


    seating_values = [
        o["bench_type"]
        if o["bench_type"]
        else o["shelter_type"]
        for o in observations
    ]


    seating_type = most_common(
        seating_values
    )


    comfort = most_common(
        [
            o["rider_comfort_category"]
            for o in observations
        ]
    )


    hostile = most_common(
        [
            o["hostile_design"]
            for o in observations
        ]
    )


    confidence = sum(
        [
            o["confidence"]
            for o in observations
            if isinstance(o["confidence"], (int,float))
        ]
    )


    confidence_count = sum(
        1
        for o in observations
        if isinstance(o["confidence"], (int,float))
    )


    confidence = (
        confidence / confidence_count
        if confidence_count
        else 0
    )


    cur.execute(
        """
        INSERT INTO stop_consensus
        (
            stop_id,
            reviewer_count,
            has_shelter,
            has_bench,
            bench_feasible,
            ada_accessible,
            confidence,
            consensus_status,
            seating_type_consensus,
            rider_comfort_consensus,
            hostile_design_consensus
        )

        VALUES (?,?,?,?,?,?,?,?,?,?,?)

        """,
        (
            stop_id,
            reviewer_count,
            has_shelter,
            has_bench,
            bench_feasible,
            ada_accessible,
            confidence,
            "verified",
            seating_type,
            comfort,
            hostile
        )
    )


    created += 1


conn.commit()
conn.close()


print(
    f"Consensus records created: {created}"
)
