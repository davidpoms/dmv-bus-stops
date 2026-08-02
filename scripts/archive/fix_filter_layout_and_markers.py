from pathlib import Path


# ----------------------------
# Fix dashboard filter HTML
# ----------------------------

html_path = Path(
    "src/dashboard/templates/dashboard.html"
)

text = html_path.read_text(
    encoding="utf-8"
)


old = """
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
<option value="">All</option>
<option value="DC">DC</option>
<option value="Maryland">Maryland</option>
<option value="Virginia">Virginia</option>
</select>
</label>
"""


new = """
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
<option value="">All</option>
<option value="DC">DC</option>
<option value="Maryland">Maryland</option>
<option value="Virginia">Virginia</option>
</select>

</div>
"""


if old not in text:
    raise Exception(
        "Could not find filter HTML block"
    )


text = text.replace(
    old,
    new
)


html_path.write_text(
    text,
    encoding="utf-8"
)



# ----------------------------
# Simplify marker styling
# ----------------------------

js_path = Path(
    "src/dashboard/static/dashboard.js"
)

js = js_path.read_text(
    encoding="utf-8"
)


old_marker = """
let color = "gray";
let radius = 5;


if (
    props.impact === "very_high"
) {
    color = "red";
    radius = 14;
}

else if (
    props.impact === "high"
) {
    color = "orange";
    radius = 10;
}

else if (
    props.impact === "medium"
) {
    color = "gold";
    radius = 7;
}
"""


new_marker = """
let color = "#666";
let radius = 7;
"""


if old_marker not in js:
    raise Exception(
        "Could not find marker styling block"
    )


js = js.replace(
    old_marker,
    new_marker
)


old_options = """
radius:radius,
color:color,
fillOpacity:0.7,

pane:
    props.impact === "very_high"
    ? "veryHighPriority"
    :
    props.impact === "high"
    ? "highPriority"
    :
    "markerPane"
"""


new_options = """
radius:radius,
color:color,
fillOpacity:0.7
"""


if old_options in js:
    js = js.replace(
        old_options,
        new_options
    )


js_path.write_text(
    js,
    encoding="utf-8"
)


print(
    "Filter layout and marker simplification complete."
)