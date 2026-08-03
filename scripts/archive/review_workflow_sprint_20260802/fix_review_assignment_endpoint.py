from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


start = text.index(
    '@app.route("/review/<int:stop_id>/assignment")'
)

end = text.index(
    '@app.route("/review/submit"',
    start
)


replacement = r'''
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


    if assignment_id:

        assignment = query_db(
            """
            SELECT
                id,
                reviewer_id,
                stop_id

            FROM stop_review_assignments

            WHERE id=?
            """,
            (
                assignment_id,
            )
        )

    else:

        assignment = query_db(
            """
            SELECT
                id,
                reviewer_id,
                stop_id

            FROM stop_review_assignments

            WHERE stop_id=?
            AND reviewer_id=?
            AND status='assigned'

            ORDER BY id DESC

            LIMIT 1
            """,
            (
                stop_id,
                reviewer_id
            )
        )


    if not assignment:

        scenario = request.args.get(
            "mode",
            "opportunity"
        )

        query_db(
            """
            INSERT INTO stop_review_assignments
            (
                stop_id,
                reviewer_id,
                scenario,
                status
            )

            VALUES (?, ?, ?, 'assigned')
            """,
            (
                stop_id,
                reviewer_id,
                scenario
            )
        )


        assignment = query_db(
            """
            SELECT
                id,
                reviewer_id,
                stop_id

            FROM stop_review_assignments

            WHERE stop_id=?
            AND reviewer_id=?
            AND status='assigned'

            ORDER BY id DESC

            LIMIT 1
            """,
            (
                stop_id,
                reviewer_id
            )
        )


    if not assignment:

        return jsonify(
            {
                "error":
                    "No active assignment found"
            }
        ), 404


    return jsonify(
        {
            "assignment_id":
                assignment[0][0],

            "reviewer_id":
                assignment[0][1],

            "stop_id":
                assignment[0][2]
        }
    )


'''


new_text = (
    text[:start]
    + replacement
    + text[end:]
)


path.write_text(
    new_text,
    encoding="utf-8"
)


print("Fixed review assignment endpoint")