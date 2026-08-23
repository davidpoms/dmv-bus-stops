from pathlib import Path

path = Path("src/review/assignment_router.py")

text = path.read_text()

start = text.find("    conn.close()\n\n\n    if not row:")

if start == -1:
    raise Exception("Could not find broken assignment_router tail")

replacement = """    if not row:
        conn.close()
        return None


    stop_id = row[1]


    cur.execute(
        \"\"\"
        INSERT INTO stop_review_assignments
        (
            stop_id,
            reviewer_id,
            scenario,
            status
        )
        VALUES (?, ?, ?, 'assigned')
        \"\"\",
        (
            stop_id,
            reviewer_id,
            scenario
        )
    )


    assignment_id = cur.lastrowid


    conn.commit()
    conn.close()


    return assignment_id, stop_id
"""

new_text = text[:start] + replacement

path.write_text(new_text)

print("Fixed assignment_router.py tail")