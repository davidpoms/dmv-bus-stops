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
            jurisdiction
        FROM physical_stops
        WHERE id=?
        """,
        (stop_id,)
    )

    if not stop:
        return "Stop not found", 404

    return render_template(
        "review.html",
        stop=stop[0],
        stop_id=stop_id,
        survey_html=render_survey()
    )
'''

if old not in text:
    raise Exception("review_page route block not found")

text = text.replace(old, new)

p.write_text(text)

print("Updated review_page route")
