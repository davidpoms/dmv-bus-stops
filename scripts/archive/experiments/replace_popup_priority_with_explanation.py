from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
                                <b>Community improvement priority</b><br>
                                ${
                                    props.score
                                    ? props.score + " / 100"
                                    : "Not yet calculated"
                                }<br>
                                ${props.impact ? "Community impact: " + props.impact + "<br>" : ""}<br>
"""


new = """
                                <b>Why this stop is being reviewed</b><br>

                                This stop has been identified as a possible
                                opportunity for improvement. Community feedback
                                will help determine whether riders would benefit
                                from changes like seating, shelter, or other
                                waiting area improvements.
                                <br><br>
"""


if old not in text:
    raise Exception(
        "Could not find priority explanation block"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Replaced internal priority score with plain-language explanation"
)
