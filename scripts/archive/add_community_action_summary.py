from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

anchor = """
@app.route("/validation/status-summary")
def validation_status_summary():
"""

new_route = '''
@app.route("/community-actions/summary")
def community_action_summary():

    rows = query_db(
        """
        SELECT
            status,
            COUNT(*)
        FROM community_actions
        GROUP BY status
        """
    )


    summary = {
        "planned": 0,
        "in_progress": 0,
        "installed": 0,
        "total": 0
    }


    for row in rows:

        if row[0] in summary:
            summary[row[0]] = row[1]

        summary["total"] += row[1]


    return jsonify(summary)



'''

if "/community-actions/summary" in text:
    print("endpoint already exists")
    raise SystemExit(0)

if anchor not in text:
    print("endpoint location not found")
    raise SystemExit(1)

text = text.replace(
    anchor,
    new_route + anchor,
    1
)

p.write_text(text)

print("community action summary endpoint added")
