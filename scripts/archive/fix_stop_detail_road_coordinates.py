from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


old = """    road = get_road_index().nearest_road(
        row[3],
        row[2]
    )
"""


new = """    road = get_road_index().nearest_road(
        row[2],
        row[1]
    )
"""


if old not in text:
    raise Exception("Could not find road lookup block")


text = text.replace(old, new, 1)


path.write_text(text)

print("Fixed stop_detail road coordinate ordering")