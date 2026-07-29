from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

anchor = '''
@app.route("/geography/dc-wards")
'''

insert = '''
@app.route("/geography/dc-ancs")
def geography_dc_ancs():

    rows = query_db(
        """
        SELECT DISTINCT dc_anc
        FROM stop_jurisdiction
        WHERE dc_anc IS NOT NULL
        ORDER BY dc_anc
        """
    )

    return jsonify(
        [
            row[0]
            for row in rows
        ]
    )


'''

if '"/geography/dc-ancs"' in text:
    print("ANC endpoint already exists")

elif anchor not in text:
    raise Exception("Could not find geography anchor")

else:
    text = text.replace(
        anchor,
        insert + anchor
    )

    p.write_text(text)

    print("Added ANC endpoint")
