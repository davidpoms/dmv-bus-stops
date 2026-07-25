import sqlite3
import random

DB = "src/database/dmv_bus_stops.db"

REVIEWERS_PER_STOP = 3
BATCH_SIZE = 100


conn = sqlite3.connect(DB)
cur = conn.cursor()


# Find reviewers
reviewers = cur.execute("""
SELECT id
FROM community_reviewers
ORDER BY id
""").fetchall()


if len(reviewers) < REVIEWERS_PER_STOP:
    print(
        f"Need at least {REVIEWERS_PER_STOP} reviewers. "
        f"Currently have {len(reviewers)}."
    )
    conn.close()
    raise SystemExit


reviewer_ids = [
    r[0]
    for r in reviewers
]


# Stops already having consensus
completed = {
    row[0]
    for row in cur.execute("""
        SELECT stop_id
        FROM stop_consensus
        WHERE consensus_status = 'verified'
    """)
}


# Stops needing assignment
stops = [
    row[0]
    for row in cur.execute("""
        SELECT physical_stop_id
        FROM stop_validation
        WHERE status = 'needs_validation'
    """)
    if row[0] not in completed
]


random.shuffle(stops)

assigned = 0


for stop_id in stops:

    if assigned >= BATCH_SIZE:
        break


    existing = {
        row[0]
        for row in cur.execute(
            """
            SELECT reviewer_id
            FROM stop_review_assignments
            WHERE stop_id = ?
            """,
            (stop_id,)
        )
    }


    available = [
        r
        for r in reviewer_ids
        if r not in existing
    ]


    if len(available) < REVIEWERS_PER_STOP:
        continue


    chosen = random.sample(
        available,
        REVIEWERS_PER_STOP
    )


    for reviewer_id in chosen:

        cur.execute(
            """
            INSERT OR IGNORE INTO stop_review_assignments
            (
                stop_id,
                reviewer_id
            )
            VALUES (?,?)
            """,
            (
                stop_id,
                reviewer_id
            )
        )


    assigned += 1


conn.commit()


count = cur.execute("""
SELECT COUNT(*)
FROM stop_review_assignments
""").fetchone()[0]


conn.close()


print(
    f"Created assignments for {assigned} stops"
)

print(
    f"Total assignments: {count}"
)
