from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = '@app.route("/routes")'

insert = r'''
@app.route("/priority-summary")
def priority_summary():

    rows = query_db(
        """
        SELECT
            priority_level,
            COUNT(*) AS count

        FROM stop_improvement_impact

        GROUP BY priority_level;
        """
    )

    summary = {
        "P1": 0,
        "P2": 0,
        "P3": 0,
        "monitor": 0
    }

    for row in rows:
        if row[0] in summary:
            summary[row[0]] = row[1]

    return jsonify(summary)



'''

if marker in text:
    text = text.replace(marker, insert + marker, 1)
    p.write_text(text)
    print("Added priority summary API")
else:
    print("Routes marker not found")
