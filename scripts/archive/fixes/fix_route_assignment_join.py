from pathlib import Path

path = Path("src/review/assignment_router.py")

text = path.read_text(encoding="utf-8")


old = """            FROM review_queue rq

            JOIN stop_routes sr
                ON sr.stop_id = rq.physical_stop_id

            JOIN community_reviewer_routes crr
                ON crr.route_id = sr.route_id
"""


new = """            FROM review_queue rq

            JOIN physical_stop_members psm
                ON psm.physical_stop_id = rq.physical_stop_id

            JOIN stop_routes sr
                ON sr.stop_id = psm.bus_stop_id

            JOIN community_reviewer_routes crr
                ON crr.route_id = sr.route_id
"""


if old not in text:
    raise SystemExit(
        "Could not find route mode join block"
    )


text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("Route assignment join fixed")