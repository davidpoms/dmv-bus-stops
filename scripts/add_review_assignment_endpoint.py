from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

route = r'''

@app.route("/review/<int:stop_id>/assignment")
def review_assignment(stop_id):

    assignment = query_db(
        """
        SELECT
            id,
            reviewer_id,
            stop_id

        FROM stop_review_assignments

        WHERE stop_id=?

        AND status='assigned'

        ORDER BY id

        LIMIT 1
        """,
        (
            stop_id,
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

if 'def review_assignment(stop_id)' not in text:

    insert = text.find('@app.route("/review/submit"')

    text = (
        text[:insert]
        +
        route
        +
        text[insert:]
    )

    p.write_text(text)

    print("Added review assignment endpoint")

else:
    print("Endpoint already exists")

