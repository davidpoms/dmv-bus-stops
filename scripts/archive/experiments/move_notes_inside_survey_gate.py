from pathlib import Path

p = Path("src/review/render_survey.py")

text = p.read_text()


notes = '''    html.append(
        render_question(
            SURVEY["notes"]
        )
    )
'''


if notes not in text:
    raise Exception("Could not find notes block")


# Remove existing notes block
text = text.replace(notes, "", 1)


closing_marker = '''    html.append(
        """
        </div>
        """
    )
'''


if closing_marker not in text:
    raise Exception("Could not find closing survey div")


text = text.replace(
    closing_marker,
    notes + "\n" + closing_marker,
    1
)


p.write_text(text)

print("Moved notes question inside surveyContent gate")
