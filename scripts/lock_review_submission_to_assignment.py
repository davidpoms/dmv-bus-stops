from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
def submit_review():

    data = request.json


    query_db(
"""

new = """
def submit_review():

    data = request.json

    stop_id = data.get("stop_id")
    reviewer_id = data.get("reviewer_id")
    assignment_id = data.get("assignment_id")


    if not assignment_id or not reviewer_id:

        return {
            "error": "assignment_id and reviewer_id required"
        }, 400


    assignment = query_db(
        '''
        SELECT id
        FROM stop_review_assignments
        WHERE id=?
        AND stop_id=?
        AND reviewer_id=?
        AND status='assigned'
        ''',
        (
            assignment_id,
            stop_id,
            reviewer_id
        )
    )


    if not assignment:

        return {
            "error": "Invalid or completed assignment"
        }, 403


    query_db(
"""

if old in text:
    text = text.replace(old,new,1)
    print("Locked review submission to assignments")
else:
    print("submit_review block not found")

p.write_text(text)
