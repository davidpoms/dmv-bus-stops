from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = '''    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    reviewer_history = query_db(
        """
        SELECT
            id,
            observed_at

        FROM stop_observations

        WHERE physical_stop_id=?

        AND reviewer_id=?

        AND source='community_review'

        ORDER BY observed_at DESC
        """,
        (
            stop_id,
            reviewer_id
        )
    )
'''


new = '''    reviewer_id = None

    reviewer_key = session.get(
        "reviewer_key"
    )


    if reviewer_key:

        reviewer_id, reviewer_key = get_or_create_reviewer(
            reviewer_key
        )


    reviewer_history = []


    if reviewer_id:

        reviewer_history = query_db(
            """
            SELECT
                id,
                observed_at

            FROM stop_observations

            WHERE physical_stop_id=?

            AND reviewer_id=?

            AND source='community_review'

            ORDER BY observed_at DESC
            """,
            (
                stop_id,
                reviewer_id
            )
        )
'''


if old in text:

    text = text.replace(old, new, 1)

    print("Reviewer page-load identity creation removed")

else:

    print("Target reviewer block not found")


path.write_text(
    text,
    encoding="utf-8"
)

print("Done")
