from pathlib import Path

p = Path("src/review/assignment_router.py")

text = p.read_text()

old = """
    elif scenario == "nearby" and latitude and longitude:

        row = cur.execute(
"""

new = """
    elif scenario == "route":

        row = cur.execute(
            \"\"\"
            SELECT
                rq.id,
                rq.physical_stop_id
            FROM review_queue rq
            JOIN stop_routes sr
                ON sr.stop_id = rq.physical_stop_id
            WHERE rq.review_status='pending'
            AND rq.community_review_available=1
            AND rq.physical_stop_id NOT IN (
                SELECT stop_id
                FROM stop_review_assignments
                WHERE status='assigned'
            )
            ORDER BY rq.priority_rank
            LIMIT 1
            \"\"\"
        ).fetchone()


    elif scenario == "nearby" and latitude and longitude:

        row = cur.execute(
"""

if old not in text:
    raise Exception("Could not find insertion point")

text = text.replace(old, new)

p.write_text(text)

print("Added route assignment mode")