from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = '''    community_review = {
        "has_reviewed": bool(reviewer_history),

        "review_count":
            len(reviewer_history),

        "latest_review_id":
            reviewer_history[0][0]
            if reviewer_history
            else None,

        "last_reviewed_at":
            reviewer_history[0][1]
            if reviewer_history
            else None
    }
'''


new = '''    my_review_count = len(reviewer_history)


    total_stop_reviews = query_db(
        """
        SELECT COUNT(*)

        FROM stop_observations

        WHERE physical_stop_id=?

        AND source='community_review'
        """,
        (stop_id,)
    )


    community_review = {

        "has_reviewed": bool(reviewer_history),

        "my_review_count":
            my_review_count,

        "total_stop_reviews":
            total_stop_reviews[0][0]
            if total_stop_reviews
            else 0,

        "latest_review_id":
            reviewer_history[0][0]
            if reviewer_history
            else None,

        "last_reviewed_at":
            reviewer_history[0][1]
            if reviewer_history
            else None
    }
'''


if old in text:

    text = text.replace(old, new, 1)

    print("Updated community review summary")

else:

    print("Target block not found")


path.write_text(text, encoding="utf-8")

print("Done")
