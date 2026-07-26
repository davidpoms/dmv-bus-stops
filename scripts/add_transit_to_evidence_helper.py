from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

start = text.find("def get_stop_evidence_summary(stop_id):")
end = text.find("@app.route(\"/observations/create\"", start)

if start == -1:
    raise Exception("get_stop_evidence_summary not found")

if end == -1:
    raise Exception("next route marker not found")

new_function = '''def get_stop_evidence_summary(stop_id):

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    transit = conn.execute(
        """
        SELECT *
        FROM stop_transit_evidence
        WHERE stop_id=?
        """,
        (stop_id,)
    ).fetchone()


    osm = conn.execute(
        """
        SELECT *
        FROM stop_osm_evidence
        WHERE stop_id=?
        """,
        (stop_id,)
    ).fetchone()


    reviews = conn.execute(
        """
        SELECT *
        FROM stop_observations
        WHERE physical_stop_id=?
        ORDER BY observed_at DESC
        """,
        (stop_id,)
    ).fetchall()


    conn.close()


    return {
        "transit": dict(transit) if transit else None,

        "osm": dict(osm) if osm else None,

        "reviews": [
            dict(r)
            for r in reviews
        ]
    }


'''

text = text[:start] + new_function + text[end:]

path.write_text(text)

print("Updated get_stop_evidence_summary with transit evidence.")
