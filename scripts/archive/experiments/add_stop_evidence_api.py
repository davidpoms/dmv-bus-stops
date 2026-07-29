from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

addition = r'''

@app.route("/api/stops/<int:stop_id>/evidence")
def stop_evidence(stop_id):

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    osm = conn.execute(
        """
        SELECT

            osm_bus_stop,
            osm_bench,
            osm_shelter,
            osm_tags,
            osm_snapshot_date,
            osm_source_file

        FROM stop_osm_evidence

        WHERE stop_id=?

        """,
        (stop_id,)
    ).fetchone()


    observations = conn.execute(
        """
        SELECT

            source,
            bench_present,
            shelter_present,
            notes,
            confidence,
            observed_at

        FROM stop_observations

        WHERE physical_stop_id=?

        ORDER BY observed_at DESC

        """,
        (stop_id,)
    ).fetchall()


    conn.close()


    return jsonify(
        {
            "stop_id": stop_id,

            "osm": dict(osm) if osm else None,

            "observations":
                [
                    dict(row)
                    for row in observations
                ]
        }
    )

'''

if "/api/stops/<int:stop_id>/evidence" not in text:

    text += addition

    p.write_text(text)

    print("Added stop evidence API")

else:

    print("Evidence API already exists")
