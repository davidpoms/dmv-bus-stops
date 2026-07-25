from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

addition = r'''

@app.route("/reviewer/<int:reviewer_id>")
def reviewer_dashboard(reviewer_id):

    assignments = query_db(
        """
        SELECT

            a.stop_id,
            a.status,

            p.latitude,
            p.longitude,
            p.stop_name

        FROM stop_review_assignments a

        JOIN physical_stops p
        ON p.id=a.stop_id

        WHERE reviewer_id=?

        ORDER BY a.status, a.assigned_at

        """,
        (reviewer_id,)
    )

    return render_template(
        "reviewer_dashboard.html",
        assignments=assignments,
        reviewer_id=reviewer_id
    )

'''

if "def reviewer_dashboard(" not in text:
    text += addition

p.write_text(text)

print("Added reviewer dashboard route")
