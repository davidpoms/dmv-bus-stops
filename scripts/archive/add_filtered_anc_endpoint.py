from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

if 'def geography_dc_ancs_by_ward' in text:
    print("Filtered ANC endpoint already exists")
    exit()


anchor = '''
@app.route("/geography/dc-wards")
'''

insert = '''
@app.route("/geography/dc-ancs")
def geography_dc_ancs():

    dc_ward = request.args.get("dc_ward")


    rows = query_db(
        """
        SELECT DISTINCT dc_anc
        FROM stop_jurisdiction
        WHERE dc_anc IS NOT NULL

        AND (
            ? IS NULL
            OR dc_ward = ?
        )

        ORDER BY dc_anc
        """,
        (
            dc_ward,
            dc_ward
        )
    )


    return jsonify(
        [
            row[0]
            for row in rows
        ]
    )


'''

if anchor not in text:
    raise Exception("Could not find geography anchor")


text = text.replace(
    anchor,
    insert + anchor
)


p.write_text(text)

print("Added ward-dependent ANC endpoint")
