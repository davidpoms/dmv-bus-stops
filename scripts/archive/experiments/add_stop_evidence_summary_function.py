from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = "\n@app.route(\"/api/stops/<int:stop_id>/evidence\")"

addition = """

def get_stop_evidence_summary(stop_id):

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    osm = conn.execute(
        '''
        SELECT *
        FROM stop_osm_evidence
        WHERE stop_id=?
        ''',
        (stop_id,)
    ).fetchone()

    reviews = conn.execute(
        '''
        SELECT *
        FROM stop_observations
        WHERE physical_stop_id=?
        ORDER BY observed_at DESC
        ''',
        (stop_id,)
    ).fetchall()

    conn.close()

    return {
        "osm": dict(osm) if osm else None,
        "reviews": [
            dict(r)
            for r in reviews
        ]
    }

"""

if marker not in text:
    raise Exception("Injection point not found")

text = text.replace(
    marker,
    addition + marker,
    1
)

p.write_text(text)

print("Added stop evidence summary function")
