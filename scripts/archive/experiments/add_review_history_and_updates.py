from pathlib import Path


# -----------------------------
# Patch app.py
# -----------------------------

app_path = Path("src/api/app.py")

app = app_path.read_text(encoding="utf-8")


# Add community review history endpoint
marker = '@app.route("/review/submit", methods=["POST"])'


endpoint = r'''

@app.route("/stops/<int:stop_id>/community-reviews")
def community_reviews(stop_id):

    reviews = query_db(
        """
        SELECT
            id,
            observed_at,
            shelter_present,
            bench_present,
            notes,
            reviewer_id
        FROM stop_observations
        WHERE physical_stop_id=?
        AND source='community_review'
        ORDER BY observed_at DESC
        """,
        (stop_id,)
    )


    return jsonify(
        {
            "review_count":
                len(reviews),

            "reviews":
                [
                    {
                        "id": row[0],
                        "date": row[1],
                        "shelter": row[2],
                        "bench": row[3],
                        "notes": row[4]
                    }
                    for row in reviews
                ]
        }
    )


'''


if "/stops/<int:stop_id>/community-reviews" not in app:

    app = app.replace(
        marker,
        endpoint + marker,
        1
    )


# Replace duplicate review blocking

old = r'''
    if existing_review:
        return {
            "success": True,
            "message": "Review already submitted",
            "stop_id": stop_id,
            "reviewer_id": reviewer_id
        }
'''


new = r'''
    review_action = data.get(
        "review_action",
        "new"
    )


    if existing_review and review_action == "update":

        query_db(
            """
            UPDATE stop_observations
            SET
                shelter_present=?,
                bench_present=?,
                trash_present=?,
                bench_feasible=?,
                ada_clearance_possible=?,
                notes=?,
                observed_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                data.get("shelter_present"),
                data.get("bench_present"),
                data.get("trash_present"),
                data.get("bench_feasible"),
                data.get("ada_clearance_possible"),
                data.get("notes"),
                existing_review[0][0]
            )
        )


        return {
            "success": True,
            "message": "Review updated",
            "stop_id": stop_id
        }


'''


if old in app:

    app = app.replace(
        old,
        new,
        1
    )

else:

    print(
        "Warning: duplicate review block not found"
    )


app_path.write_text(
    app,
    encoding="utf-8"
)


# -----------------------------
# Patch review.html
# -----------------------------

html_path = Path(
    "src/dashboard/templates/review.html"
)

html = html_path.read_text(
    encoding="utf-8"
)


# Remove reviewer hidden input

html = html.replace(
    '<input type="hidden" name="reviewer_id" id="reviewer_id">',
    ''
)


# Add review action field

if "review_action" not in html:

    html = html.replace(
        '<input type="hidden" name="assignment_id" id="assignment_id">',
        '''
<input type="hidden" name="assignment_id" id="assignment_id">

<input type="hidden"
name="review_action"
id="review_action"
value="new">
'''
    )


# Remove reviewer assignment JS

html = html.replace(
'''
    document
    .getElementById("reviewer_id")
    .value =
        data.reviewer_id;
''',
''
)


# Remove reviewer payload

html = html.replace(
'''
payload.reviewer_id =
    document.getElementById("reviewer_id").value;
''',
''
)


html_path.write_text(
    html,
    encoding="utf-8"
)


print(
    "Review history and update/new observation support added"
)