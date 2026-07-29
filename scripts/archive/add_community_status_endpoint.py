from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = """
@app.route("/stops/<int:stop_id>")
def stop_detail(stop_id):
"""

if "/community-status" in text:
    print("community status endpoint already exists")
    raise SystemExit


insert = r'''
@app.route("/stops/<int:stop_id>/community-status")
def community_status(stop_id):

    validation = query_db(
        """
        SELECT
            status,
            validator,
            validated_at
        FROM stop_validation
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )


    review_count = query_db(
        """
        SELECT COUNT(*)
        FROM stop_reviews
        WHERE stop_id = ?
        """,
        (stop_id,)
    )[0][0]


    observation_count = query_db(
        """
        SELECT COUNT(*)
        FROM stop_observations
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )[0][0]


    projects = query_db(
        """
        SELECT
            recommendation_type,
            project_status,
            assigned_team,
            completed_date
        FROM improvement_projects
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )


    if validation:

        validation_status = validation[0][0]
        validator = validation[0][1]
        validated_at = validation[0][2]

    else:

        validation_status = "needs_validation"
        validator = None
        validated_at = None



    installed_projects = []

    for project in projects:

        installed_projects.append(
            {
                "type": project[0],
                "status": project[1],
                "steward": project[2],
                "completed_date": project[3]
            }
        )


    return jsonify(
        {
            "validation_status": validation_status,

            "validation": {
                "validator": validator,
                "validated_at": validated_at
            },

            "evidence": {
                "streetview_reviews": review_count,
                "field_observations": observation_count
            },

            "community_action": {
                "improvements": installed_projects
            }
        }
    )


'''


text = text.replace(
    marker,
    insert + marker
)


p.write_text(text)

print("community status endpoint added")
