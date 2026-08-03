from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = '''
        "reviewer_stats": {
            "review_count": review_count,
            "first_review": first_review
        },
'''


new = '''
        "reviewer_stats": {

            "display_name":
                query_db(
                    """
                    SELECT display_name
                    FROM community_reviewers
                    WHERE id=?
                    """,
                    (reviewer_id,)
                )[0][0],

            "review_count":
                review_count,

            "first_review":
                first_review,

            "stops_reviewed":
                query_db(
                    """
                    SELECT COUNT(DISTINCT stop_id)
                    FROM stop_review_assignments
                    WHERE reviewer_id=?
                    AND status='completed'
                    """,
                    (reviewer_id,)
                )[0][0]

        },
'''


if old not in text:
    raise SystemExit(
        "reviewer_stats block not found"
    )


text = text.replace(
    old,
    new
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Added reviewer profile stats"
)