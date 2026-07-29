from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


# add request variable
old = """
    dc_ward = request.args.get("dc_ward")
"""

new = """
    dc_ward = request.args.get("dc_ward")
    dc_anc = request.args.get("dc_anc")
"""

if "dc_anc = request.args.get" not in text:
    text = text.replace(old, new)


# add SQL filter after ward filters
old_sql = """
            AND (
                ? IS NULL
                OR sj.dc_ward = ?
            )
"""

new_sql = """
            AND (
                ? IS NULL
                OR sj.dc_ward = ?
            )

            AND (
                ? IS NULL
                OR sj.dc_anc = ?
            )
"""

text = text.replace(old_sql, new_sql)


# add query parameters after ward pairs
old_params = """
                dc_ward,
                dc_ward,
"""

new_params = """
                dc_ward,
                dc_ward,
                dc_anc,
                dc_anc,
"""

text = text.replace(old_params, new_params)


p.write_text(text)

print("ANC map filtering added")
