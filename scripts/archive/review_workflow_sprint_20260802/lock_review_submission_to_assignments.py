from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
@app.route("/review/submit", methods=["POST"])
def submit_review():
"""

new = """
@app.route("/review/submit", methods=["POST"])
def submit_review():
"""

# insert assignment check after data extraction
needle = """
    data = request.form
"""

replacement = """
    data = request.form

    stop_id = data.get("stop_id")
    reviewer_id = data.get("reviewer_id")

    assignment = query_db(
        '''
        SELECT id
        FROM stop_review_assignments
        WHERE stop_id = ?
        AND reviewer_id = ?
        AND status = 'assigned'
        ''',
        (
            stop_id,
            reviewer_id
        )
    )

    if not assignment:
        return {
            "error": "No active assignment for this reviewer"
        }, 403
"""

if needle in text and "No active assignment for this reviewer" not in text:
    text = text.replace(
        needle,
        replacement,
        1
    )

p.write_text(text)

print("Locked review submission to assignments")
