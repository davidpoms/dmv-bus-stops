from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


marker = """

@app.route("/api/review-queue")
"""


helper = r'''

def get_reviewer_impact(reviewer_id):

    return query_db(
        """
        SELECT
            COUNT(DISTINCT sra.stop_id),
            COALESCE(SUM(si.daily_route_exposure),0)

        FROM stop_review_assignments sra

        LEFT JOIN stop_improvement_impact si
            ON sra.stop_id = si.physical_stop_id

        WHERE sra.reviewer_id=?

        AND sra.status='completed'

        """,
        (reviewer_id,)
    )[0]


'''


if helper.strip() in text:
    print("Helper already exists")

elif marker not in text:
    raise Exception("Insertion point not found")

else:
    text = text.replace(
        marker,
        helper + marker
    )

    path.write_text(
        text,
        encoding="utf-8"
    )

    print("Added reviewer impact helper")