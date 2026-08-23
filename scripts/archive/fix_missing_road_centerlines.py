from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

start = text.find("def get_road_index():")

end = text.find("\n\n@app.route", start)

if start == -1 or end == -1:
    raise Exception("Could not locate get_road_index function")

replacement = r'''
def get_road_index():

    global road_index

    if road_index is not None:
        return road_index


    try:

        rows = query_db(
            """
            SELECT geometry, road_class
            FROM road_centerlines
            """
        )


        roads = []

        for row in rows:

            geometry = json.loads(row[0])

            roads.append(
                {
                    "geometry": geometry["coordinates"],
                    "road_class": row[1]
                }
            )


        road_index = RoadSpatialIndex(
            roads
        )


    except Exception as e:

        print("Road centerlines unavailable:", e)


        class EmptyRoadIndex:

            def nearest_road(self, lat, lon):
                return None


        road_index = EmptyRoadIndex()


    return road_index
'''

text = text[:start] + replacement + text[end:]

path.write_text(text)

print("Replaced get_road_index() with fallback")