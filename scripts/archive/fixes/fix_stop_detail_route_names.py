from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = """
GROUP_CONCAT(DISTINCT r.route_name) AS routes
"""


new = """
GROUP_CONCAT(DISTINCT r.route_id) AS routes
"""


if old not in text:
    print("Route name query not found")
    raise SystemExit(1)


text = text.replace(
    old,
    new,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print("Updated stop detail routes to use route IDs")