from pathlib import Path


path = Path(
    "src/review/assignment_router.py"
)

text = path.read_text()


# Fix opportunity query binding
old = """
            LIMIT 1

            """,
            (
                MIN_REVIEWERS,
            )
        ).fetchone()
"""


new = """
            LIMIT 1

            """
        ).fetchone()
"""


if old not in text:
    raise Exception(
        "Opportunity binding block not found"
    )


text = text.replace(
    old,
    new,
    1
)


# Replace route and nearby entire query blocks
old_route = """
        stop = cur.execute(
            \"\"\"
            SELECT physical_stop_id
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
            \"\"\",
            (
                MIN_REVIEWERS,
            )
        ).fetchone()
"""


new_route = """
        stop = cur.execute(
            \"\"\"
            SELECT physical_stop_id

            FROM review_queue

            WHERE
                community_review_available=1

            ORDER BY RANDOM()

            LIMIT 1
            \"\"\"
        ).fetchone()
"""


count = text.count(old_route)

print(
    "Route/nearby blocks found:",
    count
)


if count != 2:
    raise Exception(
        f"Expected 2 route/nearby blocks, found {count}"
    )


text = text.replace(
    old_route,
    new_route
)


path.write_text(text)


print(
    "✓ Updated assignment router modes"
)
