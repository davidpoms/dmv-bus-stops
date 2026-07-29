from pathlib import Path


APP_FILE = Path("src/api/app.py")


def main():

    text = APP_FILE.read_text()


    # 1. Add import
    old = "from src.assessment.interpretation import ("

    if "from src.spatial.nearest_road import RoadSpatialIndex" not in text:

        text = text.replace(
            old,
            "from src.spatial.nearest_road import RoadSpatialIndex\n\n"
            + old
        )


    # 2. Add road index loader after imports / before first route
    marker = "\n\n@app.route"

    loader = r'''

\n
road_index = None


def get_road_index():

    global road_index

    if road_index is not None:
        return road_index


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

    return road_index

'''

    if "def get_road_index()" not in text:

        text = text.replace(
            marker,
            loader + marker,
            1
        )


    # 3. Replace survey streetview generation
    old_url = '''"streetview_url":
                f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={row[2]},{row[3]}"'''

    new_block = r'''streetview = get_road_index().nearest_road(
        row[3],
        row[2]
    )


    heading = 0

    if streetview and streetview["heading"] is not None:
        heading = streetview["heading"]


    streetview_url = (
        "https://www.google.com/maps/@?api=1"
        "&map_action=pano"
        f"&viewpoint={row[2]},{row[3]}"
        f"&heading={heading}"
        "&pitch=0"
        "&fov=90"
    )'''

    if old_url in text:

        text = text.replace(
            old_url,
            '"streetview_url": streetview_url'
        )


        # Insert calculation before return jsonify if needed
        target = "return jsonify(\n        {"

        text = text.replace(
            target,
            new_block + "\n\n    " + target,
            1
        )


    APP_FILE.write_text(text)

    print("Updated:", APP_FILE)


if __name__ == "__main__":
    main()
