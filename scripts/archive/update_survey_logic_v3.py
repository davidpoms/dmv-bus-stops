from pathlib import Path

p = Path("src/review/render_survey.py")

text = p.read_text()


start = text.index(
    "def render_survey():"
)


new_function = '''def render_survey():

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


    # Always include remote-visible questions.
    # In-person review adds additional observations.
    # Steward questions are available to all reviewers.

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


text = text[:start] + new_function


p.write_text(text)

print("Updated render_survey()")
