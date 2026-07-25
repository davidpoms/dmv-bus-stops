from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
    )


    return jsonify(
        {
            "status":"saved"
        }
    )
"""

new = """
    )


    query_db(
        '''
        UPDATE stop_review_assignments
        SET
            status='completed',
            completed_at=CURRENT_TIMESTAMP
        WHERE id=?
        ''',
        (
            assignment_id,
        )
    )


    return jsonify(
        {
            "status":"saved"
        }
    )
"""

if old in text:
    text = text.replace(old, new, 1)
    print("Added assignment completion")
else:
    print("Return block not found")

p.write_text(text)
