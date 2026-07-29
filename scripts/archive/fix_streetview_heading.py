from pathlib import Path

p = Path("src/spatial/nearest_road.py")

text = p.read_text()


old = """
        dx = px - best[0]

        dy = py - best[1]

        if dx == 0 and dy == 0:

            heading = None

        else:

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


new = """
        edge = self.edges[idx]

        ax, ay, bx, by = edge


        heading = (
            math.degrees(
                math.atan2(
                    bx - ax,
                    by - ay
                )
            )
            % 360
        )
"""


if old not in text:
    raise Exception(
        "Could not find old heading calculation"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print("Fixed Street View heading calculation")
