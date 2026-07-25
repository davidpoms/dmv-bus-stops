from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

addition = r'''

@app.get("/api/reviewer/<int:reviewer_id>/queue")
def reviewer_queue(reviewer_id):

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT

            a.stop_id,
            a.status,

            p.latitude,
            p.longitude,

            p.stop_name

        FROM stop_review_assignments a

        JOIN physical_stops p
        ON p.id = a.stop_id

        WHERE a.reviewer_id = ?

        ORDER BY a.assigned_at

        """,
        (
            reviewer_id,
        )
    ).fetchall()


    conn.close()

    return [
        dict(row)
        for row in rows
    ]

'''

if "def reviewer_queue" not in text:
    text += addition

p.write_text(text)

print("Added reviewer queue endpoint")
