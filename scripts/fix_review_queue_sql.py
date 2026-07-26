from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

start = text.find('@app.route("/api/review-queue")')

if start == -1:
    raise Exception("review queue endpoint not found")

end = text.find('\n@app.route', start + 10)

if end == -1:
    end = len(text)

replacement = r'''
@app.route("/api/review-queue")
def review_queue():

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            ir.physical_stop_id,
            ps.lat,
            ps.lon,
            ir.recommendation_type,
            ir.priority,
            ir.confidence,
            ir.reasons,
            ir.evidence

        FROM improvement_recommendations ir

        JOIN physical_stops ps
            ON ps.id = ir.physical_stop_id

        ORDER BY
            CASE ir.priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                ELSE 3
            END,
            ir.physical_stop_id

        """
    ).fetchall()

    conn.close()

    return jsonify(
        {
            "count": len(rows),
            "queue": [
                {
                    "stop_id": row["physical_stop_id"],
                    "lat": row["lat"],
                    "lon": row["lon"],
                    "type": row["recommendation_type"],
                    "priority": row["priority"],
                    "confidence": row["confidence"],
                    "reasons": json.loads(row["reasons"])
                        if row["reasons"]
                        else [],
                    "evidence": json.loads(row["evidence"])
                        if row["evidence"]
                        else {}
                }
                for row in rows
            ]
        }
    )

'''

text = text[:start] + replacement + text[end:]

path.write_text(text)

print("Fixed review queue endpoint SQL")
