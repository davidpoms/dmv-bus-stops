from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

route = r'''

@app.route("/review/<int:stop_id>")
def review_page(stop_id):

    return send_from_directory(
        BASE_DIR / "src" / "dashboard" / "templates",
        "review.html"
    )

'''

if 'def review_page(stop_id)' not in text:

    insert_point = text.find('@app.route("/review/submit"')

    text = (
        text[:insert_point]
        +
        route
        +
        text[insert_point:]
    )

    p.write_text(text)

    print("Added review page route")

else:

    print("Review page route already exists")
