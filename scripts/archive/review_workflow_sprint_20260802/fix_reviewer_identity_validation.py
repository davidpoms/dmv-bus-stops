from pathlib import Path


APP = Path("src/api/app.py")

text = APP.read_text(encoding="utf-8")


old = """
    stop_id = data.get("stop_id")
    reviewer_id = data.get("reviewer_id")
    assignment_id = data.get("assignment_id")


    if not assignment_id or not reviewer_id:
        return {
            "error": "assignment_id and reviewer_id required"
        }, 400
"""


new = """
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


if old in text:
    text = text.replace(old, new)
    print("Added reviewer identity validation")
else:
    print("Validation block not found")


APP.write_text(text, encoding="utf-8")

print("Complete")