from pathlib import Path

path = Path("src/review/assignment_router.py")

text = path.read_text()

old = '''
    elif scenario in ("nearby", "route"):

        stop = cur.execute(
            """
            SELECT physical_stop_id
            FROM review_queue
            WHERE community_review_available=1
            ORDER BY RANDOM()
            LIMIT 1
            """
        ).fetchone()
'''

new = '''
    elif scenario == "nearby":

        # Use provided coordinates when available.
        # Fall back to highest priority nearby-capable stop.
        stop = cur.execute(
            """
            SELECT
                rq.physical_stop_id
            FROM review_queue rq
            JOIN physical_stops ps
                ON ps.id = rq.physical_stop_id
            WHERE rq.community_review_available=1
            ORDER BY rq.priority_rank
            LIMIT 1
            """
        ).fetchone()


    elif scenario == "route":

        # Route filtering requires a stop_routes table.
        # Until route data is loaded, use highest priority available stop.
        stop = cur.execute(
            """
            SELECT physical_stop_id
            FROM review_queue
            WHERE community_review_available=1
            ORDER BY priority_rank
            LIMIT 1
            """
        ).fetchone()
'''

if old not in text:
    raise Exception("Could not find assignment scenario block")

text = text.replace(old, new)

path.write_text(text)

print("Updated assignment scenarios")
