from pathlib import Path


# ----------------------------
# Fix dashboard HTML filter layout
# ----------------------------

html_path = Path(
    "src/dashboard/templates/dashboard.html"
)

text = html_path.read_text(
    encoding="utf-8"
)


old = """
<div class="filter-row">

<label>
State
<div class="filter-group">

<label for="routeFilter">
Route
</label>

<select id="routeFilter">

<option value="">
All routes
</option>

</select>

</div>


<select id="stateFilter">
"""


new = """
<div class="filter-row">

<div class="filter-group">

<label for="routeFilter">
Route
</label>

<select id="routeFilter">

<option value="">
All routes
</option>

</select>

</div>


<div class="filter-group">

<label for="stateFilter">
State
</label>

<select id="stateFilter">
"""


if old not in text:
    raise Exception(
        "Could not find filter HTML block"
    )


text = text.replace(
    old,
    new
)


# close state div before county label
old2 = """
</select>
</label>


<label>
County
"""


new2 = """
</select>

</div>


<div class="filter-group">

<label>
County
"""


if old2 not in text:
    raise Exception(
        "Could not find state closing block"
    )


text = text.replace(
    old2,
    new2,
    1
)


html_path.write_text(
    text,
    encoding="utf-8"
)


# ----------------------------
# Fix marker styling
# ----------------------------

js_path = Path(
    "src/dashboard/static/dashboard.js"
)

js = js_path.read_text(
    encoding="utf-8"
)


start = js.find(
    'let color = "gray";'
)

end = js.find(
    'const marker = L.circleMarker',
    start
)


if start == -1 or end == -1:
    raise Exception(
        "Could not find marker styling block"
    )


replacement = """
let color = "gray";
let radius = 6;


"""


js = (
    js[:start]
    +
    replacement
    +
    js[end:]
)


# remove conditional pane logic

old_pane = """
pane:
                            props.impact === "very_high"
                            ? "veryHighPriority"
                            :
                            props.impact === "high"
                            ? "highPriority"
                            :
                            "markerPane"
"""

js = js.replace(
    old_pane,
    ""
)


js_path.write_text(
    js,
    encoding="utf-8"
)


print(
    "Filter layout and marker styling fixed."
)