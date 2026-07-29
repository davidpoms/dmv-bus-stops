from pathlib import Path


path = Path(
    "src/review/assignment_router.py"
)

text = path.read_text()


old = """def assign_stop(
    reviewer_id,
    scenario
):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
"""


new = """def assign_stop(
    reviewer_id,
    scenario
):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()


    # Reuse existing active assignment
    existing = cur.execute(
        '''
        SELECT
            id,
            stop_id

        FROM stop_review_assignments

        WHERE reviewer_id=?
        AND status='assigned'

        ORDER BY id DESC

        LIMIT 1
        ''',
        (
            reviewer_id,
        )
    ).fetchone()


    if existing:

        conn.close()

        return existing[0], existing[1]
"""


if old not in text:
    raise Exception(
        "Target function header not found"
    )


text = text.replace(
    old,
    new
)


path.write_text(text)

print(
    "✓ Added assignment reuse logic"
)
