from pathlib import Path

p = Path("src/review/render_survey.py")

text = p.read_text()


old = '''def render_survey():

    html = []

    html.append(
        render_question(
            {
                "field": "review_mode",
                "label": SURVEY["review_mode"]["label"],
                "type": SURVEY["review_mode"]["type"],
                "options": SURVEY["review_mode"]["options"]
            }
        )
    )

    html.append(
        render_section("remote")
    )

    html.append(
        render_section("in_person")
    )

    html.append(
        render_section("steward")
    )

    return "\\n".join(html)
'''


new = '''def render_survey():

    html = []

    html.append(
        render_question(
            {
                "field": "review_mode",
                "label": SURVEY["review_mode"]["label"],
                "type": SURVEY["review_mode"]["type"],
                "options": SURVEY["review_mode"]["options"]
            }
        )
    )


    # Remote questions are the baseline.
    # In-person reviews inherit all remote questions
    # plus additional field observations.

    html.append(
        render_section("remote")
    )


    html.append(
        render_section("in_person")
    )


    html.append(
        render_section("steward")
    )


    return "\\n".join(html)
'''


if old not in text:
    raise Exception(
        "Expected render_survey block not found"
    )


text = text.replace(old, new)

p.write_text(text)

print(
    "Updated render_survey logic"
)
