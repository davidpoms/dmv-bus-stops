from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = """
@app.route("/review/<int:stop_id>")
def review_page(stop_id):

    return send_from_directory(
        BASE_DIR / "src" / "dashboard" / "templates",
        "review.html"
    )
"""

new = """
@app.route("/review/<int:stop_id>")
def review_page(stop_id):

    from review.render_survey import render_survey

    return render_template(
        "review.html",
        stop_id=stop_id,
        survey_html=render_survey()
    )
"""

if "survey_html=render_survey()" in text:
    print("Review route already updated")
    raise SystemExit(0)

if old not in text:
    raise SystemExit(
        "Could not find review route block"
    )

text = text.replace(old, new)

path.write_text(text)

print("Updated review route to render survey dynamically")
