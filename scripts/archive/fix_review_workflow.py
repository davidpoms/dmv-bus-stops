from pathlib import Path


def replace(path, old, new, description):
    p = Path(path)
    text = p.read_text()

    if old not in text:
        print(f"SKIP: {description} (not found)")
        return

    text = text.replace(old, new, 1)
    p.write_text(text)

    print(f"OK: {description}")


# -------------------------------------------------
# 1. Replace old survey-page route with redirect
# -------------------------------------------------

replace(
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

    "replace survey-page prototype route"
)


# -------------------------------------------------
# 2. Dashboard links should go to real review page
# -------------------------------------------------

replace(
    "src/dashboard/static/dashboard.js",

    "window.location='/survey-page/${stop.stop_id}'",

    "window.location='/review/${stop.stop_id}'",

    "redirect dashboard review button"
)


# -------------------------------------------------
# 3. Remove empty loader include
# -------------------------------------------------

replace(
    "src/dashboard/templates/review.html",

    '<script src="/static/review_info_loader.js"></script>\n',

    "",

    "remove empty review_info_loader include"
)


# -------------------------------------------------
# 4. Add review_stop.js
# -------------------------------------------------

replace(
    "src/dashboard/templates/review.html",

    '<script src="/static/review_survey.js"></script>',

    '''<script src="/static/review_survey.js"></script>
<script src="/static/review_stop.js"></script>''',

    "add review_stop javascript"
)


# -------------------------------------------------
# 5. Add heading display
# -------------------------------------------------

replace(
    "src/dashboard/static/review_stop.js",

'''                Coordinates:
                ${data.lat.toFixed(5)},
                ${data.lon.toFixed(5)}
                <br><br>
                <a href="${data.streetview_url}"
''',

'''                Coordinates:
                ${data.lat.toFixed(5)},
                ${data.lon.toFixed(5)}

                <br>

                Camera heading:
                ${
                    data.heading
                    ? data.heading.toFixed(1)
                    : "unknown"
                }°

                <br><br>

                <a href="${data.streetview_url}"
''',

"add heading display"
)


print("\nDone.")
