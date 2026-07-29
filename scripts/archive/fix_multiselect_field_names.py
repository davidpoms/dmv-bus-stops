from pathlib import Path

p = Path("src/review/render_survey.py")

text = p.read_text()


old = """
                <input
                    type="checkbox"
                    name="{escape(field)}"
                    value="{escape(value)}">
"""


new = """
                <input
                    type="checkbox"
                    name="{escape(field)}[]"
                    value="{escape(value)}">
"""


if old not in text:
    raise Exception(
        "Could not find checkbox renderer"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Updated multi-select checkbox names"
)
