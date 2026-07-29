from pathlib import Path
import re


path = Path(
    "src/review/assignment_router.py"
)

text = path.read_text()


# Add consensus threshold after DB definition

marker = """
DB = (
    Path(__file__).resolve()
    .parents[1]
    / "database"
    / "dmv_bus_stops.db"
)
"""


replacement = """
DB = (
    Path(__file__).resolve()
    .parents[1]
    / "database"
    / "dmv_bus_stops.db"
)


# Minimum independent reviews before consensus
MIN_REVIEWERS = 3
"""


if "MIN_REVIEWERS" not in text:

    text = text.replace(
        marker,
        replacement
    )


# Replace opportunity query

old = """
        stop = cur.execute(
            \"\"\"
            SELECT physical_stop_id
            FROM review_queue
            WHERE review_status='pending'
            ORDER BY priority_rank
            LIMIT 1
            \"\"\"
        ).fetchone()
"""


new = """
        stop = cur.execute(
            \"\"\"
            SELECT rq.physical_stop_id

            FROM review_queue rq

            LEFT JOIN stop_consensus sc
                ON sc.stop_id = rq.physical_stop_id

            WHERE
                sc.stop_id IS NULL

                OR (
                    sc.consensus_status != 'verified'
                    AND sc.reviewer_count < ?
                )

            ORDER BY rq.priority_rank

            LIMIT 1

            \"\"\",
            (
                MIN_REVIEWERS,
            )
        ).fetchone()
"""


if old not in text:
    raise Exception(
        "Opportunity query block not found"
    )


text = text.replace(
    old,
    new
)


# Replace route and nearby queries similarly

text = text.replace(
"""
            FROM review_queue
            WHERE review_status='pending'
            ORDER BY RANDOM()
            LIMIT 1
""",
"""
            FROM review_queue rq

            LEFT JOIN stop_consensus sc
                ON sc.stop_id = rq.physical_stop_id

            WHERE
                sc.stop_id IS NULL

                OR (
                    sc.consensus_status != 'verified'
                    AND sc.reviewer_count < ?
                )

            ORDER BY RANDOM()

            LIMIT 1
"""
)


path.write_text(text)

print("✓ Updated assignment router consensus logic")
