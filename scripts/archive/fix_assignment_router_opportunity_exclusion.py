from pathlib import Path

p = Path("src/review/assignment_router.py")

text = p.read_text()

old = '''        row = cur.execute(
            """
            SELECT
                id,
                physical_stop_id
            FROM review_queue
WHERE review_status='pending'
AND community_review_available=1
AND physical_stop_id NOT IN (
    SELECT stop_id
    FROM stop_review_assignments
    WHERE reviewer_id=?
)
ORDER BY priority_rank
LIMIT 1
            """
    (
        reviewer_id,
    )
    ).fetchone()
'''

new = '''        row = cur.execute(
            """
            SELECT
                id,
                physical_stop_id
            FROM review_queue
            WHERE review_status='pending'
            AND community_review_available=1
            AND physical_stop_id NOT IN (
                SELECT stop_id
                FROM stop_review_assignments
                WHERE reviewer_id=?
            )
            ORDER BY priority_rank
            LIMIT 1
            """,
            (
                reviewer_id,
            )
        ).fetchone()
'''

if old not in text:
    raise Exception("Malformed opportunity query block not found")

text = text.replace(old, new)

p.write_text(text)

print("Fixed opportunity assignment query")