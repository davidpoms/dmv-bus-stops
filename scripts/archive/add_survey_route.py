from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = """
@app.route("/priorities/top")
"""

insert = r'''
@app.route("/survey/<int:stop_id>")
def survey(stop_id):

    stop = query_db(
        """
        SELECT
            ps.id,
            ps.primary_name,
            ps.latitude,
            ps.longitude

        FROM physical_stops ps

        WHERE ps.id = ?;
        """,
        (stop_id,)
    )

    if not stop:
        return "Stop not found", 404

    row = stop[0]

    return jsonify(
        {
            "stop_id": row[0],
            "location": row[1],
            "lat": row[2],
            "lon": row[3],
            "streetview_url":
                f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={row[2]},{row[3]}"
        }
    )


'''

if marker in text:
    text = text.replace(marker, insert + marker, 1)
    p.write_text(text)
    print("Added survey route")
else:
    print("Marker not found")
