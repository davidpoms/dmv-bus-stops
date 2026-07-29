from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = '@app.route("/priority-summary")'

insert = r'''

@app.route("/validation/status-summary")
def validation_status_summary():

    rows = query_db(
        """
        SELECT
            status,
            COUNT(*) AS count
        FROM stop_validation
        GROUP BY status
        ORDER BY count DESC
        """
    )

    return jsonify(
        [
            {
                "status": row[0],
                "count": row[1]
            }
            for row in rows
        ]
    )



'''

if "/validation/status-summary" not in text:
    text = text.replace(marker, insert + marker)

p.write_text(text)

print("validation status endpoint added")
