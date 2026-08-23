from pathlib import Path

path = Path(
    "src/dashboard/static/dashboard.js"
)

text = path.read_text()


old = """
detail.impact_summary.estimated_weekday_boardings.toLocaleString()
"""


new = """
(
    detail.impact_summary &&
    detail.impact_summary.estimated_weekday_boardings != null
)
?
detail.impact_summary.estimated_weekday_boardings.toLocaleString()
:
"Unknown"
"""


if old not in text:
    raise Exception(
        "boarding popup text not found"
    )


text = text.replace(
    old,
    new
)


old2 = """
detail.impact_summary.routes.length
"""


new2 = """
(
    detail.impact_summary &&
    detail.impact_summary.routes &&
    detail.impact_summary.routes.length
)
"""


if old2 not in text:
    raise Exception(
        "route popup text not found"
    )


text = text.replace(
    old2,
    new2
)


path.write_text(text)

print(
    "dashboard popup null handling fixed"
)