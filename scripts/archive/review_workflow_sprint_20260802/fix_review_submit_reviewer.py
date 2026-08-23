from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = """
    stop_id = data.get("stop_id")
    reviewer_id = data.get("reviewer_id")
    assignment_id = data.get("assignment_id")


    if (
        not assignment_id
        or not reviewer_id
        or str(reviewer_id) in ("undefined", "null", "")
    ):
        return {
            "error": "valid assignment_id and reviewer_id required"
        }, 400
"""


new = """
    stop_id = data.get("stop_id")
    assignment_id = data.get("assignment_id")


    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    if not assignment_id:
        return {
            "error": "valid assignment_id required"
        }, 400
"""


if old not in text:
    raise Exception(
        "Could not find reviewer validation block"
    )


text = text.replace(
    old,
    new,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Fixed review submit reviewer handling"
)