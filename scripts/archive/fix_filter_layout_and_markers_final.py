from pathlib import Path


# -----------------------------
# Fix dashboard filter HTML
# -----------------------------

html_path = Path("src/dashboard/templates/dashboard.html")

text = html_path.read_text(encoding="utf-8")


# Remove the accidental nesting around route filter
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
"""


if old not in text:
    raise Exception(
        "Could not find route/state nesting block"
    )


text = text.replace(old, new)


# Add missing filter-group wrappers to remaining filters
replacements = [
(
"""
<label>
County
<select id="countyFilter">
""",
"""
<div class="filter-group">
<label for="countyFilter">
County
</label>

<select id="countyFilter">
"""
),
(
"""
<label>
Ward
<select id="wardFilter">
""",
"""
<div class="filter-group">
<label for="wardFilter">
Ward
</label>

<select id="wardFilter">
"""
),
(
"""
<label>
ANC
<select id="ancFilter">
""",
"""
<div class="filter-group">
<label for="ancFilter">
ANC
</label>

<select id="ancFilter">
"""
),
(
"""
<label>
Municipality
<select id="municipalityFilter">
""",
"""
<div class="filter-group">
<label for="municipalityFilter">
Municipality
</label>

<select id="municipalityFilter">
"""
)
]


for a,b in replacements:
    if a in text:
        text = text.replace(a,b)


html_path.write_text(
    text,
    encoding="utf-8"
)


# -----------------------------
# Fix marker visualization
# -----------------------------

js_path = Path("src/dashboard/static/dashboard.js")

js = js_path.read_text(
    encoding="utf-8"
)


start = js.find(
"""
let color = "gray";
let radius = 5;
"""
)

end = js.find(
"""
const marker = L.circleMarker(
""",
start
)


if start == -1 or end == -1:
    raise Exception(
        "Could not locate marker styling block"
    )


replacement = """
let color = "gray";
let radius = 7;

"""


js = (
    js[:start]
    +
    replacement
    +
    js[end:]
)


# simplify pane selection too

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

new_pane = """
pane:
    "markerPane"
"""


if old_pane in js:
    js = js.replace(
        old_pane,
        new_pane
    )


js_path.write_text(
    js,
    encoding="utf-8"
)


print(
    "Filter layout and marker simplification complete."
)