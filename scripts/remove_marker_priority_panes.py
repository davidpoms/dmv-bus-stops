from pathlib import Path

path = Path(
    "src/dashboard/static/dashboard.js"
)

js = path.read_text(
    encoding="utf-8"
)


old = """
                            pane:
                                props.impact === "very_high"
                                ? "veryHighPriority"
                                :
                                props.impact === "high"
                                ? "highPriority"
                                :
                                "markerPane"
"""


new = """
                            pane: "markerPane"
"""


if old not in js:
    raise Exception(
        "Could not find priority pane block"
    )


js = js.replace(
    old,
    new
)


path.write_text(
    js,
    encoding="utf-8"
)


print(
    "Removed priority marker panes."
)