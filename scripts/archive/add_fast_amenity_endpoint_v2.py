from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

if "def stop_amenities" in text:
    print("Already exists")
    raise SystemExit


insert = r'''

@app.route("/stops/<int:stop_id>/amenities")
def stop_amenities(stop_id):

    wmata = query_db(
        """
        SELECT
            wmata_shelter,
            wmata_bench,
            wmata_accessible,
            match_confidence
        FROM stop_wmata_evidence
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )

    osm = query_db(
        """
        SELECT
            osm_shelter,
            osm_bench
        FROM stop_osm_evidence
        WHERE stop_id = ?
        """,
        (stop_id,)
    )

    return jsonify(
        {
            "wmata": (
                {
                    "shelter": wmata[0][0],
                    "bench": wmata[0][1],
                    "accessible": wmata[0][2],
                    "confidence": wmata[0][3],
                }
                if wmata else None
            ),
            "osm": (
                {
                    "shelter": osm[0][0],
                    "bench": osm[0][1],
                }
                if osm else None
            )
        }
    )

'''


marker='@app.route("/survey-page/<int:stop_id>")'

if marker not in text:
    raise Exception("Could not find insertion point")

text=text.replace(marker, insert+"\n"+marker)

p.write_text(text)

print("Added amenity endpoint")
