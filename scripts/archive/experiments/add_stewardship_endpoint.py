from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")

marker = "@app.route(\"/stops/<int:stop_id>/community-action\", methods=[\"POST\"])"

insert = r'''
@app.route("/stops/<int:stop_id>/steward", methods=["POST"])
def create_stewardship(stop_id):

    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    query_db(
        """
        INSERT OR IGNORE INTO community_stewardships
        (
            reviewer_id,
            stop_id
        )
        VALUES (?, ?)
        """,
        (
            reviewer_id,
            stop_id
        )
    )


    return jsonify(
        {
            "status": "stewarded",
            "stop_id": stop_id
        }
    )


'''

if insert.strip() in text:
    print("Endpoint already exists")
elif marker in text:
    text = text.replace(
        marker,
        insert + marker,
        1
    )
    path.write_text(
        text,
        encoding="utf-8"
    )
    print("Added stewardship endpoint")
else:
    raise Exception("Marker not found")