from pathlib import Path

p = Path("src/spatial/nearest_road.py")

text = p.read_text()


# Add coordinate conversion if not already present
if "road_lon =" not in text:

    old = """
        distance = math.sqrt(best_dist)

        dx = px - best[0]
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
"""

    if old not in text:
        raise Exception(
            "Could not find distance calculation block"
        )

    text = text.replace(
        old,
        new
    )


# Replace only the return dictionary contents
old_return_start = """
        return {
"""

start = text.find(old_return_start)

if start == -1:
    raise Exception(
        "Could not find return statement"
    )


end = text.find(
    "\n        }",
    start
)

if end == -1:
    raise Exception(
        "Could not find return end"
    )

end += len("\n        }")


old_return = text[start:end]


new_return = """
        return {

            "heading": heading,

            "distance_m": distance,

            "road_class": best_class,

            "road_lat": road_lat,

            "road_lon": road_lon

        }
"""


text = text[:start] + new_return + text[end:]


p.write_text(text)

print(
    "Updated nearest road return payload"
)
