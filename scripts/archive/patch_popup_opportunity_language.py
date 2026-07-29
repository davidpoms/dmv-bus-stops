from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
                                    <b>Opportunity Signal</b><br>

                                    Score:
                                    ${props.score}<br>

                                    Impact:
                                    ${props.impact}<br>
"""


new = """
                                    <b>Opportunity Signal</b><br>

                                    Rider impact:
                                    ${props.impact}<br>

                                    This stop is being evaluated through
                                    community verification.
                                    <br>
"""


if old not in text:
    print("popup opportunity block not found")
    raise SystemExit(1)


text = text.replace(old, new)

p.write_text(text)

print("popup opportunity language patched")

