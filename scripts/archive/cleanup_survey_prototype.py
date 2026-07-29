from pathlib import Path


def remove_file(path):
    p = Path(path)

    if p.exists():
        p.unlink()
        print("REMOVED:", path)
    else:
        print("MISSING:", path)


def replace_once(path, old, new, label):

    p = Path(path)

    text = p.read_text()

    if old not in text:
        print("SKIPPED:", label)
        return

    text = text.replace(old,new,1)

    p.write_text(text)

    print("UPDATED:", label)


# Remove old prototype javascript
remove_file(
    "src/dashboard/static/review.js"
)


# Remove old script reference if still present
replace_once(
    "src/dashboard/templates/review.html",
    '<script src="/static/review.js"></script>',
    '',
    "remove old review.js include"
)


# Disable old survey-page route
replace_once(
    "src/api/app.py",
    '''@app.route("/survey-page/<int:stop_id>")
def survey_page(stop_id):

    from flask import render_template

    return render_template(
        "survey.html"
    )

''',
    '''@app.route("/survey-page/<int:stop_id>")
def survey_page(stop_id):

    return redirect(
        f"/review/{stop_id}"
    )

''',
    "replace old survey-page redirect"
)


print("\nCleanup complete")
