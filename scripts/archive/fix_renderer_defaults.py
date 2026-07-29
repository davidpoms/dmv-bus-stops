from pathlib import Path

path = Path("src/review/render_survey.py")

text = path.read_text()

text = text.replace(
    'qtype = question["type"]',
    'qtype = question.get("type", "select")'
)

text = text.replace(
'''    html.append(
        render_section("in_person")
    )

    return "\\n".join(html)
''',
'''    html.append(
        render_section("in_person")
    )

    html.append(
        render_section("steward")
    )

    html.append(
        render_question(SURVEY["notes"])
    )

    return "\\n".join(html)
'''
)

path.write_text(text)

print("Fixed renderer")
