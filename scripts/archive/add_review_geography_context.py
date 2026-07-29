from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = '''@app.route("/review/<int:stop_id>")
def review_page(stop_id):

    from src.review.render_survey import render_survey

    return render_template(
        "review.html",
        stop_id=stop_id,
        survey_html=render_survey()
    )
'''


new = '''@app.route("/review/<int:stop_id>")
def review_page(stop_id):

    from src.review.render_survey import render_survey


    stop = query_db(
        """
        SELECT
            id,
            primary_name,
            latitude,
            longitude,
            state,
            dc_ward,
            dc_anc,
            county,
            municipality
        FROM physical_stops
        WHERE id=?
        """,
        (stop_id,)
    )


    if not stop:
        return "Stop not found", 404


    row = stop[0]


    stop_info = {
        "id": row[0],
        "name": row[1],
        "latitude": row[2],
        "longitude": row[3],
        "state": row[4],
        "ward": row[5],
        "anc": row[6],
        "county": row[7],
        "municipality": row[8],
    }


    return render_template(
        "review.html",
        stop_id=stop_id,
        stop_info=stop_info,
        survey_html=render_survey()
    )
'''


if old not in text:
    raise Exception("Could not find review_page block")


text = text.replace(old,new)

p.write_text(text)

print("Updated review_page geography context")
