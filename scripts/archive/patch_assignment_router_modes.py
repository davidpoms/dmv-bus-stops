from pathlib import Path

p = Path("src/review/assignment_router.py")

text = p.read_text()

old = '''    elif scenario == "nearby" and latitude and longitude:
'''

new = '''    elif scenario == "route":

        row = cur.execute(
            """
            SELECT
                rq.id,
                rq.physical_stop_id
            FROM review_queue rq
            WHERE rq.community_review_available=1
            AND rq.review_status='pending'
            AND rq.physical_stop_id NOT IN (
                SELECT stop_id
                FROM stop_review_assignments
                WHERE reviewer_id=?
                AND status='completed'
            )
            ORDER BY rq.priority_rank
            LIMIT 1
            """,
            (
                reviewer_id,
            )
        ).fetchone()


    elif scenario == "nearby" and latitude and longitude:
'''

if old not in text:
    raise Exception("Could not find insertion point")

text = text.replace(old, new)

p.write_text(text)

print("patched assignment router route mode")