from pathlib import Path

p = Path("src/spatial/nearest_road.py")

text = p.read_text()

old = """
            heading = (
                math.degrees(
                    math.atan2(dx, dy)
                )
                % 360
            )
"""

new = """
            heading = (
                (
                    math.degrees(
                        math.atan2(dx, dy)
                    )
                    + 180
                )
                % 360
            )
"""

if old not in text:
    raise Exception(
        "Could not find heading calculation"
    )

text = text.replace(
    old,
    new
)

p.write_text(text)

print("Flipped Street View heading direction")
