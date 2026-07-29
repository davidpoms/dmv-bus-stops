from pathlib import Path

path = Path("src/review/assignment_router.py")

text = path.read_text()

old = """    elif scenario == "nearby":

        # Use provided coordinates when available.
        # Fall back to highest priority nearby-capable stop.
        stop = cur.execute(
            \"\"\"
            SELECT
                rq.physical_stop_id
            FROM review_queue rq
            JOIN physical_stops ps
                ON ps.id = rq.physical_stop_id
            WHERE rq.community_review_available=1
            ORDER BY rq.priority_rank
            LIMIT 1
            \"\"\"
        ).fetchone()
"""

new = """    elif scenario == "nearby":

        if latitude and longitude:

            stop = cur.execute(
                \"\"\"
                SELECT
                    rq.physical_stop_id
                FROM review_queue rq
                JOIN physical_stops ps
                    ON ps.id = rq.physical_stop_id
                WHERE rq.community_review_available=1
                ORDER BY
                    ((ps.latitude - ?) * (ps.latitude - ?))
                    +
                    ((ps.longitude - ?) * (ps.longitude - ?))
                LIMIT 1
                \"\"\",
                (
                    float(latitude),
                    float(latitude),
                    float(longitude),
                    float(longitude)
                )
            ).fetchone()

        else:

            stop = cur.execute(
                \"\"\"
                SELECT physical_stop_id
                FROM review_queue
                WHERE community_review_available=1
                ORDER BY priority_rank
                LIMIT 1
                \"\"\"
            ).fetchone()
"""

if old not in text:
    raise Exception("Nearby block not found")

text = text.replace(old, new)

path.write_text(text)

print("Nearby distance assignment enabled")
