from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

if '"/api/review-queue"' in text:
    raise SystemExit("review queue endpoint already exists")

marker = '@app.route("/stops/<int:stop_id>/review-summary")'

idx = text.find(marker)

if idx == -1:
    raise Exception("review-summary marker not found")

addition = r'''

@app.route("/api/review-queue")
def review_queue():

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            ps.id AS stop_id,
            ps.location,
            ps.lat,
            ps.lon,
            io.opportunity_score,

            COALESCE(ste.gtfs_bus_stop,0)
                AS gtfs_bus_stop,

            COALESCE(ose.osm_bench,0)
                AS osm_bench,

            COALESCE(ose.osm_shelter,0)
                AS osm_shelter

        FROM physical_stops ps

        LEFT JOIN improvement_opportunities io
            ON io.physical_stop_id = ps.id

        LEFT JOIN stop_transit_evidence ste
            ON ste.stop_id = ps.id

        LEFT JOIN stop_osm_evidence ose
            ON ose.stop_id = ps.id

        WHERE
            ste.gtfs_bus_stop = 1

        AND
            (
                ose.osm_bench = 0
                OR
                ose.osm_shelter = 0
            )

        ORDER BY
            io.opportunity_score DESC

        LIMIT 100;
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

text = text[:idx] + addition + text[idx:]

path.write_text(text)

print("Added review queue endpoint")
