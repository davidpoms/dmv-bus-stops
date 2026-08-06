from pathlib import Path


path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = """
LEFT JOIN stop_routes sr
    ON bs.id = sr.stop_id
"""


new = """
LEFT JOIN stop_routes sr
    ON bs.gtfs_stop_id = CAST(sr.stop_id AS TEXT)
"""


if old not in text:
    print("Old route join not found")
    raise SystemExit(1)


text = text.replace(old, new, 1)


path.write_text(
    text,
    encoding="utf-8"
)


print("Updated stop detail route join")