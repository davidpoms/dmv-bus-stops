from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


marker = """
@app.route("/validation/status-summary")
def validation_status_summary():
"""


insert = '''
@app.route("/stops/<int:stop_id>/community-action", methods=["POST"])
def create_community_action(stop_id):

    data = request.get_json()

    status = data.get(
        "status",
        "planned"
    )

    project_type = data.get(
        "project_type"
    )

    steward = data.get(
        "steward"
    )

    notes = data.get(
        "notes"
    )


    query_db(
        """
        INSERT INTO community_actions
        (
            physical_stop_id,
            status,
            project_type,
            steward,
            notes
        )
        VALUES
        (?, ?, ?, ?, ?)
        """,
        (
            stop_id,
            status,
            project_type,
            steward,
            notes
        )
    )


    return jsonify(
        {
            "status": "created",
            "stop_id": stop_id
        }
    )


'''


if marker not in text:
    print("endpoint insertion point not found")
    raise SystemExit(1)


text = text.replace(
    marker,
    insert + marker,
    1
)


p.write_text(text)

print("community action endpoint added")
