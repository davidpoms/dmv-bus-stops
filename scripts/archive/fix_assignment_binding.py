from pathlib import Path
import re


# -----------------------------
# Fix Flask assignment endpoint
# -----------------------------

app_path = Path("src/api/app.py")
text = app_path.read_text()


pattern = re.compile(
    r'@app\.route\("/review/<int:stop_id>/assignment"\).*?(?=@app\.route\("/review/submit")',
    re.S
)


replacement = r'''
@app.route("/review/<int:stop_id>/assignment")
def review_assignment(stop_id):

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


new_text, count = pattern.subn(
    replacement,
    text
)


if count != 1:
    raise Exception(
        f"Assignment endpoint replacement failed. Matches: {count}"
    )


app_path.write_text(new_text)

print("✓ Updated Flask assignment endpoint")



# -----------------------------
# Fix review.html assignment fetch
# -----------------------------

html_path = Path(
    "src/dashboard/templates/review.html"
)

html = html_path.read_text()


old = """
    const response =
        await fetch(
            `/review/${stopId}/assignment`
        );
"""


new = """
    const params =
        new URLSearchParams(
            window.location.search
        );


    const assignmentId =
        params.get("assignment");


    const response =
        await fetch(
            `/review/${stopId}/assignment?assignment_id=${assignmentId}`
        );
"""


if old not in html:
    raise Exception(
        "Could not find review assignment fetch block"
    )


html = html.replace(
    old,
    new
)


html_path.write_text(html)

print("✓ Updated review.html assignment lookup")

print("Done.")
