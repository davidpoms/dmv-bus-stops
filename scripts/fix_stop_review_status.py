from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")

start = text.index('@app.route("/stops/<int:stop_id>")')
end = text.index('@app.route("/review/start")')

section = text[start:end]


if "community_review =" not in section:

    marker = """
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

    if marker not in section:
        raise Exception("Could not find stop_detail return")

    section = section.replace(
        marker,
        addition + marker,
        1
    )

    text = (
        text[:start]
        + section
        + text[end:]
    )


path.write_text(
    text,
    encoding="utf-8"
)

print("Fixed community_review placement")
