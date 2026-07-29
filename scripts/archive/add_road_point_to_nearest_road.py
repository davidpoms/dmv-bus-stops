from pathlib import Path

p = Path("src/spatial/nearest_road.py")

text = p.read_text()

old = """
        return {

            "heading": heading,

            "distance_m": distance,

            "road_class": best_class

        }
"""

new = """
        road_lon = None
        road_lat = None

        if self.lon0 is not None and self.lat0 is not None:

            road_lon = (
                self.lon0
                +
                math.degrees(
                    best[0]
                    /
                    (
                        EARTH_RADIUS_METERS
                        *
                        math.cos(math.radians(self.lat0))
                    )
                )
            )

            road_lat = (
                self.lat0
                +
                math.degrees(
                    best[1]
                    /
                    EARTH_RADIUS_METERS
                )
            )


        return {

            "heading": heading,

            "distance_m": distance,

            "road_class": best_class,

            "road_lon": road_lon,

            "road_lat": road_lat

        }
"""

if old not in text:
    raise Exception("Could not find return block")

text = text.replace(old, new)

p.write_text(text)

print("Added nearest road coordinates")
