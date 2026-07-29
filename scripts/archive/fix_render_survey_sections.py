from pathlib import Path

path = Path("src/review/render_survey.py")

text = path.read_text()

start = text.find("def render_survey():")

if start == -1:
    raise SystemExit("Could not find render_survey function")

new_function = """def render_survey():

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

    return "\\n".join(html)
"""

text = text[:start] + new_function

path.write_text(text)

print("Replaced render_survey function")
