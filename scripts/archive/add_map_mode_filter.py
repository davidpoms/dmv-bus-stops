from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
@app.route("/map/stops")
def map_stops():

    rows = query_db(
"""

new = """
@app.route("/map/stops")
def map_stops():

    mode = request.args.get(
        "mode",
        "review"
    )

    rows = query_db(
"""

if old not in text:
    print("map endpoint start not found")
    raise SystemExit(1)

text = text.replace(old,new)

p.write_text(text)

print("map mode parameter added")
