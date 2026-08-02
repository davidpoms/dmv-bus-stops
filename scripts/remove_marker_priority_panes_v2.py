from pathlib import Path
import re


path = Path(
    "src/dashboard/static/dashboard.js"
)

js = path.read_text(
    encoding="utf-8"
)


pattern = r"""
\s*pane:
\s*props\.impact === "very_high"
\s*\?
\s*"veryHighPriority"
\s*:
\s*props\.impact === "high"
\s*\?
\s*"highPriority"
\s*:
\s*"markerPane"
"""


replacement = """
                            pane: "markerPane"
"""


new_js, count = re.subn(
    pattern,
    replacement,
    js,
    flags=re.VERBOSE
)


if count == 0:
    raise Exception(
        "Could not find priority pane logic"
    )


path.write_text(
    new_js,
    encoding="utf-8"
)


print(
    "Marker priority panes removed:",
    count
)