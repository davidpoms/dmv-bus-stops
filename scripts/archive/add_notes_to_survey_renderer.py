from pathlib import Path


path = Path("src/review/render_survey.py")

text = path.read_text()


old = """    html.append(
        render_section("steward")
    )


    return "\\n".join(html)
"""


new = """    html.append(
        render_section("steward")
    )


    html.append(
        render_question(
            SURVEY["notes"]
        )
    )


    return "\\n".join(html)
"""


if old not in text:
    raise SystemExit(
        "Could not find render_survey insertion point"
    )


text = text.replace(old, new)


path.write_text(text)

print("Added notes field to survey renderer")
