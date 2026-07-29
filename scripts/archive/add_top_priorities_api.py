from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

insert = '''
@app.route("/priorities/top")
def top_priorities():

    rows = query_db(
        """
        SELECT
            ps.primary_name,
            sii.opportunity_score,
            sii.priority_level,
            sii.impact_level

        FROM stop_improvement_impact sii

        JOIN physical_stops ps
            ON sii.physical_stop_id = ps.id

        ORDER BY sii.opportunity_score DESC

        LIMIT 10;
        """
    )

    return jsonify(
        [
            {
                "location": row[0],
                "score": row[1],
                "priority": row[2],
                "impact": row[3]
            }
            for row in rows
        ]
    )

'''

marker = '@app.route("/map/stops")'

if marker in text:
    text = text.replace(marker, insert + "\n" + marker, 1)
    p.write_text(text)
    print("Added top priorities API")
else:
    print("API marker not found")
