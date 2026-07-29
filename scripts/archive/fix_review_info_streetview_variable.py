from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

needle = """
    row = stop[0]

    return jsonify(
"""

replacement = """
    row = stop[0]


    streetview = get_road_index().nearest_road(
        row[2],
        row[3]
    )


    heading = 0

    if streetview and streetview.get("heading") is not None:
        heading = streetview["heading"]


    streetview_url = (
        "https://www.google.com/maps/@?"
        f"api=1&map_action=pano"
        f"&viewpoint={row[2]},{row[3]}"
        f"&heading={heading}"
    )


    return jsonify(
"""

if needle not in text:
    raise Exception(
        "Could not find insertion point"
    )

text = text.replace(
    needle,
    replacement,
    1
)

p.write_text(text)

print(
    "Restored streetview_url generation"
)
