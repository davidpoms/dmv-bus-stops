from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = "\n\n@app.route("

insert = """

@app.route("/validation/queue")
def validation_queue():

    rows = query_db(
        '''
        SELECT
            ps.id,
            ps.primary_name,
            ps.latitude,
            ps.longitude,
            sii.opportunity_score,
            sii.priority_level,
            sv.status

        FROM stop_validation sv

        JOIN stop_improvement_impact sii
            ON sv.physical_stop_id = sii.physical_stop_id

        JOIN physical_stops ps
            ON ps.id = sv.physical_stop_id

        WHERE sv.status = 'needs_validation'

        ORDER BY
            CASE sii.priority_level
                WHEN 'P1' THEN 1
                WHEN 'P2' THEN 2
                WHEN 'P3' THEN 3
                ELSE 4
            END,
            sii.opportunity_score DESC

        LIMIT 75;
        '''
    )

    return jsonify(
        [
            {
                "stop_id": row[0],
                "location": row[1],
                "lat": row[2],
                "lon": row[3],
                "score": row[4],
                "priority": row[5],
                "status": row[6]
            }

            for row in rows
        ]
    )

"""

if "/validation/queue" not in text:
    text = text.replace(marker, insert + marker, 1)
    p.write_text(text)

print("Added validation queue API")
