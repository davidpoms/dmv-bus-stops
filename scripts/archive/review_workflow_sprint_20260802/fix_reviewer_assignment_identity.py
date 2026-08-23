from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = """
@app.route("/review/<int:stop_id>/assignment")
def review_assignment(stop_id):

    assignment_id = request.args.get(
        "assignment_id"
    )
"""

new = """
@app.route("/review/<int:stop_id>/assignment")
def review_assignment(stop_id):

    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    assignment_id = request.args.get(
        "assignment_id"
    )
"""


if old not in text:
    raise RuntimeError(
        "Could not find review_assignment header"
    )

text = text.replace(old, new)


old = """
            (
                stop_id,
                "anonymous",
                scenario
            )
"""


new = """
            (
                stop_id,
                reviewer_id,
                scenario
            )
"""


if old not in text:
    raise RuntimeError(
        "Could not find anonymous assignment insert"
    )


text = text.replace(old, new)


# remove duplicated assignment lookup block
duplicate = """
        assignment = query_db(
            \"\"\"
            SELECT
                id,
                reviewer_id,
                stop_id

            FROM stop_review_assignments

            WHERE stop_id=?

            AND status='assigned'

            ORDER BY id DESC

            LIMIT 1
            \"\"\",
            (
                stop_id,
            )
        )


        assignment = query_db(
"""


replacement = """
        assignment = query_db(
"""


if duplicate in text:
    text = text.replace(
        duplicate,
        replacement,
        1
    )


path.write_text(
    text,
    encoding="utf-8"
)

print(
    "Fixed reviewer identity flow"
)