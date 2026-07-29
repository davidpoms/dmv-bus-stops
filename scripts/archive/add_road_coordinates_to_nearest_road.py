from pathlib import Path

p = Path("src/spatial/nearest_road.py")

text = p.read_text()


old = """
        distance = math.sqrt(best_dist)

        dx = px - best[0]

        dy = py - best[1]
"""


new = """
        distance = math.sqrt(best_dist)


        road_lon = (
            self.lon0 +
            math.degrees(
                best[0] /
                (
                    EARTH_RADIUS_METERS *
                    math.cos(
                        math.radians(self.lat0)
                    )
                )
            )
        )


        road_lat = (
            self.lat0 +
            math.degrees(
                best[1] /
                EARTH_RADIUS_METERS
            )
        )


        dx = px - best[0]

        dy = py - best[1]
"""


if old not in text:
    raise Exception(
        "Could not find distance block"
    )


text = text.replace(
    old,
    new
)


old_return = """
        return {

            "heading": heading,

            "distance_m": distance,

            "road_class": best_class

        }
"""


new_return = """
        return {

            "heading": heading,

            "distance_m": distance,

            "road_class": best_class,

            "road_lat": road_lat,

            "road_lon": road_lon

        }
"""


if old_return not in text:
    raise Exception(
        "Could not find return block"
    )


text = text.replace(
    old_return,
    new_return
)


p.write_text(text)

print(
    "Added road coordinates to nearest road output"
)
