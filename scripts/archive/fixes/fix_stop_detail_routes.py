from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old_join = """
LEFT JOIN stop_routes sr
    ON bs.gtfs_stop_id = CAST(sr.stop_id AS TEXT)
"""


new_join = """
LEFT JOIN stop_routes sr
    ON bs.id = sr.stop_id
"""


if old_join not in text:
    print("Old stop_routes join not found")
else:
    text = text.replace(
        old_join,
        new_join,
        1
    )


old_routes = """
GROUP_CONCAT(DISTINCT r.route_name) AS routes
"""


new_routes = """
GROUP_CONCAT(DISTINCT r.route_id) AS routes
"""


if old_routes not in text:
    print("Old route name aggregation not found")
else:
    text = text.replace(
        old_routes,
        new_routes,
        1
    )


path.write_text(
    text,
    encoding="utf-8"
)


print("Fixed stop detail route join and route labels")