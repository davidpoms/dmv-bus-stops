from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = """
@app.route("/review/<int:stop_id>/assignment")
def review_assignment(stop_id):
"""

if marker not in text:
    raise Exception("Could not find review assignment route")


route = r'''
@app.route("/review/<int:stop_id>/info")
def review_stop_info(stop_id):

    stop = query_db(
        """
        SELECT
            id,
            primary_name,
            latitude,
            longitude,
            state,
            dc_ward,
            dc_anc,
            county,
            municipality
        FROM physical_stops
        WHERE id=?
        """,
        (stop_id,)
    )

    if not stop:
        return {"error": "Stop not found"}, 404

    row = stop[0]

    return jsonify(
        {
            "stop_id": row[0],
            "name": row[1],
            "lat": row[2],
            "lon": row[3],
            "state": row[4],
            "ward": row[5],
            "anc": row[6],
            "county": row[7],
            "municipality": row[8],
            "streetview_url":
                f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={row[2]},{row[3]}"
        }
    )


'''

text = text.replace(
    marker,
    route + marker
)

p.write_text(text)

print("Added review stop info endpoint")
