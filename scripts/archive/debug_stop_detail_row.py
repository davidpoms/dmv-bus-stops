from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


old = """    road = get_road_index().nearest_road(
        row[2],
        row[1]
    )
"""


new = """    print("DEBUG STOP DETAIL ROW:", row)
    print("DEBUG TYPES:", type(row[1]), type(row[2]))

    road = get_road_index().nearest_road(
        row[2],
        row[1]
    )
"""


if old not in text:
    raise Exception("Could not find road block")


text = text.replace(old, new, 1)

path.write_text(text)

print("Added stop detail debug logging")