from pathlib import Path

app = Path("src/api/app.py")

text = app.read_text(encoding="utf-8")


marker = '''
    return {
        "success": True,
        "stop_id": stop_id,
        "assignment_id": assignment_id,
        "reviewer_id": reviewer_id,
        "review_count": review_count
    }
'''


replacement = '''
    first_review = (
        query_db(
            """
            SELECT COUNT(*)
            FROM stop_review_assignments
            WHERE stop_id=?
            AND status='completed'
            """,
            (stop_id,)
        )[0][0]
        == 1
    )


    impact = query_db(
        """
        SELECT
            daily_route_exposure
        FROM stop_improvement_impact
        WHERE physical_stop_id=?
        """,
        (stop_id,)
    )


    return {
        "success": True,
        "stop_id": stop_id,
        "assignment_id": assignment_id,
        "reviewer_id": reviewer_id,

        "reviewer_stats": {
            "review_count": review_count,
            "first_review": first_review
        },

        "community_impact": {
            "daily_route_exposure":
                impact[0][0]
                if impact
                else None
        }
    }
'''


if marker not in text:
    raise RuntimeError("Could not find review response block")


text = text.replace(marker, replacement)

app.write_text(text, encoding="utf-8")

print("Added review completion impact response.")