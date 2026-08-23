from pathlib import Path


path = Path(
    "src/dashboard/static/dashboard.js"
)

text = path.read_text(
    encoding="utf-8"
)


old = """pane:
                            props.impact === "very_high"
                            ? "veryHighPriority"
                            :
                            props.impact === "high"
                            ? "highPriority"
                            :
                            "markerPane"
"""


new = """pane: "markerPane"
"""


if old not in text:
    raise Exception(
        "Exact pane block not found"
    )


text = text.replace(
    old,
    new
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Removed priority panes from markers."
)