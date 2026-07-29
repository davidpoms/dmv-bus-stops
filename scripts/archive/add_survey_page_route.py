from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

insert = '''

@app.route("/survey-page/<int:stop_id>")
def survey_page(stop_id):

    from flask import render_template

    return render_template(
        "survey.html"
    )

'''

marker = '@app.route("/survey/<int:stop_id>")'

if insert.strip() not in text:
    text = text.replace(marker, insert + marker)

    p.write_text(text)

    print("Added survey page route")
else:
    print("Already exists")
