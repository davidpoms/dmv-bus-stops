from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


insert_before = """
    return jsonify(
"""


addition = """
    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    reviewer_history = query_db(
        \"\"\"
        SELECT
            id,
            observed_at

        FROM stop_observations

        WHERE physical_stop_id=?

        AND reviewer_id=?

        AND source='community_review'

        ORDER BY observed_at DESC
        \"\"\",
        (
            stop_id,
            reviewer_id
        )
    )


    community_review = {
        "has_reviewed": bool(reviewer_history),

        "review_count":
            len(reviewer_history),

        "latest_review_id":
            reviewer_history[0][0]
            if reviewer_history
            else None,

        "last_reviewed_at":
            reviewer_history[0][1]
            if reviewer_history
            else None
    }

"""


if addition.strip() not in text:

    location = text.find(insert_before)

    if location == -1:
        raise Exception("Could not find jsonify return block")

    text = (
        text[:location]
        + addition
        + text[location:]
    )


old = """
            "wmata_evidence":
                wmata_evidence,
"""

new = """
            "wmata_evidence":
                wmata_evidence,

            "community_review":
                community_review,
"""


if old in text:

    text = text.replace(
        old,
        new,
        1
    )

else:
    print("JSON insertion point already changed or not found")


path.write_text(
    text,
    encoding="utf-8"
)

print("Added community review status to stop endpoint")
