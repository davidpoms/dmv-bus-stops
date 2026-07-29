from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
                                Improvement priority score: ${props.score || "Not available"}<br>
"""


new = """
                                <b>Community improvement priority</b><br>
                                ${
                                    props.score
                                    ? props.score + " / 100"
                                    : "Not yet calculated"
                                }<br>
"""


if old not in text:
    raise Exception(
        "Could not find popup score language"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Updated popup priority language"
)
