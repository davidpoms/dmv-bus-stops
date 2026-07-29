from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

if 'def stop_evidence(stop_id):' in text:
    print("stop_evidence already exists")
    raise SystemExit

insert_before = '\n\n@app.get("/api/reviewer/<int:reviewer_id>/queue")'

endpoint = r'''

@app.route("/api/stops/<int:stop_id>/evidence")
def stop_evidence(stop_id):

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    osm = conn.execute(
        """
        SELECT *
        FROM stop_osm_evidence
        WHERE stop_id=?
        """,
        (stop_id,)
    ).fetchone()


    observations = conn.execute(
        """
        SELECT
            source,
            observer,
            shelter_present,
            bench_present,
            bench_feasible,
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

if insert_before not in text:
    raise SystemExit("Could not find insertion point")

text = text.replace(
    insert_before,
    endpoint + insert_before
)

p.write_text(text)

print("Added stop evidence endpoint")
