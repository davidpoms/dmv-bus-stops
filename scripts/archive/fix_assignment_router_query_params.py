from pathlib import Path

path = Path(
    "src/review/assignment_router.py"
)

text = path.read_text()


# Fix random scenario queries if accidental params were added
text = text.replace(
"""
        stop = cur.execute(
            \"\"\"
            SELECT physical_stop_id
            FROM review_queue
            WHERE review_status='pending'
            ORDER BY RANDOM()
            LIMIT 1
            \"\"\",
            (
                reviewer_id,
                scenario
            )
        ).fetchone()
""",
"""
        stop = cur.execute(
            \"\"\"
            SELECT physical_stop_id
            FROM review_queue
            WHERE review_status='pending'
            ORDER BY RANDOM()
            LIMIT 1
            \"\"\"
        ).fetchone()
"""
)


# Fix opportunity query if it received params
text = text.replace(
"""
        stop = cur.execute(
            \"\"\"
            SELECT physical_stop_id
            FROM review_queue
            WHERE review_status='pending'
            ORDER BY priority_rank
            LIMIT 1
            \"\"\",
            (
                reviewer_id,
                scenario
            )
        ).fetchone()
""",
"""
        stop = cur.execute(
            \"\"\"
            SELECT physical_stop_id
            FROM review_queue
            WHERE review_status='pending'
            ORDER BY priority_rank
            LIMIT 1
            \"\"\"
        ).fetchone()
"""
)


path.write_text(text)

print(
    "✓ Fixed assignment router query parameters"
)
