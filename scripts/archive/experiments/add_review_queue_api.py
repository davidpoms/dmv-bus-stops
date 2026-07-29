from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = "\n@app.route(\"/api/stops/<int:stop_id>/evidence\")"

addition = r'''

@app.route("/api/review-queue")
def review_queue():

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT

            e.stop_id,

            ps.primary_name,

            ps.latitude,

            ps.longitude,

            CASE

                WHEN e.osm_shelter = 1
                THEN 'medium'

                ELSE 'high'

            END AS priority,


            CASE

                WHEN e.osm_shelter = 1
                THEN 'Shelter mapped, bench needs verification'

                ELSE 'No bench or shelter mapped'

            END AS reason


        FROM stop_osm_evidence e

        JOIN physical_stops ps

            ON ps.id = e.stop_id


        WHERE e.osm_bus_stop = 1

        AND e.osm_bench = 0


        ORDER BY priority DESC

        LIMIT 100

        """
    ).fetchall()


    conn.close()


    return jsonify(
        [
            dict(row)
            for row in rows
        ]
    )

'''

if marker not in text:
    raise Exception("Marker not found")

if "/api/review-queue" not in text:
    text = text.replace(marker, addition + marker, 1)

p.write_text(text)

print("Added review queue API")
